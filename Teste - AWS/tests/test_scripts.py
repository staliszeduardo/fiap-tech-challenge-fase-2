"""Testes offline: nao enviam eventos nem alteram recursos AWS/Kubernetes."""
import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import boto3
from botocore.stub import Stubber

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum
import cluster
import enviar_eventos
import testar_api

QUEUE = "https://sqs.us-east-1.amazonaws.com/608541039538/fiap-evaluation-analytics-queue"


class TestAws(unittest.TestCase):
    def test_reenvia_somente_falhas_do_lote(self):
        sqs = boto3.client("sqs", region_name="us-east-1", aws_access_key_id="testing", aws_secret_access_key="testing")
        entradas = [{"Id": "m1", "MessageBody": "{}"}, {"Id": "m2", "MessageBody": "{}"}]
        with Stubber(sqs) as stub, patch.object(enviar_eventos, "QUEUE_URL", QUEUE):
            stub.add_response("send_message_batch", {"Successful": [{"Id": "m1", "MessageId": "1", "MD5OfMessageBody": "a"}],
                              "Failed": [{"Id": "m2", "SenderFault": False, "Code": "Throttled"}]}, {"QueueUrl": QUEUE, "Entries": entradas})
            stub.add_response("send_message_batch", {"Successful": [{"Id": "m2", "MessageId": "2", "MD5OfMessageBody": "a"}], "Failed": []},
                              {"QueueUrl": QUEUE, "Entries": [entradas[1]]})
            self.assertEqual(enviar_eventos.enviar_lote(sqs, entradas, esperar=lambda _: None), 2)
            stub.assert_no_pending_responses()

    def test_sender_fault_informa_aceitas_e_nao_repete(self):
        sqs = Mock()
        sqs.send_message_batch.return_value = {"Successful": [{"Id": "m1"}], "Failed": [{"Id": "m2", "SenderFault": True, "Code": "InvalidMessageContents"}]}
        with self.assertRaises(enviar_eventos.EnvioParcialError) as contexto:
            enviar_eventos.enviar_lote(sqs, [{"Id": "m1"}, {"Id": "m2"}])
        self.assertEqual(contexto.exception.aceitas, 1)
        self.assertEqual(sqs.send_message_batch.call_count, 1)

    def test_scan_pagina_vazia_com_continuacao_nao_encerra_busca(self):
        aws = object.__new__(comum.Aws)
        aws.dynamo = boto3.resource("dynamodb", region_name="us-east-1", aws_access_key_id="testing", aws_secret_access_key="testing").meta.client
        chave = {"event_id": {"S": "anterior"}}
        with Stubber(aws.dynamo) as stub:
            stub.add_response("scan", {"Items": [], "Count": 0, "ScannedCount": 2, "LastEvaluatedKey": chave})
            stub.add_response("scan", {"Items": [{"event_id": {"S": "novo"}, "flag_name": {"S": "teste"}, "result": {"BOOL": True}}], "Count": 1, "ScannedCount": 1})
            dados = aws.eventos("teste", paginas=2)
            self.assertEqual(dados["encontrados"], 1)
            self.assertEqual(dados["avaliados"], 3)
            self.assertFalse(dados["parcial"])
            self.assertIs(dados["itens"][0]["result"], True)
            stub.assert_no_pending_responses()

    def test_scan_limitado_sinaliza_parcial(self):
        aws = object.__new__(comum.Aws)
        aws.dynamo = boto3.resource("dynamodb", region_name="us-east-1", aws_access_key_id="testing", aws_secret_access_key="testing").meta.client
        with Stubber(aws.dynamo) as stub:
            stub.add_response("scan", {"Items": [], "Count": 0, "ScannedCount": 200, "LastEvaluatedKey": {"event_id": {"S": "continuacao"}}})
            self.assertTrue(aws.eventos(paginas=1)["parcial"])
            stub.assert_no_pending_responses()

    def test_conta_incorreta_bloqueia_clientes_de_servico(self):
        session = Mock()
        session.client.return_value.get_caller_identity.return_value = {"Account": "000000000000"}
        with patch.object(comum.boto3, "Session", return_value=session), self.assertRaisesRegex(RuntimeError, "Conta atual"):
            comum.Aws()
        self.assertEqual(session.client.call_count, 1)
        session.resource.assert_not_called()

    def test_pausa_nao_altera_scaledobject_de_outro_servico(self):
        objeto = {"spec": {"scaleTargetRef": {"name": "outro-servico"}}}
        with patch.object(cluster, "kubectl", return_value=json.dumps(objeto)) as comando, self.assertRaises(RuntimeError):
            cluster.controlar("pausar")
        self.assertEqual(comando.call_count, 1)

    def test_retomar_remove_anotacoes_sem_mudar_replicas_manualmente(self):
        objeto = {"spec": {"scaleTargetRef": {"name": "analytics-service"}}, "metadata": {"annotations": {"autoscaling.keda.sh/paused-replicas": "0"}}}
        with patch.object(cluster, "kubectl", side_effect=[json.dumps(objeto), "retomado\n"]) as comando, contextlib.redirect_stdout(io.StringIO()):
            cluster.controlar("retomar")
        self.assertEqual(comando.call_count, 2)
        self.assertEqual(comando.call_args.args[-1], "autoscaling.keda.sh/paused-replicas-")


