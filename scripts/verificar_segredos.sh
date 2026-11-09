#!/bin/sh
# Etapa de segurança do pipeline: falha se houver segredo versionado no repositório.
set -e
sensiveis=$(git ls-files | grep -E '\.(key|pem|p12|pfx)$|(^|/)\.env$' || true)
if [ -n "$sensiveis" ]; then
  echo "ERRO: arquivos sensíveis versionados:"
  echo "$sensiveis"
  exit 1
fi
if git grep -nIE -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' -- . ':(exclude)scripts/verificar_segredos.sh'; then
  echo "ERRO: chave privada encontrada no código"
  exit 1
fi
echo "OK: nenhum segredo encontrado no repositório"
