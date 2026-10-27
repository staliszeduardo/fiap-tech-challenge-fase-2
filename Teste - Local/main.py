"""Menu interativo para gerenciar e testar flags pelas APIs HTTP."""

import math
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote

from dotenv import dotenv_values
import requests

from http_info import mostrar_solicitacao


PASTA = Path(__file__).resolve().parent
ARQUIVO_ENV = PASTA / ".env"

OPERACOES = {
    "1": ("Criar flag", "criar_flag.py"),
    "2": ("Listar flags", "listar_flags.py"),
    "3": ("Consultar flag", "consultar_flag.py"),
    "4": ("Editar flag (descrição e ativar/desativar)", "atualizar_flag.py"),
    "5": ("Excluir flag", "excluir_flag.py"),
    "6": ("Criar regra com porcentagem personalizada", "criar_regra.py"),
    "7": ("Consultar regra", "consultar_regra.py"),
    "8": ("Editar regra (porcentagem e ativar/desativar)", "atualizar_regra.py"),
    "9": ("Excluir regra", "excluir_regra.py"),
    "10": ("Avaliar flag para um usuário", "avaliar_flag.py"),
    "11": ("Criar chave de API e salvar no .env", "criar_chave.py"),
    "12": ("Validar chave de API", "validar_chave.py"),
    "13": ("Executar teste do fluxo completo", "testar_fluxo.py"),
    "14": ("Escolher flag e usuário de referência", None),
    "15": ("Criar flag personalizada", "criar_flag.py"),
}


def configuracao_atual():
    # Não carregar no ambiente: a opção 11 pode salvar uma chave nova a qualquer momento.
    return {**dotenv_values(ARQUIVO_ENV), **os.environ}


def consultar_api(servico, caminho):
    configuracao = configuracao_atual()
    padrao = {"FLAG_URL": "http://localhost:8002", "TARGETING_URL": "http://localhost:8003"}
    base = (configuracao.get("API_URL") or configuracao.get(servico) or padrao[servico]).rstrip("/")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {configuracao.get('API_KEY', '')}",
    }
    if configuracao.get("API_HOST"):
        headers["Host"] = configuracao["API_HOST"]
    try:
        resposta = requests.get(f"{base}{caminho}", headers=headers, timeout=10)
    except requests.RequestException as erro:
        print(f"\nNão foi possível consultar a API: {erro}")
        return None
    mostrar_solicitacao(resposta.request)
    print(f"HTTP {resposta.status_code}")
    if not resposta.ok:
        print(resposta.text)
        return None
    try:
        return resposta.json()
    except ValueError:
        print("\nA API retornou uma resposta que não é JSON.")
        return None


def mostrar_menu(nome_flag, user_id):
    print("\n" + "=" * 62)
    print("TOGGLEMASTER - TESTES DA API")
    print("=" * 62)
    print(f"Última flag utilizada: {nome_flag or 'nenhuma'}")
    print(f"Usuário de referência: {user_id}")
    print("Você escolhe a flag em cada operação.\n")
    for numero, (descricao, _) in OPERACOES.items():
        print(f"{numero:>2} - {descricao}")
    print(" 0 - Sair")


def escolher_flag(nome_anterior):
    flags = consultar_api("FLAG_URL", "/flags")
    if flags is None:
        return None
    if not flags:
        print("\nNenhuma flag cadastrada. Use a opção 1 para criar uma.")
        return None
    print("\nFlags disponíveis:")
    for numero, flag in enumerate(flags, 1):
        estado = "ativa" if flag["is_enabled"] else "inativa"
        print(f"{numero:>2} - {flag['name']} ({estado})")
    print("Para escolher um nome numérico, use nome:123.")

    anterior = next((flag for flag in flags if flag["name"] == nome_anterior), None)
    sugestao = f"; Enter mantém {nome_anterior}" if anterior else ""
    while True:
        escolha = input(f"Escolha pelo número ou nome (0 cancela{sugestao}): ").strip()
        if escolha == "0":
            return None
        if not escolha and anterior:
            return anterior
        nome_explicito = escolha.startswith("nome:")
        if not nome_explicito and escolha.isdecimal() and 1 <= int(escolha) <= len(flags):
            return flags[int(escolha) - 1]
        nome = escolha[5:].strip() if nome_explicito else escolha
        encontrada = next((flag for flag in flags if flag["name"] == nome), None)
        if encontrada:
            return encontrada
        print("Escolha um dos números ou digite o nome de uma flag da lista.")


def ler_nome():
    while True:
        nome = input("Nome da nova flag (ex.: novo-checkout): ").strip()
        if not nome:
            print("Informe um nome para a nova flag.")
        elif nome in {".", ".."}:
            print("O nome da flag não pode ser . ou ..")
        elif len(nome) > 100:
            print("O nome deve ter no máximo 100 caracteres.")
        elif any(caractere in nome for caractere in "/?#%"):
            print("O nome não pode conter /, ?, # ou %.")
        else:
            return nome


def ler_nome_chave():
    while True:
        nome = input("Nome da chave de API [teste-python]: ").strip() or "teste-python"
        if len(nome) <= 100:
            return nome
        print("O nome deve ter no máximo 100 caracteres.")


def ler_sim_nao(pergunta, padrao=True):
    opcoes = "S/n" if padrao else "s/N"
    while True:
        escolha = input(f"{pergunta} [{opcoes}]: ").strip().casefold()
        if not escolha:
            return padrao
        if escolha in {"s", "sim"}:
            return True
        if escolha in {"n", "nao", "não"}:
            return False
        print("Digite S para sim ou N para não.")


