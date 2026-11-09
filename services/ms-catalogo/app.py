"""ms-catalogo — vitrine de vinhos da Vinheria Agnello.

- POST /v1/auth/token : troca usuário e senha (HTTP Basic) por um JWT de 15 minutos.
- GET  /v1/vinhos     : exige JWT com escopo "catalogo:ler"; consulta o ms-estoque
                        por HTTPS com mTLS e um JWT de serviço próprio.
O HTTP sem criptografia (porta 8001) só é ligado com PERMITIR_HTTP=sim, para a
demonstração com o Wireshark.
"""
import base64
import binascii
import hmac
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comum"))
from seguranca import (TokenInvalido, contexto_tls_cliente, contexto_tls_servidor,  # noqa: E402
                       gerar_token, ler_segredo, validar_token)

SEGREDO = ler_segredo(os.environ.get("JWT_SEGREDO"))
USUARIO = os.environ.get("DEMO_USUARIO", "sommelier")
SENHA = os.environ.get("DEMO_SENHA", "")
PORTA_HTTPS = int(os.environ.get("PORTA_HTTPS", "8443"))
PORTA_HTTP = int(os.environ.get("PORTA_HTTP", "8001"))
PERMITIR_HTTP = os.environ.get("PERMITIR_HTTP", "nao").lower() == "sim"
ESTOQUE_URL = os.environ.get("ESTOQUE_URL", "https://estoque.vinheria.internal:8443")
CERTS = os.environ.get("DIR_CERTS", "/certs")

if len(SENHA) < 8 or SENHA.startswith("troque"):
    raise SystemExit("DEMO_SENHA ausente ou fraca: defina no .env uma senha com 8+ caracteres")

CATALOGO = [
    {"sku": "VA-0001", "nome": "Catena Malbec 2021", "tipo": "Tinto", "pais": "Argentina", "preco": 189.00},
    {"sku": "VA-0002", "nome": "Cloudy Bay Sauvignon Blanc 2023", "tipo": "Branco", "pais": "Nova Zelândia", "preco": 329.00},
    {"sku": "VA-0003", "nome": "Dom Pérignon 2013", "tipo": "Espumante", "pais": "França", "preco": 2490.00},
    {"sku": "VA-0004", "nome": "Quinta do Crasto Reserva 2020", "tipo": "Tinto", "pais": "Portugal", "preco": 459.00},
    {"sku": "VA-0006", "nome": "Barca Velha 2015", "tipo": "Tinto", "pais": "Portugal", "preco": 5900.00},
]

# Cliente TLS para falar com o ms-estoque: confere o certificado dele e apresenta o próprio (mTLS)
CONTEXTO_ESTOQUE = contexto_tls_cliente(f"{CERTS}/ca.crt", f"{CERTS}/servico.crt", f"{CERTS}/servico.key")
# Chamada direta na rede interna, sem passar por proxy
ABRIR = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                    urllib.request.HTTPSHandler(context=CONTEXTO_ESTOQUE)).open


def registrar(metodo, caminho, status, canal, sujeito="-"):
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} ms-catalogo [{canal}] {metodo} {caminho} {status} sub={sujeito}', flush=True)


def consultar_estoque():
    token_servico = gerar_token("ms-catalogo", ["estoque:ler"], SEGREDO, validade=60)
    pedido = urllib.request.Request(f"{ESTOQUE_URL}/v1/estoque",
                                    headers={"Authorization": f"Bearer {token_servico}"})
    with ABRIR(pedido, timeout=3) as resposta:
        return {item["sku"]: item["quantidade"] for item in json.load(resposta)}


class Manipulador(BaseHTTPRequestHandler):
    server_version = "ms-catalogo"
    sys_version = ""
    canal = "https"

    def _responder(self, status, corpo, extra=None):
        dados = json.dumps(corpo, ensure_ascii=False, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        for chave, valor in (extra or {}).items():
            self.send_header(chave, valor)
        self.end_headers()
        self.wfile.write(dados)

    def do_POST(self):
        if self.path != "/v1/auth/token":
            registrar("POST", self.path, 404, self.canal)
            return self._responder(404, {"erro": "não encontrado"})
        cabecalho = self.headers.get("Authorization", "")
        try:
            usuario, senha = base64.b64decode(cabecalho[6:]).decode().split(":", 1)
        except (ValueError, binascii.Error, UnicodeDecodeError):
            usuario, senha = "", ""
        valido = (cabecalho.startswith("Basic ")
                  and hmac.compare_digest(usuario.encode(), USUARIO.encode())
                  and hmac.compare_digest(senha.encode(), SENHA.encode()))
        if not valido:
            registrar("POST", self.path, 401, self.canal)
            return self._responder(401, {"erro": "credenciais inválidas"},
                                   {"WWW-Authenticate": 'Basic realm="vinheria"'})
        token = gerar_token(usuario, ["catalogo:ler"], SEGREDO, validade=900)
        registrar("POST", self.path, 200, self.canal, usuario)
        return self._responder(200, {"access_token": token, "token_type": "Bearer", "expires_in": 900})

    def do_GET(self):
        if self.path == "/health":
            registrar("GET", self.path, 200, self.canal)
            return self._responder(200, {"status": "ok", "servico": "ms-catalogo"})
        if self.path != "/v1/vinhos":
            registrar("GET", self.path, 404, self.canal)
            return self._responder(404, {"erro": "não encontrado"})
        cabecalho = self.headers.get("Authorization", "")
        try:
            if not cabecalho.startswith("Bearer "):
                raise TokenInvalido("token ausente")
            corpo = validar_token(cabecalho[7:], SEGREDO, "catalogo:ler")
        except TokenInvalido as erro:
            status = 403 if str(erro) == "escopo insuficiente" else 401
            registrar("GET", self.path, status, self.canal)
            return self._responder(status, {"erro": str(erro)},
                                   {"WWW-Authenticate": 'Bearer error="invalid_token"'})
        try:
            saldo = consultar_estoque()
        except (urllib.error.URLError, OSError, ValueError) as erro:
            registrar("GET", self.path, 503, self.canal, corpo["sub"])
            return self._responder(503, {"erro": "ms-estoque indisponível", "detalhe": str(erro)})
        vinhos = [dict(v, quantidade=saldo.get(v["sku"], 0)) for v in CATALOGO]
        registrar("GET", self.path, 200, self.canal, corpo["sub"])
        return self._responder(200, vinhos)

    def log_message(self, *args):
        pass


class ManipuladorHttp(Manipulador):
    canal = "http"


if __name__ == "__main__":
    https = ThreadingHTTPServer(("0.0.0.0", PORTA_HTTPS), Manipulador)
    https.socket = contexto_tls_servidor(f"{CERTS}/servico.crt", f"{CERTS}/servico.key").wrap_socket(
        https.socket, server_side=True)
    print(f"ms-catalogo ouvindo em HTTPS :{PORTA_HTTPS}", flush=True)
    if PERMITIR_HTTP:
        http = ThreadingHTTPServer(("0.0.0.0", PORTA_HTTP), ManipuladorHttp)
        threading.Thread(target=http.serve_forever, daemon=True).start()
        print(f"ATENÇÃO: HTTP sem criptografia ligado na porta {PORTA_HTTP} (somente para demonstração)", flush=True)
    https.serve_forever()
