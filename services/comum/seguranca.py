"""Funções de segurança usadas pelos dois microsserviços.

- Tokens JWT assinados com HMAC-SHA256 (HS256): emissão e validação.
- Contextos TLS para servidor e cliente (TLS 1.2 ou superior).
"""
import base64
import binascii
import hashlib
import hmac
import json
import ssl
import time

EMISSOR = "vinheria-agnello"


class TokenInvalido(Exception):
    """Token ausente, malformado, adulterado, expirado ou sem a permissão exigida."""


def _b64url(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def _b64url_decodificar(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _assinar(mensagem: str, segredo: str) -> bytes:
    return hmac.new(segredo.encode(), mensagem.encode(), hashlib.sha256).digest()


def gerar_token(sujeito: str, escopos: list, segredo: str, validade: int = 900) -> str:
    """Gera um JWT com sujeito, escopos e prazo de validade (em segundos)."""
    agora = int(time.time())
    cabecalho = {"alg": "HS256", "typ": "JWT"}
    corpo = {"iss": EMISSOR, "sub": sujeito, "scope": " ".join(escopos),
             "iat": agora, "exp": agora + validade}
    partes = [_b64url(json.dumps(cabecalho, separators=(",", ":")).encode()),
              _b64url(json.dumps(corpo, separators=(",", ":")).encode())]
    assinatura = _assinar(".".join(partes), segredo)
    return ".".join(partes + [_b64url(assinatura)])


def validar_token(token: str, segredo: str, escopo_exigido: str = None) -> dict:
    """Confere formato, algoritmo, assinatura, emissor, validade e escopo. Devolve o corpo do token."""
    try:
        cab_b64, corpo_b64, ass_b64 = token.split(".")
        cabecalho = json.loads(_b64url_decodificar(cab_b64))
        corpo = json.loads(_b64url_decodificar(corpo_b64))
        assinatura = _b64url_decodificar(ass_b64)
    except (ValueError, binascii.Error):
        raise TokenInvalido("token malformado")

    # Só HS256 é aceito: impede o ataque de trocar o algoritmo para "none"
    if cabecalho.get("alg") != "HS256":
        raise TokenInvalido("algoritmo não permitido")
    # compare_digest evita ataques de tempo na comparação da assinatura
    if not hmac.compare_digest(_assinar(f"{cab_b64}.{corpo_b64}", segredo), assinatura):
        raise TokenInvalido("assinatura inválida")
    if corpo.get("iss") != EMISSOR:
        raise TokenInvalido("emissor inválido")
    if corpo.get("exp", 0) < time.time():
        raise TokenInvalido("token expirado")
    if escopo_exigido and escopo_exigido not in corpo.get("scope", "").split():
        raise TokenInvalido("escopo insuficiente")
    return corpo


def contexto_tls_servidor(certificado: str, chave: str, ca_clientes: str = None) -> ssl.SSLContext:
    """TLS do lado servidor. Com ca_clientes, exige certificado do cliente (mTLS)."""
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    contexto.load_cert_chain(certificado, chave)
    if ca_clientes:
        contexto.load_verify_locations(ca_clientes)
        contexto.verify_mode = ssl.CERT_REQUIRED
    return contexto


def contexto_tls_cliente(ca: str, certificado: str = None, chave: str = None) -> ssl.SSLContext:
    """TLS do lado cliente: valida o servidor pela CA interna e, opcionalmente, apresenta certificado próprio."""
    contexto = ssl.create_default_context(cafile=ca)
    contexto.minimum_version = ssl.TLSVersion.TLSv1_2
    if certificado and chave:
        contexto.load_cert_chain(certificado, chave)
    return contexto


def ler_segredo(valor: str) -> str:
    """Recusa segredos fracos ou o valor de exemplo."""
    if not valor or len(valor) < 32 or valor.startswith("troque"):
        raise SystemExit("JWT_SEGREDO ausente ou fraco: defina no .env um valor aleatório com 32+ caracteres")
    return valor
