#!/bin/sh
# Monta a pasta dist/ com os serviços e uma página que identifica a versão publicada.
set -e
VERSAO=${1:-local}
COMMIT=${2:-$(git rev-parse HEAD)}
DATA=$(date '+%d/%m/%Y %H:%M:%S')
rm -rf dist && mkdir -p dist/servicos
cp -R services/comum services/ms-catalogo services/ms-estoque dist/servicos/
printf '{"versao": "%s", "commit": "%s", "data": "%s"}\n' "$VERSAO" "$COMMIT" "$DATA" > dist/versao.json
cat > dist/index.html << HTML
<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Vinheria Agnello — Publicação</title>
<style>body{font-family:Arial,sans-serif;margin:40px;color:#222}h1{color:#7B1E2B}
td{padding:6px 14px;border-bottom:1px solid #ddd}</style></head>
<body><h1>Vinheria Agnello — ambiente de produção (simulado)</h1>
<table><tr><td>Versão publicada</td><td><b>build #$VERSAO</b></td></tr>
<tr><td>Commit</td><td>$COMMIT</td></tr><tr><td>Data do deploy</td><td>$DATA</td></tr>
<tr><td>Serviços</td><td>ms-catalogo, ms-estoque</td></tr></table></body></html>
HTML
echo "Pacote da versão $VERSAO criado em dist/"
