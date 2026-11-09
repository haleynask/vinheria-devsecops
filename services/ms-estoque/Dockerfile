FROM python:3.12-alpine
WORKDIR /app
COPY services/comum/seguranca.py services/ms-estoque/app.py ./
# O serviço roda com um usuário sem privilégios de administrador
RUN adduser -D -H -u 10001 servico \
 && chmod 644 /app/*.py \
 && chown -R servico:servico /app
USER 10001
CMD ["python", "-u", "app.py"]
