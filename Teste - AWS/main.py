"""Menu local dos testes AWS; cada opcao tambem pode ser executada separadamente."""
import argparse
import subprocess
import sys

from comum import PASTA


def rodar(arquivo, *argumentos):
    try:
        resultado = subprocess.run([sys.executable, str(PASTA / arquivo), *argumentos], cwd=PASTA, check=False)
        if resultado.returncode not in (0, 130):
            print(f"O script terminou com erro (codigo {resultado.returncode}).")
    except KeyboardInterrupt:
        print("\nRetornando ao menu.")


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    while True:
        print("""
TESTES AWS - ToggleMaster
 1. Conferir conta, endpoints, fila e tabela
 2. Criar API_KEY e salvar no .env desta pasta
 3. Testar APIs e aguardar evento no DynamoDB
 4. Enviar 1.000 eventos diretamente para SQS
 5. Monitorar fila e DynamoDB (Ctrl+C volta ao menu)
 6. Consultar eventos no DynamoDB
 7. Gerar carga HTTP no evaluation (30s, 10 usuarios)
 8. Ver Pods, Deployments, HPA e KEDA
 9. Pausar analytics em zero replicas para acumular fila
10. Retomar escala automatica do analytics
11. Consultar RDS por SQL (opcional, exige tunel)
 0. Sair
""")
        try:
            escolha = input("Opcao: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if escolha == "0":
            return 0
        if escolha == "1": rodar("ver_ambiente.py")
        elif escolha == "2": rodar("criar_chave.py")
        elif escolha == "3": rodar("testar_api.py", "--manter")
        elif escolha == "4": rodar("enviar_eventos.py")
        elif escolha in {"5", "6"}:
            flag = input("Filtrar flag_name (Enter mostra todos): ").strip()
            rodar("monitorar_aws.py" if escolha == "5" else "consultar_dynamodb.py", *(["--flag", flag] if flag else []))
        elif escolha == "7":
            flag = input("Flag para avaliar (Enter usa NOME_FLAG do .env): ").strip()
            rodar("gerar_carga.py", *(["--flag", flag] if flag else []))
        elif escolha == "8": rodar("cluster.py", "status")
        elif escolha == "9": rodar("cluster.py", "pausar")
        elif escolha == "10": rodar("cluster.py", "retomar")
        elif escolha == "11": rodar("consultar_rds.py")
        else: print("Opcao invalida.")


if __name__ == "__main__":
    sys.exit(main())
