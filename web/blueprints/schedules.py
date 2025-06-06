from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from database.models import Schedule, Execution, db
from .logs import log_execution
from datetime import datetime
import subprocess
from . import schedules_bp
from .users import is_admin
from .etl import extract_script_path
from apscheduler.triggers.cron import CronTrigger

def scheduled_etl(schedule_id):
    from web.monitor import app
    with app.app_context():
        try:
            # Crie uma nova execução e obtenha o ID
            new_execution = Execution(schedule_id=schedule_id, status='Running', start_time=datetime.now())
            db.session.add(new_execution)
            db.session.commit()
            execution_id = new_execution.id

            result = subprocess.run(
                [
                    'python',
                    extract_script_path,
                    '--execution_id', str(execution_id),
                    '--schedule_id', str(schedule_id)
                ],
                capture_output=True,
                text=True
            )

            status = 'Completed' if result.returncode == 0 else 'Failed'
            log_message = result.stdout if result.returncode == 0 else result.stderr

            # Encontrar a linha que contém o número de registros processados e extrai o valor
            # Inicializa records_processed como 0
            records_processed = 0

            for line in log_message.splitlines():
                if line.startswith('RECORDS_PROCESSED='):
                    records_processed = int(line.split('=')[-1].strip())
                    break
            
            # Remove a linha de contagem de registros processados do log
            log_message = "\n".join([line for line in log_message.splitlines() if not line.startswith('RECORDS_PROCESSED=')])

            log_execution(status=status, details=log_message, execution_id=execution_id, records_processed=records_processed)
        except Exception as e:
            log_execution(status='Failed', details=f"Erro ao executar a ETL agendada: {e}", execution_id=execution_id)

def add_job_to_scheduler(schedule):
    """
    Adiciona um agendamento ao APScheduler usando apenas cron_expression.
    """
    from web.monitor import scheduler
    job_id = f"schedule_{schedule.id}"  # Torna único
    # Remova o job antigo se existir
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    try:
        # Cria o gatilho e adiciona o job ao scheduler
        trigger = CronTrigger.from_crontab(schedule.cron_expression)
        scheduler.add_job(
            scheduled_etl,
            trigger,
            id=job_id,
            args=[schedule.id],
            max_instances=2,
            misfire_grace_time=120
        )
    except Exception as e:
        raise ValueError(f"Erro ao adicionar agendamento {schedule.id}: {e}")

def load_schedules():
    """
    Carrega os agendamentos do banco de dados e os registra no APScheduler.
    """
    from web.monitor import scheduler
    schedules = Schedule.query.filter_by(active=True).all()

    # Buscar o último log de agendamento ativo
    last_scheduled_execution = Execution.query.filter_by(status='Scheduled').order_by(Execution.start_time.desc()).first()

    if schedules:
        if last_scheduled_execution:
            # Atualizar o último log de agendamento ativo
            last_scheduled_execution.start_time = datetime.now()
            last_scheduled_execution.end_time = None  # Garantir que ele continue "Em andamento"
            db.session.commit()
        else:
            # Criar um novo log de agendamento se não houver nenhum ativo
            log_execution(status='Scheduled', details="Agendamentos carregados ao iniciar o servidor.")

        # Concluir todos os outros logs de agendamento que ainda estejam "Em andamento"
        other_scheduled_executions = Execution.query.filter(
            Execution.status == 'Scheduled',
            Execution.id != last_scheduled_execution.id if last_scheduled_execution else True
        ).all()

        for execution in other_scheduled_executions:
            execution.status = 'Completed'
            execution.end_time = datetime.now()
            db.session.commit()

        # Adicionar os agendamentos ao APScheduler
        for schedule in schedules:
            try:
                add_job_to_scheduler(schedule)
            except Exception as e:
                log_execution(status='Failed', details=f"Erro ao carregar o agendamento {schedule.id}: {e}")

    else:
        # Concluir todos os logs de execução que ainda estejam "Em andamento"
        ongoing_executions = Execution.query.filter(Execution.status == 'Scheduled').all()
        for execution in ongoing_executions:
            execution.status = 'Completed'
            execution.end_time = datetime.now()
            db.session.commit()

        # Registrar um log informando que não há agendamentos ativos
        log_execution(status='Info', details="Nenhum agendamento ativo encontrado no banco de dados.")