class TestHttp(unittest.TestCase):
    def test_fluxo_real_http_e_limpeza_dos_nomes_exclusivos(self):
        estado = {"flags": {}, "rules": {}, "headers": []}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def responder(self):
                from urllib.parse import urlsplit, parse_qs
                url = urlsplit(self.path)
                estado["headers"].append((self.headers.get("Host"), self.headers.get("Authorization")))
                rota = url.path
                partes = rota.strip("/").split("/")
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
                status, dados = 200, {}
                if rota == "/evaluate":
                    nome = parse_qs(url.query)["flag_name"][0]
                    dados = {"result": estado["flags"][nome]["is_enabled"]}
                elif rota == "/validate":
                    dados = {"message": "valida"}
                else:
                    recurso = partes[0]
                    if self.command == "POST":
                        nome = body.get("name") or body["flag_name"]
                        estado[recurso][nome] = body
                        dados, status = body, 201
                    elif self.command == "GET":
                        dados = estado[recurso][partes[1]]
                    elif self.command == "PUT":
                        estado[recurso][partes[1]].update(body)
                        dados = estado[recurso][partes[1]]
                    elif self.command == "DELETE":
                        del estado[recurso][partes[1]]
                        status = 204
                payload = b"" if status == 204 else json.dumps(dados).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_POST = do_PUT = do_DELETE = responder

        servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        try:
            raiz_testes = Path(__file__).resolve().parents[1]
            pasta_temporaria = raiz_testes / "resultados"
            pasta_temporaria.mkdir(exist_ok=True)
            assert pasta_temporaria.resolve().is_relative_to(raiz_testes)
            with tempfile.TemporaryDirectory(dir=pasta_temporaria) as pasta, patch.object(comum, "PASTA", Path(pasta)), \
                 patch.object(comum, "API_URL", f"http://127.0.0.1:{servidor.server_port}"), \
                 patch.object(comum, "API_HOST", "togglemaster.local"), patch.object(testar_api, "API_KEY", "chave-falsa"), \
                 patch.object(testar_api, "Api", side_effect=lambda: comum.Api("chave-falsa")), contextlib.redirect_stdout(io.StringIO()):
                testar_api.testar(SimpleNamespace(sem_dynamodb=True, manter=False, espera=1, paginas=1))
                resultado = json.loads((Path(pasta) / "resultados/ultimo_teste_api.json").read_text(encoding="utf-8"))
                self.assertTrue(resultado["sucesso"])
            self.assertFalse(estado["flags"])
            self.assertFalse(estado["rules"])
            self.assertTrue(all(host == "togglemaster.local" and chave == "Bearer chave-falsa" for host, chave in estado["headers"]))
        finally:
            servidor.shutdown()
            servidor.server_close()
            thread.join(timeout=3)

    def test_falha_ao_criar_regra_limpa_apenas_a_flag_criada(self):
        api = Mock()
        def chamar(metodo, rota, **kwargs):
            if metodo == "POST" and rota == "/rules": raise RuntimeError("falha simulada")
            if metodo == "GET" and rota.startswith("/flags/"): return {"is_enabled": True}
            return {}
        api.chamar.side_effect = chamar
        with patch.object(testar_api, "API_KEY", "falsa"), patch.object(testar_api, "Api", return_value=api), \
             patch.object(testar_api, "salvar_resultado", return_value="resultado-local"), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "falha simulada"):
            testar_api.testar(SimpleNamespace(sem_dynamodb=True, manter=False))
        delecoes = [c for c in api.chamar.call_args_list if c.args[0] == "DELETE"]
        self.assertEqual(len(delecoes), 1)
        self.assertTrue(delecoes[0].args[1].startswith("/flags/teste-api-aws-"))


if __name__ == "__main__":
    unittest.main()
