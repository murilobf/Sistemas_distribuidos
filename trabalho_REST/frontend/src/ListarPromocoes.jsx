import { useEffect, useState } from "react";
import { listarPromocoes } from "./api";

/**
 * Consulta e exibe as promoções publicadas pelo gateway.
 * Promoções com `destaque` (hot deal) recebem realce visual.
 * Atualiza automaticamente a cada 8s além do refresh manual.
 */
export default function ListarPromocoes() {
  const [promocoes, setPromocoes] = useState([]);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);

  async function carregar() {
    try {
      const dados = await listarPromocoes();
      setPromocoes(Array.isArray(dados) ? dados : []);
      setErro("");
    } catch (e) {
      setErro(e.message);
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    const id = setInterval(carregar, 8000);
    return () => clearInterval(id);
  }, []);

  return (
    <section>
      <header className="page-head">
        <h1 className="page-title">Promoções publicadas</h1>
        <p className="page-sub">
          Ofertas validadas pelo sistema · destaques marcados como{" "}
          <strong>hot deal</strong>.
        </p>
      </header>

      <div style={{ marginBottom: 18 }}>
        <button className="btn ghost" onClick={carregar} disabled={carregando}>
          ↻ Atualizar
        </button>
      </div>

      {erro && <div className="alert err">Não foi possível carregar: {erro}</div>}

      {!erro && carregando && <p className="muted">Carregando…</p>}

      {!erro && !carregando && promocoes.length === 0 && (
        <div className="empty">Nenhuma promoção publicada ainda.</div>
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
              <div className="card-price">{formatarValor(p.valor)}</div>
              {(p.votos ?? p.score ?? p.voto) !== undefined && (
                <div className="card-votes">
                  👍 {p.votos ?? p.score ?? p.voto} voto(s)
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function formatarValor(valor) {
  if (valor == null || valor === "") return "—";
  const num = Number(String(valor).replace(",", "."));
  if (Number.isNaN(num)) return String(valor);
  return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
