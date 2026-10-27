"""Confere credenciais locais, fila e tabela; somente leitura."""
import argparse
import json
import sys

from comum import API_HOST, API_URL, Aws, QUEUE_URL, REGION, TABLE_NAME, executar_cli


def executar():
    aws = Aws()
    tabela = aws.dynamo.describe_table(TableName=TABLE_NAME)["Table"]
    print(f"Conta AWS: {aws.identity['Account']}\nIdentidade: {aws.identity['Arn']}\nRegiao: {REGION}")
    print(f"API: {API_URL}\nHost HTTP: {API_HOST}\nFila: {QUEUE_URL}")
    print("Fila (aproximado): " + json.dumps(aws.fila()))
    print(f"DynamoDB: {TABLE_NAME} | estado: {tabela['TableStatus']} | chave: {tabela['KeySchema']}")
    print("A identidade local e usada pelos testes boto3; as roles IRSA sao usadas pelos Pods.")


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    return executar_cli(executar)


if __name__ == "__main__":
    sys.exit(main())
