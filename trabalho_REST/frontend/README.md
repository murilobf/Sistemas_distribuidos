# PromoGate — Frontend

Frontend web (React + Vite) do sistema distribuído de promoções. Comunica-se
com o backend **exclusivamente** via API REST (MS Gateway) e recebe
notificações em tempo real via **SSE** — atendendo aos requisitos do trabalho.

> Linguagem do frontend (JavaScript/React) é diferente do backend (Python),
> conforme exigido pelo enunciado.

## Como rodar

```bash
cd frontend
npm install      # apenas na primeira vez
npm run dev      # http://localhost:5173
```

O Vite faz proxy de `/api` e `/sse` para o gateway Flask em `localhost:9999`
(ver `vite.config.js`). Suba o `gateway/gateway.py` em paralelo para ver dados
reais — a interface carrega mesmo sem o backend (mostra estados vazios/erro).

Build de produção: `npm run build` (gera `dist/`); pré-visualizar: `npm run preview`.

## Funcionalidades (requisitos do PDF)

| Requisito (consumidor)                       | Onde                         |
|----------------------------------------------|------------------------------|
| Consultar promoções publicadas               | aba **Promoções**            |
| Votar positivo/negativo                       | aba **Votar**                |
| Registrar interesse em categorias             | aba **Interesses**           |
| Cancelar interesse em categorias              | aba **Interesses**           |
| Receber notificações SSE (sem refresh)        | toasts + aba **Alertas**     |
| Destaque de *hot deals*                       | realce nos cards             |
| (Loja) cadastrar promoção + e-mail            | aba **Inserir**              |

As notificações SSE aparecem automaticamente como *toasts* em qualquer aba e
ficam registradas na aba **Alertas** — sem atualização manual da página.

## Contrato REST esperado do MS Gateway

O frontend chama os endpoints abaixo (nomes alinhados ao `gateway/gateway.py`).
Ao concluir o backend em Python, basta implementá-los respeitando este formato:

| Método  | Rota                                | Corpo enviado / resposta                                   |
|---------|-------------------------------------|------------------------------------------------------------|
| GET     | `/api/listar_promocoes`             | → `[{categoria, nome, valor, votos?, destaque?}, ...]`     |
| POST    | `/api/inserir_promocao`             | ← `{categoria, nome, valor, email}`                        |
| PATCH   | `/api/votar`                        | ← `{nome, voto: 1 \| -1}`                                  |
| POST    | `/api/registra_interesse`           | ← `{cliente, categoria}`                                   |
| DELETE  | `/api/remove_interesse`             | ← `{cliente, categoria}`                                   |
| GET     | `/sse/notificacoes?cliente=<id>`    | → stream `text/event-stream`                               |

### SSE — eventos consumidos

O `EventSource` escuta a mensagem padrão e os eventos nomeados `hotdeal`,
`categoria` e `promocao`. O gateway deve enviar `data:` em JSON, ex.:

```
event: hotdeal
data: {"nome":"rtx 4070","categoria":"gpu","valor":"2999.90","mensagem":"Virou hot deal!"}
```

O campo `cliente` (query string do SSE e corpo dos interesses) é um ID anônimo
gerado e persistido no navegador (`localStorage`), usado pelo gateway para
filtrar as notificações por interesse de cada usuário.

> **Atenção sobre o gateway atual:** em `gateway.py`, `inserir_promocao` e
> `votar_promocao` ainda usam `input()` e leem os dados do terminal. Para o
> frontend funcionar, troque por leitura de `request.json` (categoria/nome/
> valor/email e nome/voto). Faltam também os endpoints de interesse e o de SSE.