def ler_porcentagem(padrao):
    while True:
        valor = input(f"Porcentagem de usuários, de 0 a 100 [{padrao:g}]: ").strip()
        if not valor:
            return padrao
        try:
            porcentagem = float(valor.replace(",", "."))
        except ValueError:
            porcentagem = math.nan
        if math.isfinite(porcentagem) and 0 <= porcentagem <= 100:
            return porcentagem
        print("Informe um número entre 0 e 100.")


def executar_operacao(opcao, nome_flag, user_id, argumentos=()):
    descricao, script = OPERACOES[opcao]
    print(f"\n--- {descricao} ---", flush=True)
    if opcao == "13":
        print("O fluxo usa uma flag exclusiva e remove seus dados ao terminar.", flush=True)
    ambiente = {**os.environ, "USER_ID": user_id}
    if nome_flag:
        ambiente["NOME_FLAG"] = nome_flag
    resultado = subprocess.run(
        [sys.executable, str(PASTA / script), *argumentos],
        cwd=PASTA,
        env=ambiente,
        check=False,
    )
    if resultado.returncode != 0:
        print("\nA operação falhou. Confira a resposta acima; o menu continua disponível.")
    elif opcao in {"4", "5", "6", "8", "9"}:
        print("\nA avaliação pode usar os dados anteriores do cache por até 30 segundos.")
    return resultado.returncode == 0


def criar_flag(opcao, user_id):
    print("\n--- Nova flag ---")
    nome = ler_nome()
    descricao = input("Descrição (opcional): ").strip()
    ativa = ler_sim_nao("A flag começa ativa?")
    argumentos = (f"--nome={nome}", f"--descricao={descricao}", "--ativa" if ativa else "--inativa")
    if executar_operacao(opcao, nome, user_id, argumentos):
        print(f"\nFlag '{nome}' criada.")
        return nome
    return None


def editar_flag(flag, user_id):
    print(f"\nEditando a flag: {flag['name']}")
    descricao_atual = flag.get("description") or ""
    print(f"Descrição atual: {descricao_atual or '(vazia)'}")
    descricao = input("Nova descrição (Enter mantém; - limpa): ").strip()
    if not descricao:
        descricao = descricao_atual
    elif descricao == "-":
        descricao = ""
    ativa = ler_sim_nao("A flag deve ficar ativa?", flag["is_enabled"])
    argumentos = []
    if descricao != descricao_atual:
        argumentos.append(f"--descricao={descricao}")
    if ativa != flag["is_enabled"]:
        argumentos.append("--ativa" if ativa else "--inativa")
    if not argumentos:
        print("\nNenhuma alteração informada. A flag foi mantida.")
        return
    executar_operacao("4", flag["name"], user_id, argumentos)


def configurar_regra(opcao, flag, user_id):
    porcentagem, ativa = 100, True
    if opcao == "8":
        regra = consultar_api("TARGETING_URL", f"/rules/{quote(flag['name'], safe='')}")
        if regra is None:
            return
        if regra.get("rules", {}).get("type") != "PERCENTAGE":
            print("Este menu edita regras do tipo PERCENTAGE.")
            return
        porcentagem = regra["rules"]["value"]
        ativa = regra["is_enabled"]
    print(f"\nConfigurando a regra da flag: {flag['name']}")
    porcentagem = ler_porcentagem(porcentagem)
    ativa = ler_sim_nao("A regra deve ficar ativa?", ativa)
    argumentos = (f"--porcentagem={porcentagem}", "--ativa" if ativa else "--inativa")
    executar_operacao(opcao, flag["name"], user_id, argumentos)


def main():
    configuracao = configuracao_atual()
    nome_flag = None
    user_id = configuracao.get("USER_ID") or "usuario-123"
    if not ARQUIVO_ENV.is_file():
        print("Configure o .env desta pasta conforme o README antes de acessar as APIs.")

    while True:
        mostrar_menu(nome_flag, user_id)
        opcao = input("\nEscolha uma opção: ").strip()
        if opcao == "0":
            print("Menu encerrado.")
            return
        if opcao not in OPERACOES:
            print("\nOpção inválida. Digite um dos números do menu.")
            continue

        if opcao in {"1", "15"}:
            nome_criado = criar_flag(opcao, user_id)
            if nome_criado:
                nome_flag = nome_criado
        elif opcao in {"3", "4", "5", "6", "7", "8", "9", "10", "14"}:
            flag = escolher_flag(nome_flag)
            if flag is not None:
                nome_flag = flag["name"]
                if opcao == "4":
                    editar_flag(flag, user_id)
                elif opcao in {"6", "8"}:
                    configurar_regra(opcao, flag, user_id)
                elif opcao in {"10", "14"}:
                    user_id = input(f"ID do usuário [{user_id}]: ").strip() or user_id
                    if opcao == "10":
                        executar_operacao(opcao, nome_flag, user_id)
                else:
                    sucesso = executar_operacao(opcao, nome_flag, user_id)
                    if opcao == "5" and sucesso:
                        nome_flag = None
        elif opcao == "11":
            executar_operacao(opcao, nome_flag, user_id, (f"--nome={ler_nome_chave()}",))
        else:
            executar_operacao(opcao, nome_flag, user_id)
        input("\nPressione Enter para voltar ao menu...")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nMenu encerrado.")
