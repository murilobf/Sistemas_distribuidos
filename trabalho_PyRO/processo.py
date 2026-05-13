import Pyro5
import Pyro5.api
import random
import threading
import time
import sys

lista_processos = [
    "PYRO:processo1@localhost:9001",
    "PYRO:processo2@localhost:9002",
    "PYRO:processo3@localhost:9003",
    "PYRO:processo4@localhost:9004",
]

THRESHOLD_VOTOS = len(lista_processos) // 2 + 1
TEMPO_HEARTBEAT = 1
TIMEOUT_MIN = TEMPO_HEARTBEAT * 4
TIMEOUT_MAX = TEMPO_HEARTBEAT * 8
TIMEOUT_RPC = 2

class NoProcesso:
    def __init__(self, node_id, porta):
        self._lock = threading.Lock()
        self.nome = f"processo{node_id}"
        self.uri = f"PYRO:{self.nome}@localhost:{porta}"
        self.estado = "seguidor"
        self.termo = 0
        self.termo_votado = -1
        self.log = []
        self.commit_index = -1
        self.timer = None
        self.inicia_timer()

    def inicia_timer(self):
        timeout = random.uniform(TIMEOUT_MIN, TIMEOUT_MAX)
        self.timer = threading.Timer(timeout, self.pede_voto)
        self.timer.daemon = True
        self.timer.start()

    def reseta_timer(self):
        if self.timer:
            self.timer.cancel()

        if self.estado != "lider":
            self.inicia_timer()

    def toma_posse(self, termo_eleicao):
        with self._lock:
            if self.estado != "candidato" or self.termo != termo_eleicao:
                return

            self.estado = "lider"
            termo = self.termo

        print(f"[{self.nome}] Tomei posse no termo {termo}")

        try:
            with Pyro5.api.locate_ns() as ns:
                try:
                    ns.remove("lider")
                except:
                    pass

                ns.register("lider", self.uri)

        except Exception as e:
            print(f"[{self.nome}] Aviso: não registrei no NS ({e})")

        threading.Thread(target=self.envia_heartbeats, daemon=True).start()

    def envia_heartbeats(self):
        def enviar(uri):
            try:
                with Pyro5.api.Proxy(uri) as p:
                    p._pyroTimeout = TIMEOUT_RPC
                    p.replica_entradas(termo_atual, log_atual, commit_atual)
            except:
                pass

        while True:
            with self._lock:
                if self.estado != "lider":
                    return

                termo_atual = self.termo
                log_atual = list(self.log)
                commit_atual = self.commit_index

            for uri in lista_processos:
                if uri == self.uri:
                    continue

                threading.Thread(target=enviar, args=(uri,), daemon=True).start()

            time.sleep(TEMPO_HEARTBEAT)

    @Pyro5.api.expose
    def replica_entradas(self, termo_lider, log_lider, commit_lider):
        escrever = False
        self.reseta_timer()

        with self._lock:
            if termo_lider < self.termo:
                return False
            
            avancou_termo = termo_lider > self.termo
            self.termo = termo_lider

            if avancou_termo or self.estado != "lider":
                self.estado = "seguidor"

            if avancou_termo:
                self.termo_votado = -1

            log_anterior = len(self.log)
            self.log = list(log_lider)

            novos = self.log[log_anterior:]
            if novos:
                for entrada in novos:
                    print(f"[{self.nome}] Replicado: '{entrada['comando']}'")

            if commit_lider > self.commit_index:
                novo = min(commit_lider, len(self.log) - 1)

                if novo > self.commit_index:
                    self.commit_index = novo
                    comando = self.log[novo]["comando"]
                    escrever = True
                    print(f"[{self.nome}] Commit índice {novo}: '{comando}'")

            self.reseta_timer()

        if(escrever):
            with open(f"{self.nome}.txt", "a") as f:
                f.write(comando + "\n")

        return True

    @Pyro5.api.expose
    def manda_voto(self, termo_candidato, ultimo_indice_candidato, ultimo_termo_candidato):
        voto = False

        with self._lock:
            if self.estado == "lider" and termo_candidato <= self.termo:
                return False
            if termo_candidato < self.termo:
                return False

            if termo_candidato > self.termo:
                self.termo = termo_candidato
                self.estado = "seguidor"
                self.termo_votado = -1

            ja_votei = self.termo_votado != -1 and self.termo_votado == self.termo

            if not ja_votei:
                meu_ultimo_termo = self.log[-1]["termo"] if self.log else -1
                meu_ultimo_indice = len(self.log) - 1

                log_ok = (
                    ultimo_termo_candidato > meu_ultimo_termo or
                    (
                        ultimo_termo_candidato == meu_ultimo_termo and
                        ultimo_indice_candidato >= meu_ultimo_indice
                    )
                )

                if log_ok:
                    self.termo_votado = self.termo
                    voto = True
                    print(f"[{self.nome}] Votei no candidato (termo {self.termo})")

        self.reseta_timer()
        return voto

    @Pyro5.api.expose
    def recebe_comando(self, comando):
        escrever = False
        def propaga(uri):
            try:
                with Pyro5.api.Proxy(uri) as processo:
                    processo._pyroTimeout = TIMEOUT_RPC * 2
                    processo.replica_entradas(termo_atual, log_atual, novo_commit)
            except:
                pass

        with self._lock:
            if self.estado != "lider":
                return {"ok": False, "erro": "nao_sou_lider"}

            entrada = {"termo": self.termo, "comando": comando}
            print(f'[{self.nome}] Recebido: {entrada}')
            self.log.append(entrada)

            indice = len(self.log) - 1
            termo_atual = self.termo
            log_atual = list(self.log)
            commit_atual = self.commit_index

        confirmacoes = [1]
        conf_lock = threading.Lock()

        def replica(uri):
            try:
                with Pyro5.api.Proxy(uri) as processo:
                    processo._pyroTimeout = TIMEOUT_RPC * 2

                    if processo.replica_entradas(termo_atual, log_atual, commit_atual):
                        with conf_lock:
                            confirmacoes[0] += 1

            except:
                pass

        threads = []

        for uri in lista_processos:
            if uri == self.uri:
                continue

            t = threading.Thread(target=replica, args=(uri,), daemon=True)
            t.start()
            threads.append(t)

        deadline = time.time() + TIMEOUT_RPC * 2

        for t in threads:
            t.join(timeout=max(0.0, deadline - time.time()))

        if confirmacoes[0] < THRESHOLD_VOTOS:
            return {
                "ok": False,
                "erro": "sem_quorum",
                "confirmacoes": confirmacoes[0]
            }

        with self._lock:
            if self.estado != "lider" or self.termo != termo_atual:
                return {"ok": False, "erro": "perdi_lideranca"}

            if indice > self.commit_index:
                self.commit_index = indice
                print(f"[{self.nome}] Comando '{comando}' efetivado no índice {indice}")
                escrever = True

        if(escrever):
            with open(f"{self.nome}.txt", "a") as f:
                f.write(comando + "\n")

            novo_commit = self.commit_index
            log_atual = list(self.log)

        for uri in lista_processos:
            if uri == self.uri:
                continue

            threading.Thread(target=propaga, args=(uri,), daemon=True).start()

        return {"ok": True, "indice": indice}

    @Pyro5.api.expose
    def status(self):
        with self._lock:
            return {
                "nome": self.nome,
                "estado": self.estado,
                "termo": self.termo,
                "log_len": len(self.log),
                "commit_index": self.commit_index,
                "log": list(self.log)
            }

    def pede_voto(self):
        with self._lock:
            if self.estado != "seguidor":
                return

            self.estado = "candidato"
            self.termo += 1
            self.termo_votado = self.termo

            termo_eleicao = self.termo
            ultimo_indice = len(self.log) - 1
            ultimo_termo_log = self.log[-1]["termo"] if self.log else -1

        print(f"[{self.nome}] Iniciando eleição no termo {termo_eleicao}")

        votos = [1]
        votos_lock = threading.Lock()

        def pede(uri):
            try:
                with Pyro5.api.Proxy(uri) as p:
                    p._pyroTimeout = TIMEOUT_RPC

                    if p.manda_voto(termo_eleicao, ultimo_indice, ultimo_termo_log):
                        with votos_lock:
                            votos[0] += 1

                        print(f"[{self.nome}] Recebi voto de {uri}")

            except:
                pass

        threads = []

        for uri in lista_processos:
            if uri == self.uri:
                continue

            t = threading.Thread(target=pede, args=(uri,), daemon=True)
            t.start()
            threads.append(t)

        deadline = time.time() + TIMEOUT_RPC * 2

        for t in threads:
            t.join(timeout=max(0.0, deadline - time.time()))

        cont_votos = votos[0]
        eleito = False

        with self._lock:
            ainda_candidato_no_termo = (
                self.estado == "candidato" and
                self.termo == termo_eleicao
            )

            if ainda_candidato_no_termo and cont_votos >= THRESHOLD_VOTOS:
                eleito = True

            elif self.estado == "candidato":
                self.estado = "seguidor"

        if eleito:
            self.timer.cancel()
            self.toma_posse(termo_eleicao)
        else:
            self.reseta_timer()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python processo.py <node_id>")
        sys.exit(1)

    node_id = int(sys.argv[1])
    porta = 9000 + node_id

    no = NoProcesso(node_id, porta)

    daemon = Pyro5.api.Daemon(port=porta)
    daemon.register(no, f"processo{node_id}")

    print(f"[{no.nome}] Pronto em {no.uri}")

    daemon.requestLoop()