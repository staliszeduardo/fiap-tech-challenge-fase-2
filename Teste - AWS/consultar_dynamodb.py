"""Consulta eventos gravados pelo analytics, sem consumir mensagens nem alterar dados."""
import argparse
import json
import sys

from comum import Aws, TABLE_NAME, executar_cli, positivo, salvar_resultado


def executar(args):
    dados = Aws().eventos(args.flag, paginas=args.paginas, limite=args.limite)
    print(f"DynamoDB: {TABLE_NAME} | filtro: {args.flag or 'todos'}")
    print(f"Encontrados: {dados['encontrados']} | avaliados no Scan: {dados['avaliados']} | paginas: {dados['paginas']}")
    print("Consulta PARCIAL; aumente --paginas para continuar a busca." if dados["parcial"] else "Scan percorreu a tabela nesta consulta.")
    print(f"Amostra: ate {args.limite} eventos mais recentes dentre os registros percorridos.")
    for item in dados["itens"]:
        print(json.dumps(item, ensure_ascii=False, default=str))
    print(f"Resultado salvo: {salvar_resultado('consulta_dynamodb.json', dados)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flag", help="Filtra flag_name, inclusive dos lotes enviados diretamente a SQS.")
    parser.add_argument("--limite", type=positivo, default=20, help="Quantidade de registros exibidos.")
    parser.add_argument("--paginas", type=positivo, default=50, help="Maximo de paginas de 200 itens avaliados.")
    args = parser.parse_args()
    return executar_cli(lambda: executar(args))


if __name__ == "__main__":
    sys.exit(main())
