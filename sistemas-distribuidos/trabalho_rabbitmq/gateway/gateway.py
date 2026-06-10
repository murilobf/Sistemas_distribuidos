import pika
import threading
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding

#Mantém uma lista local de promoções validadas
promocoes_aprovadas = []

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
        print("HASH INVÁLIDO!!")
        return

    json_payload_promocao = json.dumps(payload_promocao).encode()

    try:
        chave_publica_promocao.verify(bytes.fromhex(assinatura_promocao), json_payload_promocao, padding.PKCS1v15(), hashes.SHA256())
        promocoes_aprovadas.append(payload_promocao)
    except Exception as e:
        print('Assinatura inválida')

#Falta terminar só de especificar os campos de promoção
def listar_promocoes():
    print("##############################")
    print("PROMOÇÕES APROVADAS ATÉ ENTÃO:")
    print("#============================#")

    for promocao in promocoes_aprovadas:
        print(promocao)
        
    print("#============================#")

def inserir_promocao():
    print("Iniciando inserção da promoção")
    print("Categorias disponíveis: ram;cpu;gpu")
    print("Insira a categoria que deseja inserir")
    categoria = input('>').strip().lower()

    if(categoria not in ['ram','cpu','gpu']):
        print("CATEGORIA INVÁLIDA!!")
        return
    print("Insira o nome do produto que deseja inserir")
    nome = input('>').strip().lower()
    
    print("Digite o valor do produto na promoção")
    valor = input('>').strip().lower()

    promocao = {}
    promocao['categoria'] = categoria
    promocao['nome'] = nome 
    promocao['valor'] = valor

    json_conteudo = json.dumps(promocao, sort_keys=True).encode()
    
    assinatura = chave_privada_gateway.sign(json_conteudo, padding.PKCS1v15(), hashes.SHA256())
    hash_conteudo = gerar_hash(promocao)

    payload = json.dumps({'payload':promocao, 'assinatura':assinatura.hex(), 'hash':hash_conteudo}, sort_keys=True)
    
    canal.basic_publish(exchange='promocoes', routing_key='promocao.recebida', body=payload)
    

def votar_promocao():
    print("Insira o nome do produto que deseja votar")
    nome_produto = input('>').strip().lower()

    promocao = next((promocao for promocao in promocoes_aprovadas if promocao['nome'] == nome_produto), None)

    if(not promocao):
        print("PROMOÇÃO INVÁLIDA!!")
        return
    
    print("Digite 1 para um voto positivo e -1 para um negativo")
    voto = int(input('>').strip())

    if(voto != -1 and voto != 1):
        print("VOTO INVÁLIDO!!")
        return
    
    promocao['voto'] = voto

    json_conteudo = json.dumps(promocao, sort_keys=True).encode()
    assinatura = chave_privada_gateway.sign(json_conteudo, padding.PKCS1v15(), hashes.SHA256())
    hash_conteudo = gerar_hash(promocao)

    payload = json.dumps({'payload':promocao, 'assinatura':assinatura.hex(), 'hash': hash_conteudo}, sort_keys=True)

    canal.basic_publish(exchange='promocoes', routing_key='promocao.voto', body=payload)

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

thread_consumidor = threading.Thread(target=iniciar_consumidor, daemon=True)
thread_consumidor.start()

#Leitura das chaves publicas e privadas utilizadas
with open('./chaves_publicas/chave_publica_promocao.pem', 'rb') as f:
    chave_publica_promocao = serialization.load_pem_public_key(f.read())

with open('./gateway/chave_privada_gateway.pem', 'rb') as f:
    chave_privada_gateway = serialization.load_pem_private_key(f.read(), password=None)


while True:
    print('======================================================')
    print('DIGITE 1 PARA LISTAR TODAS AS PROMOÇÕES')
    print('DIGITE 2 PARA INSERIR UM NOVO PRODUTO EM UMA CATEGORIA')
    print('DIGITE 3 PARA VOTAR EM UMA PROMOÇÃO')
    print('======================================================\n')
    opcao = input('>').strip()
    print(opcao)
    if opcao == '1':
        listar_promocoes()
    elif opcao == '2':
        inserir_promocao()
    elif opcao == '3':
        votar_promocao()
    else:
        print('NÚMERO INVÁLIDO!!')