"""Gera avaliacoes HTTP concorrentes e salva quantidade, erros e latencias."""
import argparse
import json
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import requests

from comum import Api, NOME_FLAG, executar_cli, positivo, salvar_resultado


def executar(args):
    # Valida a configuracao antes de iniciar threads.
    Api().close()
    parar = threading.Event()
    inicio = time.monotonic()
    prazo = inicio + args.duracao
    totais = Counter()
    latencias = []
    trava = threading.Lock()

    def trabalhador(numero):
        api = Api(chave="")
        locais = Counter()
        tempos = []
        chamada = 0
        try:
            while not parar.is_set() and time.monotonic() < prazo:
                chamada += 1
                antes = time.monotonic()
                try:
                    resposta = api.chamar("GET", "/evaluate", mostrar=False, params={
                        "flag_name": args.flag, "user_id": f"carga-{numero}-{chamada}"
                    })
                    if not isinstance(resposta.get("result"), bool):
                        raise RuntimeError("Resposta sem result booleano.")
                    locais["http_200_validos"] += 1
                    locais["true" if resposta["result"] else "false"] += 1
                except (requests.RequestException, RuntimeError, ValueError):
                    locais["erros"] += 1
                tempos.append((time.monotonic() - antes) * 1000)
        finally:
            api.close()
            with trava:
                totais.update(locais)
                latencias.extend(tempos)

    print(f"Carga: {args.usuarios} usuarios simultaneos, {args.duracao}s, flag={args.flag}", flush=True)
    print("Estas chamadas passam por evaluation, Redis e SQS; /health nao gera eventos.", flush=True)
    interrompido = False
    pool = ThreadPoolExecutor(max_workers=args.usuarios)
    tarefas = [pool.submit(trabalhador, numero) for numero in range(args.usuarios)]
    try:
        for tarefa in tarefas:
            tarefa.result()
    except KeyboardInterrupt:
        interrompido = True
        parar.set()
    finally:
        parar.set()
        pool.shutdown(wait=True)
    segundos = time.monotonic() - inicio
    ordenados = sorted(latencias)
    resumo = {"flag": args.flag, "segundos": round(segundos, 2), "usuarios": args.usuarios, **totais,
              "requisicoes": len(ordenados), "requisicoes_por_segundo": round(len(ordenados) / max(segundos, .001), 2),
              "p50_ms": round(ordenados[int((len(ordenados)-1)*.50)], 2) if ordenados else None,
              "p95_ms": round(ordenados[int((len(ordenados)-1)*.95)], 2) if ordenados else None}
    print(json.dumps(resumo, indent=2))
    print(f"Resumo: {salvar_resultado('ultima_carga_http.json', resumo)}")
    print("HTTP 200 confirma a avaliacao; confirme a entrega assincrona separadamente no DynamoDB.")
    if interrompido:
        return 130
    if totais["erros"] or not ordenados:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flag", default=NOME_FLAG)
    parser.add_argument("--duracao", type=positivo, default=30)
    parser.add_argument("--usuarios", type=positivo, default=10)
    args = parser.parse_args()
    if args.usuarios > 100:
        parser.error("Use no maximo 100 usuarios simultaneos neste script de demonstracao.")
    return executar_cli(lambda: executar(args))


if __name__ == "__main__":
    sys.exit(main())
