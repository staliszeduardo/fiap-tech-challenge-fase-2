"""Consulta SQL opcional somente leitura; requer acesso privado/tunel ja existente."""
import argparse
import getpass
import json
import os
import sys

from comum import executar_cli, positivo


def executar(args):
    import psycopg
    from psycopg.rows import dict_row

    destino = os.getenv("RDS_HOST", "").strip()
    if not destino:
        raise ValueError("Configure RDS_HOST/RDS_PORT para um tunel ou destino privado acessivel. O script nao expoe o RDS nem cria um tunel.")
    consultas = {
        "authdb": ("api_keys", "id, name, is_active, created_at", "name"),
        "flagdb": ("flags", "id, name, description, is_enabled, created_at, updated_at", "name"),
        "targetingdb": ("targeting_rules", "id, flag_name, is_enabled, rules, created_at, updated_at", "flag_name"),
    }
    tabela, colunas, coluna_filtro = consultas[args.database]
    # Identificadores vem exclusivamente do dicionario fechado acima; valores sao parametros SQL.
    sql = f"SELECT {colunas} FROM {tabela}"
    parametros = []
    if args.nome:
        sql += f" WHERE {coluna_filtro} = %s"
        parametros.append(args.nome)
    sql += " ORDER BY id DESC LIMIT %s"
    parametros.append(args.limite)
    senha = getpass.getpass("Senha atual do usuario RDS (nao sera salva): ")
    configuracao = dict(host=destino, port=int(os.getenv("RDS_PORT", "15432")), dbname=args.database,
                        user=os.getenv("RDS_USER", "postgres"), password=senha, connect_timeout=10,
                        sslmode=os.getenv("RDS_SSLMODE", "require"),
                        options="-c default_transaction_read_only=on -c statement_timeout=10000", row_factory=dict_row)
    if os.getenv("RDS_SSLROOTCERT"):
        configuracao["sslrootcert"] = os.environ["RDS_SSLROOTCERT"]
    try:
        with psycopg.connect(**configuracao) as conexao:
            registros = conexao.execute(sql, parametros).fetchall()
    except psycopg.Error as erro:
        raise RuntimeError(f"Consulta RDS falhou: {erro}") from erro
    print(f"RDS {args.database}.{tabela} | registros exibidos: {len(registros)}")
    print(json.dumps(registros, indent=2, ensure_ascii=False, default=str))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=["authdb", "flagdb", "targetingdb"], default="flagdb")
    parser.add_argument("--nome", help="Nome exato da flag, regra ou chave a consultar.")
    parser.add_argument("--limite", type=positivo, default=10)
    args = parser.parse_args()
    return executar_cli(lambda: executar(args))


if __name__ == "__main__":
    sys.exit(main())
