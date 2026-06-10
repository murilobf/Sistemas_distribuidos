import pika
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding

chave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)

def gerar_chave_privada():
    with open('./promocao/chave_privada_promocao.pem', 'wb') as f:
        f.write(chave_privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ))

def gerar_chave_publica():
    with open('./chaves_publicas/chave_publica_promocao.pem', 'wb') as f:
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

#Validar a promoção e então enviá-la para o ms de notificação
def callback_promocao_recebida(ch, method, properties, body):
    print(f"{method.routing_key}: {body}")

    json_body = json.loads(body)
    assinatura_gateway = json_body['assinatura']
    payload_gateway = json_body['payload']
    hash_gateway = json_body['hash']

    hash_recebido = gerar_hash(payload_gateway)

    if(hash_gateway != hash_recebido):
        print('HASH INVÁLIDO!!')
        return

    #Validação de erros
    if((payload_gateway['categoria'] not in ['ram','cpu','gpu'])
        or (not payload_gateway['nome'])
        or (not payload_gateway['valor'])
        or (int(payload_gateway['valor']) < 0)):
        return 

    json_payload_gateway = json.dumps(payload_gateway).encode()

    #Verifica se a assinatura é válida
    try: 
        chave_publica_gateway.verify(bytes.fromhex(assinatura_gateway), json_payload_gateway, padding.PKCS1v15(), hashes.SHA256())

        #Assina com a chave de MS promocao
        assinatura = chave_privada_promocao.sign(json_payload_gateway, padding.PKCS1v15(), hashes.SHA256())
        hash_conteudo = gerar_hash(payload_gateway)

        payload = json.dumps({'payload':payload_gateway, 'assinatura':assinatura.hex(), 'hash': hash_conteudo}, sort_keys=True)

        #Emite a promoção para o MS de notificação
        canal.basic_publish(exchange='promocoes', routing_key='promocao.publicada', body=payload)

    except Exception as e:
        print(f'Erro: {e} \n ASSINATURA INVÁLIDA')

"""
Se deixar descomentado eles regeram as chaves novamente, então os serviços que usam as chaves podem estar com a chave antiga 
gerar_chave_privada()
gerar_chave_publica()
"""

#Leitura das chaves publicas e privadas utilizadas
with open('./chaves_publicas/chave_publica_gateway.pem', 'rb') as f:
    chave_publica_gateway = serialization.load_pem_public_key(f.read())

with open('./promocao/chave_privada_promocao.pem', 'rb') as f:
    chave_privada_promocao = serialization.load_pem_private_key(f.read(), password=None)

conexao = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
canal = conexao.channel()

canal.exchange_declare('promocoes', exchange_type='direct')

#Fila
result = canal.queue_declare(queue='Fila_Promocao', exclusive=True)
queue_name = result.method.queue

#Consumidor
canal.queue_bind(exchange='promocoes', queue=queue_name, routing_key='promocao.recebida')

canal.basic_consume(queue=queue_name, on_message_callback=callback_promocao_recebida, auto_ack=True)

canal.start_consuming()
