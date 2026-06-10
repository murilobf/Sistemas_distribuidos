import { useEffect, useRef, useState } from "react";
import ListarPromocoes from "./ListarPromocoes";
import InserirPromocao from "./InserirPromocao";
import Votar from "./Votar";
import Interesses from "./Interesses";
import Notificacoes from "./Notificacoes";
import { conectarNotificacoes } from "./api";
import "./index.css";

const TABS = [
  { id: "listar",     label: "Promoções",  glyph: "≋" },
  { id: "inserir",    label: "Inserir",    glyph: "+" },
  { id: "votar",      label: "Votar",      glyph: "◆" },
  { id: "interesses", label: "Interesses", glyph: "★" },
  { id: "alertas",    label: "Alertas",    glyph: "◔" },
];

let _seq = 0;

export default function App() {
  const [tab, setTab] = useState("listar");

  // Notificações recebidas via SSE (persistem enquanto a aba estiver aberta).
  const [feed, setFeed] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [online, setOnline] = useState(false);
  // Quantos alertas chegaram desde a última visita à aba "Alertas".
  const [naoLidas, setNaoLidas] = useState(0);
  const esRef = useRef(null);

  // Abre uma única conexão SSE para toda a aplicação.
  useEffect(() => {
    const es = conectarNotificacoes((payload, tipo) => {
      const item = {
        id: ++_seq,
        tipo,
        titulo: tituloPara(tipo, payload),
        texto: textoPara(payload),
        em: new Date(),
      };
      setFeed((f) => [item, ...f].slice(0, 50));
      setToasts((t) => [...t, item]);
      setNaoLidas((n) => n + 1);
      // Auto-fecha o toast após alguns segundos.
      setTimeout(() => setToasts((t) => t.filter((x) => x.id !== item.id)), 6000);
    });
    esRef.current = es;
    es.onopen = () => setOnline(true);
    es.onerror = () => setOnline(false);
    return () => es.close();
  }, []);

  function abrir(id) {
    setTab(id);
    if (id === "alertas") setNaoLidas(0);
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">PG</span>
          <span className="brand-name">Promo<br />Gate</span>
        </div>

        <nav className="sidenav">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`sidenav-item ${tab === t.id ? "active" : ""}`}
              onClick={() => abrir(t.id)}
            >
              <span className="sidenav-glyph">{t.glyph}</span>
              <span className="sidenav-label">{t.label}</span>
              {t.id === "alertas" && naoLidas > 0 && (
                <span className="sidenav-badge">{naoLidas}</span>
              )}
              {tab === t.id && <span className="sidenav-bar" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className={`status-dot ${online ? "" : "offline"}`} />
          <span className="status-text">
            {online ? "SSE conectado" : "SSE offline"} · :9999
          </span>
        </div>
      </aside>

      <main className="content">
        {tab === "listar"     && <ListarPromocoes />}
        {tab === "inserir"    && <InserirPromocao onSuccess={() => abrir("listar")} />}
        {tab === "votar"      && <Votar />}
        {tab === "interesses" && <Interesses />}
        {tab === "alertas"    && <Notificacoes itens={feed} />}
      </main>

      {/* Toasts de notificação SSE — aparecem em qualquer aba. */}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.tipo === "hotdeal" ? "hotdeal" : ""}`}>
            <span className="toast-icon">{t.tipo === "hotdeal" ? "🔥" : "🔔"}</span>
            <div className="toast-body">
              <span className="toast-title">{t.titulo}</span>
              <span className="toast-text">{t.texto}</span>
            </div>
            <button
              className="toast-close"
              onClick={() => setToasts((arr) => arr.filter((x) => x.id !== t.id))}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function tituloPara(tipo, payload) {
  if (tipo === "hotdeal") return "🔥 Novo hot deal!";
  if (payload?.categoria) return `Nova promoção · ${String(payload.categoria).toUpperCase()}`;
  return "Notificação";
}

function textoPara(payload) {
  if (!payload) return "";
  if (payload.mensagem) return payload.mensagem;
  const nome = payload.nome ? `${payload.nome}` : "promoção";
  const valor = payload.valor ? ` — R$ ${payload.valor}` : "";
  return `${nome}${valor}`;
}
