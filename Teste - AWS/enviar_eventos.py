"""Envia eventos validos diretamente a SQS, em lotes de no maximo 10."""
import argparse
import json
import sys
import time
from uuid import uuid4

from comum import Aws, QUEUE_URL, agora, executar_cli, positivo, salvar_resultado


class EnvioParcialError(RuntimeError):
    def __init__(self, mensagem, aceitas):
        super().__init__(mensagem)
        self.aceitas = aceitas


def enviar_lote(sqs, entradas, esperar=time.sleep):
    pendentes = entradas
    enviados = 0
    for tentativa in range(3):
        resposta = sqs.send_message_batch(QueueUrl=QUEUE_URL, Entries=pendentes)
        sucesso = {item["Id"] for item in resposta.get("Successful", [])}
        falhas = {item["Id"]: item for item in resposta.get("Failed", [])}
        esperados = {item["Id"] for item in pendentes}
        if sucesso & falhas.keys() or sucesso | falhas.keys() != esperados:
            raise RuntimeError("SQS retornou um resultado de lote incompleto ou inconsistente.")
        enviados += len(sucesso)
        if not falhas:
            return enviados
        if any(item.get("SenderFault") for item in falhas.values()):
            codigos = sorted({item.get("Code", "desconhecido") for item in falhas.values()})
            raise EnvioParcialError(f"SQS rejeitou mensagens: {codigos}. Ja aceitas neste lote: {enviados}.", enviados)
        pendentes = [item for item in pendentes if item["Id"] in falhas]
        if tentativa < 2:
            esperar(2 ** tentativa)
    raise EnvioParcialError(f"Falha ao enviar {len(pendentes)} mensagens apos 3 tentativas; aceitas neste lote: {enviados}.", enviados)


def executar(args):
    aws = Aws()
    flag = args.flag or ("teste-sqs-aws-" + uuid4().hex[:12])
    print(f"Fila: {QUEUE_URL}\nFlag dos eventos: {flag}\nQuantidade: {args.quantidade}", flush=True)
    print("Envio direto a SQS: exercita analytics e KEDA. Para testar evaluation, use gerar_carga.py.")
    inicio = time.monotonic()
    enviados = 0
    resumo = {"flag": flag, "solicitados": args.quantidade, "enviados": 0, "inicio": agora()}
    try:
        for inicio_lote in range(0, args.quantidade, 10):
            entradas = []
            for numero in range(inicio_lote, min(inicio_lote + 10, args.quantidade)):
                evento = {"user_id": f"{flag}-{numero}", "flag_name": flag, "result": True, "timestamp": agora()}
                entradas.append({"Id": f"m{numero}", "MessageBody": json.dumps(evento)})
            try:
                enviados += enviar_lote(aws.sqs, entradas)
            except EnvioParcialError as erro:
                enviados += erro.aceitas
                raise
            print(f"Aceitas pela SQS: {enviados}/{args.quantidade}", flush=True)
            if args.taxa > 0:
                time.sleep(max(0, enviados / args.taxa - (time.monotonic() - inicio)))
    finally:
        resumo.update(enviados=enviados, segundos=round(time.monotonic() - inicio, 2))
        destino = salvar_resultado("ultimo_envio_sqs.json", resumo)
        print(f"Resumo: {destino}")
    print(f"Para observar: python monitorar_aws.py --flag {flag} --cluster")
    print(f"Para consultar: python consultar_dynamodb.py --flag {flag}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quantidade", type=positivo, default=1000)
    parser.add_argument("--taxa", type=positivo, help="Limita mensagens/segundo; omitido envia o mais rapido possivel.")
    parser.add_argument("--flag", help="Identifica o lote no DynamoDB; nao precisa existir na API.")
    args = parser.parse_args()
    args.taxa = args.taxa or 0
    return executar_cli(lambda: executar(args))


if __name__ == "__main__":
    sys.exit(main())
