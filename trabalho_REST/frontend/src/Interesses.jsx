import { useState } from "react";
import { registrarInteresse, cancelarInteresse, CATEGORIAS } from "./api";

/**
 * Gerencia o interesse do consumidor em categorias de produtos.
 * Ao seguir uma categoria, o gateway passa a encaminhar — via SSE — as
 * promoções daquela categoria. O estado de "seguindo" é mantido localmente
 * (localStorage) e sincronizado com o backend a cada ação.
 */
const STORAGE = "promogate:interesses";

function carregarLocal() {
  try {
    return new Set(JSON.parse(localStorage.getItem(STORAGE) || "[]"));
  } catch {
    return new Set();
  }
}

export default function Interesses() {
  const [seguindo, setSeguindo] = useState(carregarLocal);
  const [estado, setEstado] = useState({ tipo: "", msg: "" });
  const [ocupado, setOcupado] = useState(null);

  function persistir(set) {
    localStorage.setItem(STORAGE, JSON.stringify([...set]));
    setSeguindo(new Set(set));
  }

  async function alternar(categoria) {
    const segue = seguindo.has(categoria);
    setOcupado(categoria);
    setEstado({ tipo: "", msg: "" });
    try {
      if (segue) {
        await cancelarInteresse(categoria);
        seguindo.delete(categoria);
        persistir(seguindo);
        setEstado({ tipo: "ok", msg: `Interesse em ${categoria.toUpperCase()} cancelado.` });
      } else {
        await registrarInteresse(categoria);
        seguindo.add(categoria);
        persistir(seguindo);
        setEstado({ tipo: "ok", msg: `Você agora segue ${categoria.toUpperCase()}.` });
      }
    } catch (err) {
      setEstado({ tipo: "err", msg: err.message });
    } finally {
      setOcupado(null);
    }
  }

  return (
    <section>
      <header className="page-head">
        <h1 className="page-title">Meus interesses</h1>
        <p className="page-sub">
          Siga categorias para receber notificações em tempo real (SSE) sobre
          novas promoções e hot deals.
        </p>
      </header>

      {estado.msg && (
        <div className={`alert ${estado.tipo}`} style={{ marginBottom: 16, maxWidth: 460 }}>
          {estado.msg}
        </div>
      )}

      <div className="interest-list">
        {CATEGORIAS.map((c) => {
          const segue = seguindo.has(c);
          return (
            <div className="interest-row" key={c}>
              <span className="label">
                <span className="chip">{c}</span>
                {segue && <span className="following">● seguindo</span>}
              </span>
              <button
                className={`btn ${segue ? "danger" : ""}`}
                disabled={ocupado === c}
                onClick={() => alternar(c)}
              >
                {ocupado === c ? "…" : segue ? "Cancelar" : "Seguir"}
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
