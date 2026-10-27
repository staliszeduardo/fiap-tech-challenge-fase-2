"""Consulta Pods/HPA/KEDA e pausa/retoma somente o ScaledObject do analytics."""
import argparse
import json
import os
import subprocess
import sys

from comum import EXPECTED_ACCOUNT, REGION, executar_cli


def kubectl(*argumentos):
    contexto = os.getenv("KUBECTL_CONTEXT", f"arn:aws:eks:{REGION}:{EXPECTED_ACCOUNT}:cluster/fiap-techchallenge")
    namespace = os.getenv("KUBERNETES_NAMESPACE", "togglemaster")
    processo = subprocess.run(["kubectl", "--context", contexto, "--request-timeout=15s", "-n", namespace, *argumentos],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25, check=False)
    if processo.returncode:
        raise RuntimeError("kubectl: " + processo.stderr.strip()[:1000])
    return processo.stdout


def mostrar_status():
    print(kubectl("get", "deployment,pod,hpa"), end="")
    print(kubectl("get", "scaledobject"), end="")


def replicas():
    resposta = json.loads(kubectl("get", "deployment", "analytics-service", "-o", "json"))
    status = resposta.get("status", {})
    return f"{status.get('readyReplicas', 0)}/{resposta['spec'].get('replicas', 0)}"


def controlar(acao):
    nome = os.getenv("KEDA_SCALEDOBJECT", "analytics-sqs")
    objeto = json.loads(kubectl("get", "scaledobject", nome, "-o", "json"))
    if objeto["spec"]["scaleTargetRef"]["name"] != "analytics-service":
        raise RuntimeError("O ScaledObject configurado nao aponta para analytics-service; operacao cancelada.")
    if acao == "pausar":
        print(kubectl("annotate", "scaledobject", nome, "autoscaling.keda.sh/paused-replicas=0", "--overwrite"), end="")
        print("Analytics pausado em zero replicas. Aguarde Pods terminarem antes de enviar o lote.")
    else:
        anotacoes = objeto["metadata"].get("annotations", {})
        for chave in ("autoscaling.keda.sh/paused-replicas", "autoscaling.keda.sh/paused"):
            if chave in anotacoes:
                print(kubectl("annotate", "scaledobject", nome, chave + "-"), end="")
        print("Escala automatica retomada. Acompanhe python monitorar_aws.py --cluster")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=["status", "pausar", "retomar"], nargs="?", default="status")
    args = parser.parse_args()
    return executar_cli(mostrar_status if args.acao == "status" else lambda: controlar(args.acao))


if __name__ == "__main__":
    sys.exit(main())