@schedules_bp.route('/manage_schedules', methods=['GET', 'POST'])
@login_required
def manage_schedules():
    is_admin()
    from flask_login import current_user
    from database.db_utils import get_user_allowed_origins, get_user_allowed_scripts, get_user_allowed_destinations

    if request.method == 'POST':
        # Obter os dados do formulário
        name = request.form.get('name')
        origin_id = request.form.get('origin_id')
        script_id = request.form.get('script_id')
        destination_id = request.form.get('destination_id')
        cron_expression = request.form.get('cron_expression')
        active = request.form.get('active') == 'true'
        schedule_id = request.form.get('schedule_id')

        # CONVERTA OS IDS PARA INTEIRO SE NÃO FOREM NULOS
        origin_id_int = int(origin_id) if origin_id else None
        script_id_int = int(script_id) if script_id else None
        destination_id_int = int(destination_id) if destination_id else None
        schedule_id_int = int(schedule_id) if schedule_id else None

        # Verificação de conflito de agendamento
        if Schedule.has_conflict(origin_id_int, script_id_int, destination_id_int, cron_expression, schedule_id_int):
            flash('Já existe um agendamento com esses parâmetros e horário!', 'danger')
            return redirect(url_for('schedules.manage_schedules'))

        # Validar os campos obrigatórios
        if not name or not origin_id or not script_id or not destination_id or not cron_expression:
            flash('Nome, origem, script, destino e expressão CRON são obrigatórios!', 'danger')
            return redirect(url_for('schedules.manage_schedules'))

        allowed_origin_ids = [str(o["id"]) for o in get_user_allowed_origins(current_user.id)]
        allowed_script_ids = [str(s["id"]) for s in get_user_allowed_scripts(current_user.id)]
        allowed_destination_ids = [str(d["id"]) for d in get_user_allowed_destinations(current_user.id)]

        # Verificar se o usuário tem permissão para usar os recursos selecionados
        if (origin_id not in allowed_origin_ids or
            script_id not in allowed_script_ids or
            destination_id not in allowed_destination_ids):
            flash('Você não tem permissão para criar agendamentos com esses recursos!', 'danger')
            return redirect(url_for('schedules.manage_schedules'))

        if schedule_id:
            # Atualizar agendamento existente
            schedule = Schedule.query.get(schedule_id_int)
            schedule.name = name
            schedule.origin_id = origin_id_int
            schedule.script_id = script_id_int
            schedule.destination_id = destination_id_int
            schedule.cron_expression = cron_expression
            schedule.active = active
        else:
            # Criar novo agendamento
            schedule = Schedule(
                name=name,
                origin_id=origin_id_int,
                script_id=script_id_int,
                destination_id=destination_id_int,
                cron_expression=cron_expression,
                active=active
            )
            db.session.add(schedule)

        db.session.commit()

        # Atualizar os agendamentos no APScheduler
        load_schedules()

        flash('Agendamento salvo com sucesso!', 'success')
        return redirect(url_for('schedules.manage_schedules'))

    schedules = Schedule.query.all()
    return render_template(
        'manage_schedules.html',
        schedules=schedules
    )

@schedules_bp.route('/delete_schedule/<int:schedule_id>', methods=['POST'])
@login_required
def delete_schedule(schedule_id):
    is_admin()
    schedule = Schedule.query.get_or_404(schedule_id)
    from web.monitor import scheduler
    try:
        scheduler.remove_job(f"schedule_{schedule_id}")
    except Exception:
        pass
    db.session.delete(schedule)
    db.session.commit()
    load_schedules()
    flash('Agendamento excluído com sucesso!', 'success')
    return redirect(url_for('schedules.manage_schedules'))

@schedules_bp.route('/create_schedule', methods=['GET', 'POST'])
@login_required
def create_schedule():
    return redirect(url_for('schedules.manage_schedules'))

@schedules_bp.route('/get_scripts_for_origin/<int:origin_id>')
@login_required
def get_scripts_for_origin(origin_id):
    from flask_login import current_user
    from database.db_utils import get_user_allowed_scripts_for_origin
    scripts = get_user_allowed_scripts_for_origin(current_user.id, origin_id)
    return jsonify(scripts)

@schedules_bp.route('/get_destinations_for_origin_script/<int:origin_id>/<int:script_id>')
@login_required
def get_destinations_for_origin_script(origin_id, script_id):
    from flask_login import current_user
    from database.db_utils import get_user_allowed_destinations_for_origin_script
    destinations = get_user_allowed_destinations_for_origin_script(current_user.id, origin_id, script_id)
    return jsonify(destinations)

# Editar agendamento (GET para carregar, POST para salvar)
@schedules_bp.route('/edit_schedule/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    if request.method == 'POST':
        # Atualize os campos conforme o formulário
        schedule.name = request.form.get('name')
        schedule.origin_id = request.form.get('origin_id')
        schedule.script_id = request.form.get('script_id')
        schedule.destination_id = request.form.get('destination_id')
        schedule.cron_expression = request.form.get('cron_expression')
        schedule.active = request.form.get('active') == 'true'
        db.session.commit()
        load_schedules()  # Atualiza as tarefas agendadas
        flash('Agendamento atualizado com sucesso!', 'success')
        return redirect(url_for('schedules.manage_schedules'))
    # GET: renderize o formulário de edição
    # Passe os dados necessários para o template
    return render_template('edit_schedule.html', schedule=schedule)

# Pausar agendamento
@schedules_bp.route('/pause_schedule/<int:schedule_id>', methods=['POST'])
@login_required
def pause_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    schedule.active = False
    db.session.commit()
    load_schedules()
    flash('Agendamento pausado com sucesso!', 'success')
    return redirect(url_for('schedules.manage_schedules'))

# Retomar agendamento
@schedules_bp.route('/resume_schedule/<int:schedule_id>', methods=['POST'])
@login_required
def resume_schedule(schedule_id):
    schedule = Schedule.query.get_or_404(schedule_id)
    schedule.active = True
    db.session.commit()
    load_schedules()
    flash('Agendamento retomado com sucesso!', 'success')
    return redirect(url_for('schedules.manage_schedules'))