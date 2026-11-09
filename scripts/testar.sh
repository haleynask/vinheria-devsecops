#!/bin/sh
# Testes da infraestrutura e da segurança. Rodar na pasta do repositório, com o ambiente no ar.
. ./.env
CA=certs/publico/ca.crt
URL=https://localhost:8443
linha() { printf '\n==== %s ====\n' "$1"; }

linha "1. DNS: nomes dos serviços resolvidos pelo servidor 172.28.0.2"
docker compose exec -T estacao-loja nslookup catalogo.vinheria.internal 172.28.0.2
docker compose exec -T estacao-loja nslookup estoque.vinheria.internal 172.28.0.2

linha "2. DHCP: concessão recebida pela estação da loja"
docker compose logs --no-log-prefix estacao-loja | grep -A6 'DHCP:'
docker compose logs --no-log-prefix dns-dhcp | grep -E 'DHCP(DISCOVER|OFFER|REQUEST|ACK)' | tail -4

linha "3. Sem token: acesso negado"
curl -s --cacert $CA -w '\nHTTP %{http_code}\n' $URL/v1/vinhos

linha "4. Senha errada: token negado"
curl -s --cacert $CA -u "$DEMO_USUARIO:senha-errada" -X POST -w '\nHTTP %{http_code}\n' $URL/v1/auth/token

linha "5. Login correto: JWT emitido"
RESPOSTA=$(curl -s --cacert $CA -u "$DEMO_USUARIO:$DEMO_SENHA" -X POST $URL/v1/auth/token)
TOKEN=$(printf '%s' "$RESPOSTA" | tr -d '\n ' | sed -E 's/.*"access_token":"([^"]+)".*/\1/')
echo "token (início): $(printf '%s' "$TOKEN" | cut -c1-40)..."

linha "6. Com token: catálogo + estoque (ms-catalogo -> ms-estoque por mTLS)"
curl -s --cacert $CA -H "Authorization: Bearer $TOKEN" -w '\nHTTP %{http_code}\n' $URL/v1/vinhos

linha "7. Token adulterado: assinatura não confere"
ADULTERADO="$(printf '%s' "$TOKEN" | cut -d. -f1).$(printf '{"iss":"vinheria-agnello","sub":"invasor","scope":"catalogo:ler","exp":9999999999}' | base64 | tr '+/' '-_' | tr -d '=\n').$(printf '%s' "$TOKEN" | cut -d. -f3)"
curl -s --cacert $CA -H "Authorization: Bearer $ADULTERADO" -w '\nHTTP %{http_code}\n' $URL/v1/vinhos

linha "8. ms-estoque recusa conexão sem certificado de cliente (mTLS)"
docker compose exec -T estacao-loja curl -s --cacert /certs/ca.crt -o /dev/null -w 'HTTP %{http_code}\n' \
  https://estoque.vinheria.internal:8443/health || echo "conexão recusada pelo ms-estoque (esperado)"

linha "9. ms-estoque não é acessível de fora da rede interna"
docker compose port ms-estoque 8443 2>/dev/null || echo "nenhuma porta do ms-estoque publicada no computador (esperado)"

linha "10. Registro dos serviços (o token nunca aparece no log)"
docker compose logs --no-log-prefix --tail 6 ms-catalogo ms-estoque
