import { useState } from "react";
import { inserirPromocao, CATEGORIAS } from "./api";

/**
 * Cadastro de promoção pela loja.
 * A loja informa categoria, nome, valor e o e-mail que receberá as
 * notificações (promoção aprovada / virou hot deal). A assinatura digital
 * do evento é feita no backend (gateway/loja) — aqui apenas coletamos os dados.
 */
export default function InserirPromocao({ onSuccess }) {
  const [form, setForm] = useState({ categoria: CATEGORIAS[0], nome: "", valor: "", email: "" });
  const [estado, setEstado] = useState({ tipo: "", msg: "" });
  const [enviando, setEnviando] = useState(false);

  const set = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  async function enviar(e) {
    e.preventDefault();
    setEstado({ tipo: "", msg: "" });

    if (!form.nome.trim() || !form.valor.trim() || !form.email.trim()) {
      setEstado({ tipo: "err", msg: "Preencha nome, valor e e-mail." });
      return;
    }

    setEnviando(true);
    try {
      await inserirPromocao({
        categoria: form.categoria,
        nome: form.nome.trim().toLowerCase(),
        valor: form.valor.trim(),
        email: form.email.trim(),
      });
      setEstado({ tipo: "ok", msg: "Promoção enviada para validação." });
      setForm({ categoria: CATEGORIAS[0], nome: "", valor: "", email: "" });
      if (onSuccess) setTimeout(onSuccess, 900);
    } catch (err) {
      setEstado({ tipo: "err", msg: err.message });
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section>
      <header className="page-head">
        <h1 className="page-title">Cadastrar promoção</h1>
        <p className="page-sub">
          Área da loja · o evento é assinado digitalmente e validado pelo
          MS Promoção antes de ser publicado.
        </p>
      </header>

      <form className="form" onSubmit={enviar}>
        <div className="field">
          <label htmlFor="categoria">Categoria</label>
          <select id="categoria" value={form.categoria} onChange={set("categoria")}>
            {CATEGORIAS.map((c) => (
              <option key={c} value={c}>{c.toUpperCase()}</option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="nome">Produto</label>
          <input id="nome" placeholder="ex.: rtx 4070" value={form.nome} onChange={set("nome")} />
        </div>

        <div className="field">
          <label htmlFor="valor">Valor (R$)</label>
          <input id="valor" placeholder="ex.: 2999.90" value={form.valor} onChange={set("valor")} />
        </div>

        <div className="field">
          <label htmlFor="email">E-mail da loja (notificações)</label>
          <input id="email" type="email" placeholder="loja@exemplo.com" value={form.email} onChange={set("email")} />
        </div>

        {estado.msg && <div className={`alert ${estado.tipo}`}>{estado.msg}</div>}

        <button className="btn" type="submit" disabled={enviando}>
          {enviando ? "Enviando…" : "Cadastrar promoção"}
        </button>
      </form>
    </section>
  );
}
