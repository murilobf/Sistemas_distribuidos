import pika

#Categorias hardcoded. Se sobrar tempo implementar funcionalidade
#pro próprio cliente se inscrever via terminal
categorias = ['promocao.cpu','promocao.ram']

"""
Ao receber uma mensagem de notificação, esta será exibida no terminal.
"""
def callback(ch, method, properties, body):
    print(f" [x] {method.routing_key}:{body}")
    
conexao = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
canal = conexao.channel()

canal.exchange_declare('promocoes', exchange_type='direct')

result = canal.queue_declare(queue='Fila_cliente_B')
queue_name = result.method.queue


for categoria in categorias:
    canal.queue_bind(exchange='promocoes', queue=queue_name, routing_key=categoria)

canal.basic_consume(queue=queue_name,on_message_callback=callback,auto_ack=True)

canal.start_consuming()