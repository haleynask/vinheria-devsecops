FROM alpine:3.20
RUN apk add --no-cache curl bind-tools
COPY dhcp-evento.sh /usr/local/bin/dhcp-evento.sh
RUN chmod +x /usr/local/bin/dhcp-evento.sh
# Ao iniciar, a estação pede um endereço ao servidor DHCP e mostra o que recebeu
CMD ["sh", "-c", "udhcpc -i eth0 -n -q -t 5 -T 2 -s /usr/local/bin/dhcp-evento.sh; sleep infinity"]
