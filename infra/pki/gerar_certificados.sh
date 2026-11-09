#!/bin/sh
# Cria a CA interna da Vinheria Agnello e os certificados dos microsserviços.
# Executado uma única vez pelo serviço "pki" do docker-compose; as chaves não vão para o Git.
set -e
SAIDA=${1:-/certs}
if [ -f "$SAIDA/ca/ca.crt" ]; then
  echo "Certificados já existem em $SAIDA — nada a fazer."
  exit 0
fi
mkdir -p "$SAIDA/ca" "$SAIDA/catalogo" "$SAIDA/estoque" "$SAIDA/publico"

openssl req -x509 -newkey rsa:2048 -nodes -days 365 -sha256 \
  -keyout "$SAIDA/ca/ca.key" -out "$SAIDA/ca/ca.crt" \
  -subj "/C=BR/O=Vinheria Agnello/CN=Vinheria Agnello CA Interna" 2>/dev/null

emitir() {  # emitir <serviço> <subjectAltName> <extendedKeyUsage>
  dir="$SAIDA/$1"
  openssl req -newkey rsa:2048 -nodes -keyout "$dir/servico.key" -out "$dir/servico.csr" \
    -subj "/C=BR/O=Vinheria Agnello/CN=$1.vinheria.internal" 2>/dev/null
  printf "subjectAltName=%s\nextendedKeyUsage=%s\nkeyUsage=digitalSignature,keyEncipherment\nbasicConstraints=CA:FALSE\n" \
    "$2" "$3" > "$dir/ext.cnf"
  openssl x509 -req -in "$dir/servico.csr" -CA "$SAIDA/ca/ca.crt" -CAkey "$SAIDA/ca/ca.key" \
    -CAcreateserial -days 180 -sha256 -extfile "$dir/ext.cnf" -out "$dir/servico.crt" 2>/dev/null
  cp "$SAIDA/ca/ca.crt" "$dir/ca.crt"
  rm -f "$dir/servico.csr" "$dir/ext.cnf"
  # Laboratório: leitura liberada para o usuário sem privilégios do contêiner.
  # Em produção a chave ficaria em um cofre de segredos.
  chmod 644 "$dir/servico.key"
  echo "Certificado emitido: $1.vinheria.internal ($3)"
}

# O ms-catalogo atua como servidor (clientes da loja) e como cliente (chamadas ao ms-estoque)
emitir catalogo "DNS:catalogo.vinheria.internal,DNS:localhost,IP:127.0.0.1" "serverAuth,clientAuth"
emitir estoque  "DNS:estoque.vinheria.internal" "serverAuth"
cp "$SAIDA/ca/ca.crt" "$SAIDA/publico/ca.crt"
echo "CA interna criada em $SAIDA/ca (a chave da CA não é montada em nenhum serviço)."
