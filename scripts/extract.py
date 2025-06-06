import sys
import os
import fdb
import pandas as pd
import hashlib
import logging
import argparse
from google.cloud import bigquery
from google.oauth2 import service_account
from sqlalchemy import create_engine, text
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.db_utils import resource_path, DB_PATH

# Configurar logging
LOG_FILE = os.path.join(resource_path("logs"), "etl_execution.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Capturar o argumento
parser = argparse.ArgumentParser()
parser.add_argument('--execution_id', type=int, required=True, help='ID da execução')
parser.add_argument('--schedule_id', type=int, required=False, help='ID do agendamento')
parser.add_argument('--origin_id', type=int, required=False, help='ID da origem')
parser.add_argument('--script_id', type=int, required=False, help='ID do script')
parser.add_argument('--destination_id', type=int, required=False, help='ID do destino')
args = parser.parse_args()
execution_id = args.execution_id
schedule_id = args.schedule_id
origin_id = args.origin_id
script_id = args.script_id
destination_id = args.destination_id

# Verificar o status da execução no banco de dados
def check_stop_flag(execution_id):
    """Verificar se a execução foi interrompida pelo usuário."""
    engine = create_engine(f"sqlite:///{DB_PATH}")
    with engine.connect() as connection:
        query = text("SELECT status FROM execution WHERE id = :execution_id")
        result = connection.execute(query, {"execution_id": execution_id})
        status = result.fetchone()
        if status and status[0] == 'Stopped':
            logging.info("Execução interrompida pelo usuário.")
            sys.exit(0)

# Recuperar detalhes do agendamento (ou origem, script e destino, caso não seja agendamento)
def get_schedule_details(schedule_id=None, origin_id=None, script_id=None, destination_id=None):
    """Buscar detalhes do agendamento e seus relacionamentos. (Se não for agendamento, buscar detalhes de origem, script e destino.)"""
    if not schedule_id and not (origin_id and script_id and destination_id):
        raise ValueError("É necessário fornecer um schedule_id ou os IDs de origem, script e destino.")
    if schedule_id:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as connection:
            # Buscar informações do agendamento
            query = text("""
                SELECT 
                    s.id AS schedule_id,
                    o.dsn AS origin_dsn,
                    o.user AS origin_user,
                    o.password AS origin_password,
                    d.project_id AS destination_project_id,
                    d.dataset_id AS destination_dataset_id,
                    d.table_id AS destination_table_id,
                    d.keyfile AS destination_keyfile,
                    sc.content AS script_content,
                    sc.id AS script_id
                FROM Scripts sc
                JOIN Schedule s ON s.script_id = sc.id
                JOIN Origins o ON o.id = s.origin_id
                JOIN Destinations d ON d.id = s.destination_id
                WHERE s.id = :schedule_id
            """)
            result = connection.execute(query, {"schedule_id": schedule_id}).mappings().fetchone()
            if not result:
                raise ValueError(f"Agendamento com ID {schedule_id} não encontrado.")
            return result
    else:
        # Buscar informações de origem, script e destino diretamente
        # não há agendamento, por tanto verificar a partir da tabela permissions
        # filtrando pelo usuario também
        from flask_login import current_user
        
        engine = create_engine(f"sqlite:///{DB_PATH}")
        with engine.connect() as connection:
            query = text("""
                SELECT 
                    o.dsn AS origin_dsn,
                    o.user AS origin_user,
                    o.password AS origin_password,
                    d.project_id AS destination_project_id,
                    d.dataset_id AS destination_dataset_id,
                    d.table_id AS destination_table_id,
                    d.keyfile AS destination_keyfile,
                    sc.content AS script_content,
                    sc.id AS script_id
                FROM permissions p
                JOIN Origins o ON o.id = p.origin_id
                JOIN Scripts sc ON sc.id = p.script_id
                JOIN Destinations d ON d.id = p.destination_id
                WHERE p.origin_id = :origin_id
                AND p.script_id = :script_id
                AND p.destination_id = :destination_id
                AND p.user_id = :user_id
            """)
            result = connection.execute(query, {
                "origin_id": origin_id,
                "script_id": script_id,
                "destination_id": destination_id,
                "user_id": current_user.id
            }).mappings().fetchone()
            if not result:
                raise ValueError("Origem, script ou destino não encontrado ou não autorizado.")
            return result

# Recuperar o valor de um parâmetro do script
def get_script_parameters(script_id):
    """Recuperar os parâmetros do script."""
    engine = create_engine(f"sqlite:///{DB_PATH}")
    with engine.connect() as connection:
        query = text("""
            SELECT name, value
            FROM script_parameters
            WHERE script_id = :script_id
        """)
        result = connection.execute(query, {"script_id": script_id}).mappings().fetchall()
        if not result:
            raise ValueError(f"Parâmetros não encontrados para o script ID {script_id}.")
        return {row['name']: row['value'] for row in result}

try:
    # Verificar o sinalizador de interrupção antes de iniciar
    check_stop_flag(execution_id)

    # Obter detalhes do agendamento
    schedule_details = get_schedule_details(schedule_id)

    # Configurações do banco de dados Firebird (Origem)
    dsn = schedule_details['origin_dsn']
    user = schedule_details['origin_user']
    password = schedule_details['origin_password']

    # Configurações do BigQuery (Destino)
    project_id = schedule_details['destination_project_id']
    dataset_id = schedule_details['destination_dataset_id']
    table_id = schedule_details['destination_table_id']
    json_keyfile = schedule_details['destination_keyfile']


    # Configurações do script
    query = schedule_details['script_content']
    # Parâmetros do script
    script_id = schedule_details['script_id']
    script_parameters = get_script_parameters(script_id)

    # Substituir os parâmetros na consulta dinamicamente
    for param_name, param_value in script_parameters.items():
        query = query.replace(f":{param_name}", param_value)
        
    primary_key = script_parameters.get('primary_key')
    unique_key = script_parameters.get('unique_key')

    # Verificar se o script está sendo executado em um ambiente de produção
    if os.getenv('ENV') == 'production':
        # Verificar se o script está sendo executado em um ambiente de produção
        if not os.path.exists(json_keyfile):
            raise FileNotFoundError(f"Arquivo de chave JSON não encontrado: {json_keyfile}")
        if not os.path.isfile(json_keyfile):
            raise ValueError(f"Arquivo de chave JSON inválido: {json_keyfile}")
    else:
        # Logar todas as configurações
        logging.info("Configurações do Firebird:")
        logging.info("dsn: %s", dsn)
        logging.info("user: %s", user)
        logging.info("password: %s", password)
        logging.info("Configurações do BigQuery:")
        logging.info("project_id: %s", project_id)
        logging.info("dataset_id: %s", dataset_id)
        logging.info("table_id: %s", table_id)
        logging.info("json_keyfile: %s", json_keyfile)
        logging.info("Configurações do script:")
        logging.info("query: %s", query)
        logging.info("Parâmetros do script:")
        for param_name, param_value in script_parameters.items():
            logging.info("%s: %s", param_name, param_value)
        logging.info("Parâmetro primary_key: %s", primary_key)
        logging.info("Parâmetro unique_key: %s", unique_key)

    # Conectar ao Firebird
    logging.info("Conectando ao Firebird...")
    conn = fdb.connect(dsn=dsn, user=user, password=password)
    cursor = conn.cursor()

    # Verificar o sinalizador de interrupção antes de executar a consulta
    check_stop_flag(execution_id)

    logging.info("Buscando dados da fonte origem...")
    # Executar a consulta e obter os dados
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    df_firebird = pd.DataFrame(cursor.fetchall(), columns=columns)
    df_firebird.replace({r'\r\n': ' ', r'\r': ' ', r'\n': ' '}, regex=True, inplace=True)

    # Calcular o hash MD5 para a chave primária
    df_firebird[unique_key] = df_firebird.apply(
        lambda row: '|'.join(map(lambda x: str(x) if pd.notna(x) else '', row)), axis=1
    )
    df_firebird[primary_key] = df_firebird[unique_key].apply(
        lambda x: hashlib.md5(x.encode()).hexdigest()
    )
    df_firebird.drop(unique_key, axis=1, inplace=True)

    # Reorganizar as colunas para que a coluna primary_key seja a primeira
    df_firebird = df_firebird[[primary_key] + [col for col in df_firebird.columns if col != primary_key]]

    logging.info(f"Dados extraídos do Firebird: {len(df_firebird)} registros.")

    # Verificar o sinalizador de interrupção antes de carregar os dados no BigQuery
    check_stop_flag(execution_id)

    # Configurar cliente do BigQuery
    credentials = service_account.Credentials.from_service_account_file(json_keyfile)
    client = bigquery.Client(project=project_id, credentials=credentials)

    # Verificar se a tabela já existe no BigQuery
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    try:
        client.get_table(table_ref)
        table_exists = True
    except Exception:
        table_exists = False

    if not table_exists:
        logging.info(f"Tabela {table_id} não encontrada. Criando tabela diretamente a partir do DataFrame...")
        if df_firebird.empty:
            raise ValueError("O DataFrame do Firebird está vazio. A tabela não pode ser criada sem dados.")
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_EMPTY")
        client.load_table_from_dataframe(df_firebird, table_ref, job_config=job_config).result()
        logging.info(f"Tabela {table_id} criada com sucesso.")
    else:
        logging.info(f"Tabela {table_id} já existe. Processando os dados normalmente...")
        query_existing = f"SELECT * FROM `{project_id}.{dataset_id}.{table_id}`"
        df_bigquery = client.query(query_existing).to_dataframe()

        df_insert = df_firebird[~df_firebird[primary_key].isin(df_bigquery[primary_key])]
        df_update = df_firebird[df_firebird[primary_key].isin(df_bigquery[primary_key])]
        df_delete = df_bigquery[~df_bigquery[primary_key].isin(df_firebird[primary_key])]

        if not df_insert.empty:
            job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
            client.load_table_from_dataframe(df_insert, table_ref, job_config=job_config).result()
            logging.info(f"{len(df_insert)} registros inseridos.")

        if not df_update.empty:
            try:
                temp_table = f"{dataset_id}.temp_table"
                client.load_table_from_dataframe(df_update, temp_table, job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")).result()
                update_fields = ', '.join([f"target.{col} = source.{col}" for col in df_firebird.columns if col != primary_key])
                merge_query = f"""
                MERGE `{table_ref}` AS target
                USING `{project_id}.{temp_table}` AS source
                ON target.{primary_key} = source.{primary_key}
                WHEN MATCHED THEN
                UPDATE SET {update_fields}
                """
                client.query(merge_query).result()
                logging.info(f"{len(df_update)} registros atualizados.")
            except Exception as e:
                logging.error(f"Erro ao executar a consulta MERGE: {e}")
                raise
            finally:
                # Excluir a tabela temporária
                try:
                    client.delete_table(temp_table)
                except Exception as e:
                    logging.error(f"Erro ao excluir a tabela temporária {temp_table}: {e}")

        if not df_delete.empty:
            try:
                delete_query = f"""
                DELETE FROM `{table_ref}`
                WHERE {primary_key} IN ({', '.join([f"'{val}'" for val in df_delete[primary_key].tolist()])})
                """
                client.query(delete_query).result()
                logging.info(f"{len(df_delete)} registros deletados.")
            except Exception as e:
                logging.error(f"Erro ao executar a consulta DELETE: {e}")
                raise

    # Após o processamento dos dados no BigQuery
    records_processed = len(df_firebird)
    logging.info(f"Total de registros processados: {records_processed}")
    print(f"RECORDS_PROCESSED={records_processed}")

except Exception as e:
    logging.error(f"Erro durante a execução: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
    logging.info("Conexão encerrada.")
