"""Informações do destino de uma solicitação HTTP, sem exibir credenciais."""

import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit


def mostrar_solicitacao(requisicao):
    """Exibe o destino preparado; os IPs de DNS não comprovam o peer real."""
    partes = urlsplit(requisicao.url)
    host = partes.hostname
    porta = partes.port
    if porta is None:
        porta = {"http": 80, "https": 443}.get(partes.scheme)

    # O destino continua completo, mas usuário e senha da URL não são exibidos.
    destino = partes.netloc.rsplit("@", 1)[-1]
    url = urlunsplit((partes.scheme, destino, partes.path, partes.query, partes.fragment))
    rota = partes.path or "/"
    if partes.query:
        rota += f"?{partes.query}"

    ips = "indisponível"
    if host:
        try:
            ips = str(ipaddress.ip_address(host))
        except ValueError:
            try:
                enderecos = socket.getaddrinfo(host, porta, type=socket.SOCK_STREAM)
                ips = ", ".join(dict.fromkeys(endereco[4][0] for endereco in enderecos)) or ips
            except (OSError, UnicodeError):
                pass

    print(f"Método HTTP: {requisicao.method}")
    print(f"URL: {url}")
    print(f"Endereço/host: {host or 'indisponível'}")
    print(f"IP(s) resolvido(s): {ips}")
    print(f"Porta: {porta if porta is not None else 'indisponível'}")
    print(f"Rota: {rota}")
    host_header = requisicao.headers.get("Host")
    if host_header is not None:
        print(f"Header Host: {host_header}")
