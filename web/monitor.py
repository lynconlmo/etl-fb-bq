import atexit
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from waitress import serve
from flask import Flask, render_template, request, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_required
from flask_wtf.csrf import CSRFProtect
# from flask_talisman import Talisman
# import ssl
from .blueprints.logs import logs_bp, log_execution
from .blueprints.users import users_bp
from .blueprints.schedules import schedules_bp, load_schedules
from .blueprints.etl import etl_bp
from .blueprints.auth import auth_bp
from .blueprints.permissions import permissions_bp
from database.models import db, User, Execution
from database.db_utils import DB_PATH

# Configuração do Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SECRET_KEY'] = 'supersecretkey'

# Inicialização de extensões
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
csrf = CSRFProtect(app)
# Talisman(app, content_security_policy=None, force_https=False)

# Registro de Blueprints
app.register_blueprint(logs_bp, url_prefix='/logs')
app.register_blueprint(users_bp, url_prefix='/users')
app.register_blueprint(schedules_bp, url_prefix='/schedules')
app.register_blueprint(etl_bp, url_prefix='/etl')
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(permissions_bp, url_prefix='/permissions')

# Configuração do APScheduler
scheduler = BackgroundScheduler(timezone="America/La_Paz")
scheduler.start()

# Certifique-se de parar o agendador ao encerrar o aplicativo
atexit.register(lambda: scheduler.shutdown())

def initialize_schedules():
    with app.app_context():
        # Registrar o evento de reinício do servidor
        log_execution(status='Server Restarted', details="Servidor reiniciado. Buscando agendamentos ativos.")
        load_schedules()

# Inicialização do gerenciador de usuários
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
@login_required
def dashboard():
    status_filter = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = Execution.query.order_by(Execution.start_time.desc())

    if status_filter:
        query = query.filter(Execution.status == status_filter)
    if start_date:
        query = query.filter(Execution.start_time >= datetime.datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Execution.start_time <= datetime.datetime.strptime(end_date, '%Y-%m-%d'))

    executions = query.all()
    return render_template('dashboard.html', executions=executions)

@app.route('/get_executions', methods=['GET'])
@login_required
def get_executions():
    executions = Execution.query.order_by(Execution.start_time.desc()).all()
    return jsonify([{
        'id': execution.id,
        'status': execution.status,
        'start_time': execution.start_time.strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': execution.end_time.strftime('%Y-%m-%d %H:%M:%S') if execution.end_time else None
    } for execution in executions])

# Configuração do Favicon
@app.route('/favicon.svg')
def favicon():
    return app.send_static_file('favicon.svg')

# Iniciar o servidor
def start_server():
    # ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    # ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    # serve(app, host='127.0.0.1', port=5000, ssl_context=ssl_context)
    serve(app, host='127.0.0.1', port=5000)

if __name__ == '__main__':
    start_server()
