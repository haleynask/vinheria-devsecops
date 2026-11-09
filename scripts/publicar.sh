#!/bin/sh
# Deploy: guarda a versão em releases/<build> e atualiza a pasta "atual", servida pelo nginx.
set -e
VERSAO=$1
DESTINO=${2:-/publicacao/vinheria}
mkdir -p "$DESTINO/releases/$VERSAO" "$DESTINO/atual"
cp -R dist/. "$DESTINO/releases/$VERSAO/"
# Troca o conteúdo (não a pasta) para o nginx enxergar a nova versão sem reiniciar
find "$DESTINO/atual" -mindepth 1 -delete
cp -R dist/. "$DESTINO/atual/"
# Mantém apenas as 5 versões mais recentes para permitir rollback
ls -1 "$DESTINO/releases" | grep -E '^[0-9]+$' | sort -n | head -n -5 | while read antiga; do
  rm -rf "$DESTINO/releases/$antiga"
done
echo "Versão $VERSAO publicada em $DESTINO/atual"
ls -1 "$DESTINO/releases" | grep -E '^[0-9]+$' | sort -n | sed 's/^/  release disponível: /'
