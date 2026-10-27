"""Exercita auth, flags, targeting, evaluation e confirma o evento no DynamoDB."""
import argparse
import json
import sys
import time
from uuid import uuid4

import requests

from comum import API_KEY, Api, Aws, executar_cli, positivo, salvar_resultado


def testar(args):
    if not API_KEY:
        raise ValueError("Preencha API_KEY no .env ou execute python criar_chave.py.")
    aws = None if args.sem_dynamodb else Aws()
    flag = "teste-api-aws-" + uuid4().hex[:12]
    print(f"Flag exclusiva deste teste: {flag}", flush=True)
    api = Api()
    criou_flag = criou_regra = False
    sucesso = False
    try:
        api.chamar("GET", "/validate")
        api.chamar("POST", "/flags", esperado=201, json={"name": flag, "description": "Criada pelo teste AWS", "is_enabled": True})
        criou_flag = True
        flag_lida = api.chamar("GET", f"/flags/{flag}")
        if flag_lida.get("is_enabled") is not True:
            raise RuntimeError("A leitura da flag nao confirmou a gravacao.")
        api.chamar("POST", "/rules", esperado=201, json={"flag_name": flag, "is_enabled": True, "rules": {"type": "PERCENTAGE", "value": 100}})
        criou_regra = True
        regra = api.chamar("GET", f"/rules/{flag}")
        if regra.get("rules", {}).get("value") != 100:
            raise RuntimeError("A leitura da regra nao confirmou a gravacao.")
        api.chamar("PUT", f"/flags/{flag}", json={"description": "Descricao atualizada no teste AWS"})
        if api.chamar("GET", f"/flags/{flag}").get("description") != "Descricao atualizada no teste AWS":
            raise RuntimeError("A leitura nao confirmou a atualizacao da flag.")
        print("Flags e regras foram criadas e lidas pelas APIs que usam o RDS.")
        resposta = api.chamar("GET", "/evaluate", params={"user_id": "usuario-" + flag, "flag_name": flag})
        print(json.dumps(resposta, ensure_ascii=False))
        if resposta.get("result") is not True:
            raise RuntimeError("A flag ativa com regra de 100% deveria retornar true.")
        if aws:
            prazo = time.monotonic() + args.espera
            while True:
                dados = aws.eventos(flag, paginas=args.paginas, limite=5)
                if dados["encontrados"]:
                    print(f"Evento confirmado no DynamoDB: {dados['itens'][0]['event_id']}")
                    break
                if time.monotonic() >= prazo:
                    detalhe = " O Scan foi parcial; aumente --paginas." if dados["parcial"] else ""
                    raise RuntimeError("Evento nao localizado dentro do prazo." + detalhe + " Consulte a fila e os logs do analytics.")
                print("Aguardando consumo SQS e gravacao no DynamoDB...", flush=True)
                time.sleep(min(5, max(0, prazo - time.monotonic())))
        sucesso = True
    finally:
        # Remove somente os nomes exclusivos criados nesta execucao.
        try:
            if not args.manter:
                for criado, rota in ((criou_regra, f"/rules/{flag}"), (criou_flag, f"/flags/{flag}")):
                    if criado:
                        try:
                            api.chamar("DELETE", rota, esperado=204)
                        except (requests.RequestException, RuntimeError, OSError) as erro:
                            print(f"Limpeza pendente de {rota}: {erro}", file=sys.stderr)
                            sucesso = False
        finally:
            api.close()
            destino = salvar_resultado("ultimo_teste_api.json", {"flag": flag, "sucesso": sucesso, "mantido": args.manter})
            print(f"Resultado: {destino}")
    if not sucesso:
        raise RuntimeError("O teste terminou com falhas; confira as mensagens anteriores.")
    print("Fluxo validado. Os eventos historicos no DynamoDB foram preservados.")
    if args.manter:
        print(f"Para carga: python gerar_carga.py --flag {flag} --duracao 60 --usuarios 10")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manter", action="store_true", help="Mantem flag/regra para gerar carga depois.")
    parser.add_argument("--sem-dynamodb", action="store_true", help="Executa somente as APIs HTTP.")
    parser.add_argument("--espera", type=positivo, default=120, help="Prazo em segundos para localizar o evento.")
    parser.add_argument("--paginas", type=positivo, default=50, help="Maximo de paginas por Scan.")
    args = parser.parse_args()
    return executar_cli(lambda: testar(args))


if __name__ == "__main__":
    sys.exit(main())
