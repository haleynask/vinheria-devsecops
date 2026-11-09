"""Testes unitários do módulo de segurança (executados no pipeline do Jenkins)."""
import base64
import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services", "comum"))
from seguranca import TokenInvalido, gerar_token, ler_segredo, validar_token  # noqa: E402

SEGREDO = "segredo-de-teste-com-mais-de-32-caracteres"


def _b64(dados):
    return base64.urlsafe_b64encode(json.dumps(dados).encode()).rstrip(b"=").decode()


class TestesJWT(unittest.TestCase):

    def test_token_valido_e_aceito(self):
        token = gerar_token("sommelier", ["catalogo:ler"], SEGREDO)
        corpo = validar_token(token, SEGREDO, "catalogo:ler")
        self.assertEqual(corpo["sub"], "sommelier")

    def test_corpo_adulterado_e_recusado(self):
        cab, _, ass = gerar_token("sommelier", ["catalogo:ler"], SEGREDO).split(".")
        falso = _b64({"iss": "vinheria-agnello", "sub": "admin", "scope": "catalogo:ler", "exp": 9999999999})
        with self.assertRaises(TokenInvalido):
            validar_token(f"{cab}.{falso}.{ass}", SEGREDO)

    def test_segredo_diferente_e_recusado(self):
        token = gerar_token("sommelier", ["catalogo:ler"], SEGREDO)
        with self.assertRaises(TokenInvalido):
            validar_token(token, "outro-segredo-com-mais-de-32-caracteres!")

    def test_token_expirado_e_recusado(self):
        token = gerar_token("sommelier", ["catalogo:ler"], SEGREDO, validade=-1)
        with self.assertRaises(TokenInvalido):
            validar_token(token, SEGREDO)

    def test_escopo_insuficiente_e_recusado(self):
        token = gerar_token("sommelier", ["catalogo:ler"], SEGREDO)
        with self.assertRaises(TokenInvalido):
            validar_token(token, SEGREDO, "estoque:ler")

    def test_algoritmo_none_e_recusado(self):
        corpo = _b64({"iss": "vinheria-agnello", "sub": "x", "scope": "catalogo:ler", "exp": int(time.time()) + 60})
        with self.assertRaises(TokenInvalido):
            validar_token(f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{corpo}.", SEGREDO)

    def test_token_malformado_e_recusado(self):
        with self.assertRaises(TokenInvalido):
            validar_token("isto-nao-e-um-jwt", SEGREDO)

    def test_segredo_fraco_e_recusado(self):
        with self.assertRaises(SystemExit):
            ler_segredo("curto")


if __name__ == "__main__":
    unittest.main()
