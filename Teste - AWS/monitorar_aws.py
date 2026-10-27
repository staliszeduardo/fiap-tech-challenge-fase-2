"""Mostra fila, DynamoDB e opcionalmente replicas; exporta CSV para demonstracao."""
import argparse
import csv
import sys
import time
from datetime import datetime

from comum import Aws, PASTA, TABLE_NAME, executar_cli, positivo


def executar(args):
    aws = Aws()
    if args.cluster:
        from cluster import replicas
    pasta = PASTA / "resultados"
    pasta.mkdir(exist_ok=True)
    caminho = pasta / ("monitor-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".csv")
    print(f"Conta: {aws.identity['Account']} | DynamoDB: {TABLE_NAME} | filtro: {args.flag or 'todos'}")
    print("SQS informa contagens aproximadas. DynamoDB e consultado a cada 10s; '-' significa que a consulta ainda nao ocorreu.")
    print(f"CSV: {caminho}\nCtrl+C encerra.\n", flush=True)
    print("HORA      DISPONIVEIS  EM_PROCESSO  ATRASADAS  DYNAMO_ENCONTRADOS  SCAN_PARCIAL  ANALYTICS", flush=True)
    inicio = time.monotonic()
    proximo_scan = 0
    encontrados = parcial = "-"
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["hora", "disponiveis_aprox", "em_processamento_aprox", "atrasadas_aprox", "dynamo_encontrados", "scan_parcial", "analytics_prontos_desejados"])
        while True:
            fila = aws.fila()
            if time.monotonic() >= proximo_scan:
                dados = aws.eventos(args.flag, paginas=args.paginas, limite=1)
                encontrados, parcial = dados["encontrados"], "sim" if dados["parcial"] else "nao"
                proximo_scan = time.monotonic() + 10
            pods = replicas() if args.cluster else "-"
            horario = datetime.now().astimezone().isoformat(timespec="seconds")
            escritor.writerow([horario, fila["disponiveis"], fila["em_processamento"], fila["atrasadas"], encontrados, parcial, pods])
            arquivo.flush()
            print(f"{horario[11:19]}  {fila['disponiveis']:11}  {fila['em_processamento']:11}  {fila['atrasadas']:9}  {str(encontrados):18}  {str(parcial):12}  {pods}", flush=True)
            if args.duracao and time.monotonic() - inicio >= args.duracao:
                break
            restante = args.duracao - (time.monotonic() - inicio) if args.duracao else args.intervalo
            time.sleep(max(0, min(args.intervalo, restante)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flag", help="Filtra somente eventos do teste no DynamoDB. A fila continua mostrando o total.")
    parser.add_argument("--intervalo", type=positivo, default=2)
    parser.add_argument("--duracao", type=positivo, help="Duracao em segundos; omitida monitora ate Ctrl+C.")
    parser.add_argument("--paginas", type=positivo, default=20)
    parser.add_argument("--cluster", action="store_true", help="Inclui replicas do analytics via kubectl instalado nesta maquina.")
    args = parser.parse_args()
    return executar_cli(lambda: executar(args))


if __name__ == "__main__":
    sys.exit(main())
