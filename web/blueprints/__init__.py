from flask import Blueprint

# Inicialização dos Blueprints
auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')
etl_bp = Blueprint('etl', __name__, template_folder='../templates/etl')
logs_bp = Blueprint('logs', __name__, template_folder='../templates/logs')
permissions_bp = Blueprint('permissions', __name__, template_folder='../templates/permissions')
schedules_bp = Blueprint('schedules', __name__, template_folder='../templates/schedules')
users_bp = Blueprint('users', __name__, template_folder='../templates/users')