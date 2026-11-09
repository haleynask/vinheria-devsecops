"""ms-estoque — saldo de garrafas por SKU da Vinheria Agnello.

Atende apenas HTTPS com mTLS: só aceita conexões de clientes com certificado
emitido pela CA interna. Além disso, cada requisição precisa de um JWT com o
escopo "estoque:ler".
"""
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comum"))
from seguranca import TokenInvalido, contexto_tls_servidor, ler_segredo, validar_token  # noqa: E402

SEGREDO = ler_segredo(os.environ.get("JWT_SEGREDO"))
PORTA = int(os.environ.get("PORTA_HTTPS", "8443"))
CERTS = os.environ.get("DIR_CERTS", "/certs")

ESTOQUE = {
    "VA-0001": 36,   # Catena Malbec 2021
    "VA-0002": 24,   # Cloudy Bay Sauvignon Blanc 2023
    "VA-0003": 3,    # Dom Pérignon 2013
    "VA-0004": 12,   # Quinta do Crasto Reserva 2020
    "VA-0006": 3,    # Barca Velha 2015
}


def registrar(metodo, caminho, status, sujeito="-"):
    # O token nunca é gravado no log
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S")} ms-estoque {metodo} {caminho} {status} sub={sujeito}', flush=True)


class Manipulador(BaseHTTPRequestHandler):
    server_version = "ms-estoque"
    sys_version = ""

    def _responder(self, status, corpo, extra=None):
        dados = json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        for chave, valor in (extra or {}).items():
            self.send_header(chave, valor)
        self.end_headers()
        self.wfile.write(dados)

    def _autorizar(self, escopo):
        cabecalho = self.headers.get("Authorization", "")
        if not cabecalho.startswith("Bearer "):
            raise TokenInvalido("token ausente")
        return validar_token(cabecalho[7:], SEGREDO, escopo)

    def do_GET(self):
        if self.path == "/health":
            registrar("GET", self.path, 200)
            return self._responder(200, {"status": "ok", "servico": "ms-estoque"})
        try:
            corpo = self._autorizar("estoque:ler")
        except TokenInvalido as erro:
            status = 403 if str(erro) == "escopo insuficiente" else 401
            registrar("GET", self.path, status)
            return self._responder(status, {"erro": str(erro)},
                                   {"WWW-Authenticate": 'Bearer error="invalid_token"'})
        if self.path == "/v1/estoque":
            registrar("GET", self.path, 200, corpo["sub"])
            return self._responder(200, [{"sku": s, "quantidade": q} for s, q in ESTOQUE.items()])
        achado = re.fullmatch(r"/v1/estoque/([A-Z]{2}-\d{4})", self.path)
        if achado and achado.group(1) in ESTOQUE:
            registrar("GET", self.path, 200, corpo["sub"])
            return self._responder(200, {"sku": achado.group(1), "quantidade": ESTOQUE[achado.group(1)]})
        registrar("GET", self.path, 404, corpo["sub"])
        return self._responder(404, {"erro": "não encontrado"})

    def log_message(self, *args):
        pass  # o registro é feito pela função registrar()


if __name__ == "__main__":
    servidor = ThreadingHTTPServer(("0.0.0.0", PORTA), Manipulador)
    contexto = contexto_tls_servidor(f"{CERTS}/servico.crt", f"{CERTS}/servico.key", ca_clientes=f"{CERTS}/ca.crt")
    servidor.socket = contexto.wrap_socket(servidor.socket, server_side=True)
    print(f"ms-estoque ouvindo em HTTPS :{PORTA} (mTLS obrigatório)", flush=True)
    servidor.serve_forever()
