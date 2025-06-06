import logging
import sys
from flask import render_template, request
from flask_login import login_required
from database.db_utils import resource_path
from database.models import db, Execution
from . import logs_bp

# Configuração de logging
LOG_FILE = resource_path("logs/controlador.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

@logs_bp.route('/execution_logs', methods=['GET'])
@login_required
def execution_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    query = Execution.query.order_by(Execution.start_time.desc())
    pagination = query.paginate(page=page, per_page=per_page)
    executions = pagination.items

    return render_template(
        'execution_logs.html',
        executions=executions,
        pagination=pagination,
        per_page=per_page
    )

def log_execution(status, records_processed=0, details=None, execution_id=None):
    """
    Registra informações sobre a execução da ETL no banco de dados e nos logs.

    Args:
        status (str): Status da execução (e.g., 'Completed', 'Failed').
        records_processed (int): Número de registros processados.
        details (str): Detalhes adicionais ou mensagens de erro.
        execution_id (int): ID da execução no banco de dados.
    """
    log_message = f"Execution ID: {execution_id}, Status: {status}, Records Processed: {records_processed}, Details: {details}"
    logging.info(log_message)

    # Atualizar os logs no banco de dados, se necessário
    if execution_id:
        execution = db.session.get(Execution, execution_id)
        if execution:
            execution.details = details
            execution.records_processed = records_processed
            db.session.commit()