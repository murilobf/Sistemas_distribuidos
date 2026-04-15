import pika
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding

chave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)

def gerar_chave_privada():
    with open('./notificacao/chave_privada_notificacao.pem', 'wb') as f:
        f.write(chave_privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ))

def gerar_chave_publica():
    with open('./chaves_publicas/chave_publica_notificacao.pem', 'wb') as f:
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

def verificar_assinatura(assinatura, payload):
    chaves = [chave_publica_promocao, chave_publica_ranking]  
    for chave in chaves:
        try:
            chave.verify(bytes.fromhex(assinatura), payload, padding.PKCS1v15(), hashes.SHA256())
            return True  
        except Exception:
            continue  
    return False  

#Validar a promoção e então enviá-la para os interessados
def callback_promocao_recebida(ch, method, properties, body):
    print(f"{method.routing_key}: {body}")

    json_body = json.loads(body)
    assinatura_promocao = json_body['assinatura']
    payload_promocao = json_body['payload']
    hash_promocao = json_body['hash']

    hash_recebido = gerar_hash(payload_promocao)

    if(hash_promocao != hash_recebido):
        print('HASH INVÁLIDO!!')
        return

    json_payload_promocao = json.dumps(payload_promocao).encode()

    try:
        if(not verificar_assinatura(assinatura_promocao,json_payload_promocao)):
            print(f'Assinatura inválida')
            return

        routing_key = f"promocao.{payload_promocao['categoria']}"
        canal.basic_publish(exchange='promocoes', routing_key=routing_key, body=json.dumps(payload_promocao))

    except Exception as e:
        print(f'Assinatura inválida ou erro: {e}')

"""
Se deixar descomentado eles regeram as chaves novamente, então os serviços que usam as chaves podem estar com a chave antiga 
gerar_chave_privada()
gerar_chave_publica()
"""

#Leitura das chaves publicas e privadas utilizadas
with open('./chaves_publicas/chave_publica_promocao.pem', 'rb') as f:
    chave_publica_promocao = serialization.load_pem_public_key(f.read())

with open('./chaves_publicas/chave_publica_ranking.pem', 'rb') as f:
    chave_publica_ranking = serialization.load_pem_public_key(f.read())

with open('./notificacao/chave_privada_notificacao.pem', 'rb') as f:
    chave_privada_gateway = serialization.load_pem_private_key(f.read(), password=None)

conexao = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
canal = conexao.channel()

canal.exchange_declare('promocoes', exchange_type='direct')

#Fila
result = canal.queue_declare(queue='Fila_Notificacao', exclusive=True)
queue_name = result.method.queue

#Consumidores
canal.queue_bind(exchange='promocoes', queue=queue_name, routing_key='promocao.publicada')
canal.queue_bind(exchange='promocoes', queue=queue_name, routing_key='promocao.destaque')
canal.basic_consume(queue=queue_name, on_message_callback=callback_promocao_recebida, auto_ack=True)

canal.start_consuming()
