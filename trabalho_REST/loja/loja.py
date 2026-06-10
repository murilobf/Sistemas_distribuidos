"""Só pra gerar as chcaves"""

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
    with open('./loja/chave_privada_loja.pem', 'wb') as f:
        f.write(chave_privada.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        ))

def gerar_chave_publica():
    with open('./chaves_publicas/chave_publica_loja.pem', 'wb') as f:
        f.write(chave_privada.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ))

gerar_chave_privada()
gerar_chave_publica()