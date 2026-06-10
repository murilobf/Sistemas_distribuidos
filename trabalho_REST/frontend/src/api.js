const BASE = import.meta.env.VITE_API_URL ?? "";

export const CATEGORIAS = ["ram", "cpu", "gpu"];

export function getClienteId() {
  let id = localStorage.getItem("promogate:cliente");
  if (!id) {
    id =
      (crypto.randomUUID && crypto.randomUUID()) ||
      `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    localStorage.setItem("promogate:cliente", id);
  }
  return id;
}

async function http(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message ?? body.erro ?? `HTTP ${res.status}`);
  }
  // Tolera respostas vazias (204 / corpo não-JSON).
  return res.json().catch(() => ({}));
}

export const listarPromocoes = () => http("/api/listar_promocoes");

export const inserirPromocao = (dados) =>
  http("/api/inserir_promocao", {
    method: "POST",
    body: JSON.stringify(dados),
  });

export const votarPromocao = (dados) =>
  http("/api/votar", { method: "PATCH", body: JSON.stringify(dados) });

export const registrarInteresse = (categoria) =>
  http("/api/registra_interesse", {
    method: "POST",
    body: JSON.stringify({ cliente: getClienteId(), categoria }),
  });

export const cancelarInteresse = (categoria) =>
  http("/api/remove_interesse", {
    method: "DELETE",
    body: JSON.stringify({ cliente: getClienteId(), categoria }),
  });

export function conectarNotificacoes(onMessage) {
  const url = `${BASE}/sse/notificacoes?cliente=${encodeURIComponent(getClienteId())}`;
  const es = new EventSource(url);
  const handle = (tipo) => (ev) => {
    let payload;
    try {
      payload = JSON.parse(ev.data);
    } catch {
      payload = { mensagem: ev.data };
    }
    tipo = payload?.destaque || 'promocao';
    onMessage(payload, tipo);
  };

  es.onmessage = handle("notificacao");
  es.addEventListener("hotdeal", handle("hotdeal"));
  es.addEventListener("categoria", handle("categoria"));
  es.addEventListener("promocao", handle("promocao"));

  return es;
}
