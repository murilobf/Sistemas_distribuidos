import Pyro5
import Pyro5.api
import sys
import time


def localiza_lider():
    with Pyro5.api.locate_ns() as ns:
        return ns.lookup("lider")


def envia_comando(comando, tentativas=4):
    for tentativa in range(1, tentativas + 1):
        try:
            uri = localiza_lider()
        except Exception as e:
            print(f"[cliente] (tentativa {tentativa}) NS sem 'lider': {e}")
            time.sleep(0.6)
            continue

        try:
            with Pyro5.api.Proxy(uri) as lider:
                lider._pyroTimeout = 3.0
                resposta = lider.recebe_comando(comando)
        except Exception as e:
            print(f"[cliente] (tentativa {tentativa}) Erro chamando líder {uri}: {e}")
            time.sleep(0.6)
            continue

        if resposta.get("ok"):
            print(f"[cliente] OK: '{comando}' efetivado no índice {resposta['indice']}")
            return resposta

        print(f"[cliente] (tentativa {tentativa}) Falha: {resposta}")
        time.sleep(0.6)

    print(f"[cliente] Desisti após {tentativas} tentativas")
    return None


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        envia_comando(" ".join(sys.argv[1:]))
    else:
        print("Cliente Raft (digite 'sair' para encerrar)")
        while True:
            try:
                cmd = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not cmd or cmd == "sair":
                break
            envia_comando(cmd)
