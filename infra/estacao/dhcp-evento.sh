#!/bin/sh
# Chamado pelo udhcpc a cada evento DHCP. Mostra os parâmetros entregues pelo servidor.
case "$1" in
  bound|renew)
    echo "DHCP: concessão recebida do servidor $serverid"
    echo "  endereço  : $ip/$mask"
    echo "  gateway   : $router"
    echo "  DNS       : $dns"
    echo "  domínio   : $domain"
    echo "  validade  : ${lease}s"
    ;;
  leasefail)
    echo "DHCP: nenhum servidor respondeu"
    ;;
esac
