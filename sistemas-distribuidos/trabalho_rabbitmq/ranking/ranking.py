import pika
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding

THRESHOLD = 2
qtde_votos_total = 0

promocoes_aprovadas = []

chave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)

def gerar_chave_privada():
    with open('./ranking/chave_privada_ranking.pem', 'wb') as f:
        f.write(chave_privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ))

def gerar_chave_publica():
    with open('./chaves_publicas/chave_publica_ranking.pem', 'wb') as f:
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

def callback_voto(ch, method, properties, body):
    print(f" [x] {method.routing_key}:{body}")

    json_body = json.loads(body)
    assinatura_gateway = json_body['assinatura']
    payload_gateway = json_body['payload']
    hash_gateway = json_body['hash']

    hash_recebido = gerar_hash(payload_gateway)

    if(hash_gateway != hash_recebido):
        print('HASH INVÁLIDO!!')
        return

    json_payload_gateway = json.dumps(payload_gateway).encode()

    try:
        chave_publica_gateway.verify(bytes.fromhex(assinatura_gateway), json_payload_gateway, padding.PKCS1v15(), hashes.SHA256())
       
        index = next((i for i, p in enumerate(promocoes_aprovadas) if p['nome'] == payload_gateway['nome']), None)

        if index is None:
            promocoes_aprovadas.append({'nome': payload_gateway['nome'], 'valor_voto': 0, 'qtde_votos': 0})
            index = len(promocoes_aprovadas) - 1

        voto = int(payload_gateway['voto'])

        promocoes_aprovadas[index]['valor_voto'] += voto
        promocoes_aprovadas[index]['qtde_votos'] += 1
        global qtde_votos_total
        qtde_votos_total += 1
        
        print(f'Promoção: {promocoes_aprovadas[index]}')
        print(f'Quantidade total de votos: {qtde_votos_total}')

        if(promocoes_aprovadas[index]['valor_voto'] >= THRESHOLD):
            payload_gateway['destaque'] = 'hot deal'
            json_conteudo = json.dumps(payload_gateway, sort_keys=True).encode()
            assinatura = chave_privada_ranking.sign(json_conteudo, padding.PKCS1v15(), hashes.SHA256())
            hash_conteudo = gerar_hash(payload_gateway)

            payload = json.dumps({'payload':payload_gateway, 'assinatura':assinatura.hex(), 'hash': hash_conteudo}, sort_keys=True)


            canal.basic_publish(exchange='promocoes', routing_key='promocao.destaque', body=payload)
        else:
            print('b')

    except Exception as e:
        print(f'Assinatura inválida ou erro: {e}')
 

   
    
'''gerar_chave_privada()
gerar_chave_publica()'''

with open('./chaves_publicas/chave_publica_gateway.pem', 'rb') as f:
    chave_publica_gateway = serialization.load_pem_public_key(f.read())

with open('./ranking/chave_privada_ranking.pem', 'rb') as f:
    chave_privada_ranking = serialization.load_pem_private_key(f.read(), password=None)

conexao = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
canal = conexao.channel()

canal.exchange_declare('promocoes', exchange_type='direct')

result = canal.queue_declare(queue='Fila_Ranking', exclusive=True)
queue_name = result.method.queue

#Consumidor
canal.queue_bind(exchange='promocoes', queue=queue_name, routing_key='promocao.voto')

canal.basic_consume(queue=queue_name,on_message_callback=callback_voto,auto_ack=True)

canal.start_consuming()

