import pika
import threading
import json
from flask import Flask, request, Response, jsonify, stream_with_context
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
import queue

#Lista local de promoções validadas
promocoes_aprovadas = []

#Lista de clientes e seus interesses
interesses = {}

#Lista de conecões (pro SSE)
conexoes = {}

app = Flask(__name__)

chave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)

def gerar_chave_privada():
    with open('./gateway/chave_privada_gateway.pem', 'wb') as f:
        f.write(chave_privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ))

def gerar_chave_publica():
    with open('./chaves_publicas/chave_publica_gateway.pem', 'wb') as f:
        f.write(chave_privada.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ))

def gerar_hash(conteudo) -> str:
    if isinstance(conteudo, str):
        conteudo = conteudo.encode('utf-8')
    elif isinstance(conteudo, dict):
        conteudo = json.dumps(conteudo, separators=(',', ':'), sort_keys=True).encode('utf-8')
        
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(conteudo)
    return digest.finalize().hex()

#Separado pra não bloquear o menu
def iniciar_consumidor():
    canal.basic_consume(queue=queue_name, on_message_callback=callback_promocao_publicada, auto_ack=True)
    canal.start_consuming()

def callback_promocao_publicada(ch, method, properties, body):
    #Extrair a promoção aprovada de body e inserir ele na lista de promocoes_aprovadas
    print(f"{method.routing_key}: {body}")

    json_body = json.loads(body)
    assinatura_promocao = json_body['assinatura']
    payload_promocao = json_body['payload']
    hash_promocao = json_body['hash']

    hash_recebido = gerar_hash(payload_promocao)

    if(hash_promocao != hash_recebido):
        print('hash')
        return 400
    else:
        print('hash passou')

    #json_payload_promocao = json.dumps(payload_promocao).encode()
    try:
        #chave_publica_promocao.verify(bytes.fromhex(assinatura_promocao), json_payload_promocao, padding.PKCS1v15(), hashes.SHA256())
        promocoes_aprovadas.append(payload_promocao)
        for cliente, fila in list(conexoes.items()):
            if(payload_promocao['categoria'] in interesses.get(cliente, set()) or payload_promocao.get('destaque')):
                fila.put(('promocao',payload_promocao))

    except Exception as e:
        print(f"ERRO: {e}")
        return 

@app.route('/api/listar_promocoes', methods=['GET'])
def listar_promocoes():
    return jsonify(promocoes_aprovadas), 200
        
@app.route('/api/inserir_promocao', methods=['POST'])
def inserir_promocao():
    dados = request.json
    categoria = dados.get('categoria')
    nome = dados.get('nome')
    valor = dados.get('valor')
    email = dados.get('email')

    promocao = {}
    promocao['categoria'] = categoria
    promocao['nome'] = nome 
    promocao['valor'] = valor
    promocao['email'] = email

    json_conteudo = json.dumps(promocao, sort_keys=True).encode()
    
    assinatura = chave_privada_loja.sign(json_conteudo, padding.PKCS1v15(), hashes.SHA256())
    hash_conteudo = gerar_hash(promocao)

    payload = json.dumps({'payload':promocao, 'assinatura':assinatura.hex(), 'hash':hash_conteudo}, sort_keys=True)
    
    canal.basic_publish(exchange='promocoes', routing_key='promocao.recebida', body=payload)
    return jsonify(payload),200

@app.route('/api/votar', methods=['PATCH'])
def votar_promocao():

    try:
        dados = request.json
        voto = dados.get('voto')

        nome_produto = dados.get('nome')

        promocao = next((promocao for promocao in promocoes_aprovadas if promocao['nome'] == nome_produto), None)

        promocao['voto'] = voto

        json_conteudo = json.dumps(promocao, sort_keys=True).encode()
        assinatura = chave_privada_loja.sign(json_conteudo, padding.PKCS1v15(), hashes.SHA256())
        hash_conteudo = gerar_hash(promocao)

        payload = json.dumps({'payload':promocao, 'assinatura':assinatura.hex(), 'hash': hash_conteudo}, sort_keys=True)

        canal.basic_publish(exchange='promocoes', routing_key='promocao.voto', body=payload)
        return jsonify({"ok": True}), 200
    
    except Exception as e:
        return jsonify({"ok": False}), 400

@app.route('/sse/notificacoes')
def sse_notifica():
    cliente = request.args.get('cliente')          
    fila = queue.Queue()
    conexoes[cliente] = fila
    interesses.setdefault(cliente, set())

    @stream_with_context
    def notifica():
        # pinga
        yield "event: ping\ndata: conectado\n\n"
        try:
            while True:
                evento, dados = fila.get()
                print("=================")
                print(evento)
                yield f"event: {evento}\ndata: {json.dumps(dados)}\n\n"
        finally:
            conexoes.pop(cliente, None)             

    return Response(notifica(), mimetype='text/event-stream')   


@app.route('/api/registra_interesse', methods=['POST'])
def registrar_interesse():
    dados = request.json
    cliente = dados.get('cliente')
    categoria = dados.get('categoria')

    interesses.setdefault(cliente, set()).add(categoria)

    return jsonify({"ok": True}), 200

@app.route('/api/remove_interesse', methods=['DELETE'])
def remover_intereses():
    dados = request.json
    cliente = dados.get('cliente')
    categoria = dados.get('categoria')

    interesses.get(cliente, set()).discard(categoria)

    return jsonify({"ok": True}),200
"""
Se deixar descomentado eles regeram as chaves novamente, então os serviços que usam as chaves podem estar com a chave antiga 
gerar_chave_privada()
gerar_chave_publica()
"""

conexao = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
canal = conexao.channel()

canal.exchange_declare('promocoes', exchange_type='direct')

#Fila
result = canal.queue_declare(queue='Fila_Gateway', exclusive=True)
queue_name = result.method.queue

#Consumidor
canal.queue_bind(exchange='promocoes', queue=queue_name, routing_key='promocao.publicada')
canal.queue_bind(exchange='promocoes', queue=queue_name, routing_key='promocao.destaque')

thread_consumidor = threading.Thread(target=iniciar_consumidor, daemon=True)
thread_consumidor.start()

#Leitura das chaves publicas e privadas utilizadas
with open('./chaves_publicas/chave_publica_promocao.pem', 'rb') as f:
    chave_publica_promocao = serialization.load_pem_public_key(f.read())

with open('./loja/chave_privada_loja.pem', 'rb') as f:
    chave_privada_loja = serialization.load_pem_private_key(f.read(), password=None)

app.run(host='localhost', port=9999, threaded=True)