import { useEffect, useState } from "react";
import { listarPromocoes, votarPromocao } from "./api";

/**
 * Votação do consumidor. Lista as promoções publicadas e permite votar
 * positivo (+1) ou negativo (-1). O voto é publicado pelo gateway no
 * RabbitMQ (promocao.voto) e processado pelo MS Ranking.
 */
export default function Votar() {
  const [promocoes, setPromocoes] = useState([]);
  const [erro, setErro] = useState("");
  const [estado, setEstado] = useState({ tipo: "", msg: "" });
  const [votandoNome, setVotandoNome] = useState(null);

  async function carregar() {
    try {
      const dados = await listarPromocoes();
      setPromocoes(Array.isArray(dados) ? dados : []);
      setErro("");
    } catch (e) {
      setErro(e.message);
    }
  }

  useEffect(() => { carregar(); }, []);

  async function votar(nome, voto) {
    setVotandoNome(nome + voto);
    setEstado({ tipo: "", msg: "" });
    try {
      await votarPromocao({ nome, voto });
      setEstado({
        tipo: "ok",
        msg: `Voto ${voto === 1 ? "positivo" : "negativo"} registrado para "${nome}".`,
      });
      carregar();
    } catch (err) {
      setEstado({ tipo: "err", msg: err.message });
    } finally {
      setVotandoNome(null);
    }
  }

  return (
    <section>
      <header className="page-head">
        <h1 className="page-title">Votar em promoções</h1>
        <p className="page-sub">
          Vote positivo ou negativo. Promoções muito votadas viram{" "}
          <strong>hot deals</strong>.
        </p>
      </header>

      {erro && <div className="alert err">Não foi possível carregar: {erro}</div>}
      {estado.msg && (
        <div className={`alert ${estado.tipo}`} style={{ marginBottom: 16 }}>
          {estado.msg}
        </div>
      )}

      {!erro && promocoes.length === 0 && (
        <div className="empty">Nenhuma promoção disponível para votação.</div>
      )}

      <div className="grid">
        {promocoes.map((p, i) => {
          const hot = !!(p.destaque || p.hotdeal || p.hot_deal);
          return (
            <article className={`card ${hot ? "hot" : ""}`} key={p.id ?? `${p.nome}-${i}`}>
              <div className="card-top">
                <span className="chip">{p.categoria}</span>
                {hot && <span className="badge-hot">🔥 HOT DEAL</span>}
              </div>
              <div className="card-name">{p.nome}</div>
              <div className="vote-row">
                <button
                  className="btn up"
                  disabled={votandoNome === p.nome + 1}
                  onClick={() => votar(p.nome, 1)}
                >
                  👍 Positivo
                </button>
                <button
                  className="btn down"
                  disabled={votandoNome === p.nome + -1}
                  onClick={() => votar(p.nome, -1)}
                >
                  👎 Negativo
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
