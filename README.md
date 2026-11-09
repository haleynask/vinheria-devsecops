# Vinheria Agnello — DevSecOps (Fase 7)

Simulação de parte da arquitetura da Vinheria Agnello com dois microsserviços
(**ms-catalogo** e **ms-estoque**), DNS e DHCP próprios, pipeline Jenkins e comunicação segura.

| Componente | Endereço | Função |
|---|---|---|
| dns-dhcp | 172.28.0.2 | DNS da zona `vinheria.internal` e DHCP das estações (.100–.150) |
| ms-catalogo | 172.28.0.11 · `catalogo.vinheria.internal` | Vitrine; emite JWT; porta 8443 (HTTPS) |
| ms-estoque | 172.28.0.12 · `estoque.vinheria.internal` | Saldo por SKU; só HTTPS com mTLS; sem porta externa |
| publicacao | 172.28.0.20 · `publicacao.vinheria.internal` | Servidor de produção simulado (nginx), porta 8088 |
| estacao-loja | IP por DHCP | Estação de trabalho da loja |
| jenkins | localhost:8080 | Pipeline de build, testes, verificação de segredos e deploy |

## Subir o ambiente

```sh
cp .env.exemplo .env          # e troque JWT_SEGREDO e DEMO_SENHA
docker compose up -d --build
sh scripts/testar.sh
```

## Jenkins

```sh
docker compose -f docker-compose.jenkins.yml up -d --build
```

Acesse http://localhost:8080, conclua a configuração inicial e crie um item **Pipeline**
com *Pipeline script from SCM* apontando para este repositório (arquivo `Jenkinsfile`).

## Demonstração sem criptografia (Wireshark)

```sh
PERMITIR_HTTP=sim docker compose up -d     # liga o HTTP na porta 8001 só para a demonstração
docker compose up -d                       # volta ao padrão: apenas HTTPS
```
