/**
 * Histórico das notificações recebidas via SSE durante a sessão.
 * Os itens são alimentados pelo App (conexão SSE única) e exibidos aqui.
 */
export default function Notificacoes({ itens }) {
  return (
    <section>
      <header className="page-head">
        <h1 className="page-title">Alertas em tempo real</h1>
        <p className="page-sub">
          Notificações recebidas via SSE conforme seus interesses e os hot deals.
        </p>
      </header>

      {(!itens || itens.length === 0) && (
        <div className="empty">
          Nenhuma notificação ainda. Siga categorias em <strong>Interesses</strong>{" "}
          para começar a receber.
        </div>
      )}

      <div className="feed">
        {itens.map((n) => (
          <div className={`feed-item ${n.tipo === "hotdeal" ? "hotdeal" : ""}`} key={n.id}>
            <span className="dot" />
            <div>
              <div className="toast-title">{n.titulo}</div>
              <div className="toast-text">{n.texto}</div>
            </div>
            <span className="feed-time">{horario(n.em)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function horario(d) {
  const data = d instanceof Date ? d : new Date(d);
  return data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}
