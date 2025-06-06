from flask import jsonify, request, flash, redirect, url_for, render_template
from flask_login import login_required
from .logs import log_execution
from . import etl_bp
from datetime import datetime
from database.models import db, Execution, Destination, Script
import threading
import subprocess
import logging

extract_script_path = "scripts/extract.py"

def run_etl_task(execution_id, schedule_id=None, origin_id=None, destination_id=None, script_id=None):
    from web.monitor import app
    with app.app_context():
        try:
            execution = db.session.get(Execution, execution_id)
            if not execution:
                logging.error(f"Execução com ID {execution_id} não encontrada.")
                return

            # Atualizar o status da execução para "Running"
            execution.status = 'Running'
            execution.start_time = datetime.now()
            db.session.commit()

            # adicinar log para depuração
            logging.info(f"Iniciando ETL com ID de execução: {execution_id}, Schedule ID: {schedule_id}, Origin ID: {origin_id}, Script ID: {script_id}, Destination ID: {destination_id}")

            # Executar o script ETL
            args = [
                'python',
                extract_script_path,
                '--execution_id', str(execution_id)
            ]
            if schedule_id:
                args += ['--schedule_id', str(schedule_id)]
            else:
                if origin_id:
                    args += ['--origin_id', str(origin_id)]
                if script_id:
                    args += ['--script_id', str(script_id)]
                if destination_id:
                    args += ['--destination_id', str(destination_id)]

            result = subprocess.run(
                args,
                capture_output=True,
                text=True
            )

            # Determinar o status da execução
            status = 'Completed' if result.returncode == 0 else 'Failed'
            log_message = result.stdout if result.returncode == 0 else result.stderr

            # Extrair o número de registros processados
            records_processed = 0
            for line in result.stdout.splitlines():
                if line.startswith("RECORDS_PROCESSED="):
                    records_processed = int(line.split("=")[1])
            
            # adicinar log para depuração
            logging.info(f"ETL finalizada com status: {status}, Records Processed: {records_processed}, Log: {log_message}")

            # Atualizar o status e os detalhes no banco de dados
            execution.status = status
            execution.end_time = datetime.now()
            execution.records_processed = records_processed
            execution.details = log_message
            db.session.commit()

            log_execution(status=status, records_processed=records_processed, details=log_message, execution_id=execution_id)
        except Exception as e:
            execution = db.session.get(Execution, execution_id)
            if execution:
                execution.status = 'Failed'
                execution.end_time = datetime.now()
                db.session.commit()

            log_execution(status='Failed', details=f"Erro ao executar a ETL: {e}", execution_id=execution_id)

@etl_bp.route('/start_etl', methods=['POST'])
@login_required
def start_etl():
    # adicinar log para depuração
    logging.info("Iniciando o processo ETL...")
    data = request.get_json()
    schedule_id = data.get('schedule_id')
    origin_id = data.get('origin_id')
    script_id = data.get('script_id')
    destination_id = data.get('destination_id')
    # Use esses parâmetros conforme sua lógica
    # Verificar se já existe uma execução em andamento
    ongoing_execution = Execution.query.filter_by(status='Running').first()
    if ongoing_execution:
        return jsonify({'error': 'Já existe uma execução em andamento!'}), 400

    try:
        # Registrar a execução como "Running"
        new_execution = Execution(
            start_time=datetime.now(),
            status='Running',
            details='Processo ETL iniciado.'
        )
        db.session.add(new_execution)
        db.session.commit()

        execution_id = new_execution.id

        # Montar kwargs apenas com os parâmetros informados
        kwargs = {'execution_id': execution_id}
        if schedule_id:
            kwargs['schedule_id'] = schedule_id
        if origin_id:
            kwargs['origin_id'] = origin_id
        if script_id:
            kwargs['script_id'] = script_id
        if destination_id:
            kwargs['destination_id'] = destination_id
            
        # adicinar log para depuração
        logging.info(f"Parâmetros da ETL: {kwargs}")

        # Iniciar a tarefa em um subprocesso separado
        thread = threading.Thread(target=run_etl_task, kwargs=kwargs)
        thread.start()

        # adicinar log para depuração
        logging.info(f"ETL finalizada com sucesso! Execution ID: {execution_id}")

        return jsonify({'message': 'ETL iniciada com sucesso!', 'execution_id': execution_id})
    except Exception as e:
        log_execution(status='Failed', details=f"Erro ao iniciar a ETL: {e}")
        return jsonify({'error': f"Erro ao iniciar a ETL: {e}"}), 500

@etl_bp.route('/stop_etl', methods=['POST'])
@login_required
def stop_etl():
    # Lógica para parar o ETL
    log_execution('Parado')
    return jsonify({'success': True, 'message': 'ETL parado com sucesso!'})

@etl_bp.route('/stop_etl/<int:execution_id>', methods=['POST'])
@login_required
def stop_etl_with_id(execution_id):
    try:
        execution = db.session.get(Execution, execution_id)
        if not execution:
            return jsonify({'error': 'Execução não encontrada!'}), 404

        if execution.status in ['Completed', 'Stopped']:
            return jsonify({'error': 'Execução já foi concluída ou interrompida!'}), 400

        execution.status = 'Stopped'
        execution.end_time = datetime.now()
        db.session.commit()

        log_execution(status='Stopped', details=f"Execução {execution_id} interrompida manualmente.", execution_id=execution_id)
        return jsonify({'message': 'ETL parada com sucesso!'})
    except Exception as e:
        log_execution(status='Failed', details=f"Erro ao interromper a execução {execution_id}: {e}", execution_id=execution_id)
        return jsonify({'error': 'Erro ao parar a execução!'}), 500

def start_etl_task(origin_id, destination_id, script_id):
    new_execution = Execution(
        start_time=datetime.now(),
        status='Running',
        details=f'ETL iniciada para o destino {destination_id} e script {script_id} na origem {origin_id}.'
    )
    db.session.add(new_execution)
    db.session.commit()

    # Iniciar a tarefa em um subprocesso
    execution_id = new_execution.id
    thread = threading.Thread(
        target=run_etl_task,
        kwargs={
            'execution_id': execution_id,
            'origin_id': origin_id,
            'destination_id': destination_id,
            'script_id': script_id
        }
    )
    
    thread.start()

    return execution_id

@etl_bp.route('/get_last_execution_status/<int:schedule_id>')
@login_required
def get_last_execution_status(schedule_id):
    last_exec = Execution.query.filter_by(schedule_id=schedule_id).order_by(Execution.start_time.desc()).first()
    if last_exec:
        return jsonify({
            "status": last_exec.status,
            "execution_id": last_exec.id
        })
    return jsonify({"status": "None", "execution_id": None})