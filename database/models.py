import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Execution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id', ondelete='SET NULL'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True)  # Tornar opcional
    start_time = db.Column(db.DateTime, default=datetime.datetime.now)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False)
    records_processed = db.Column(db.Integer, default=0)
    details = db.Column(db.Text)

class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)  # Nome do agendamento
    origin_id = db.Column(db.Integer, db.ForeignKey('origins.id', ondelete='CASCADE'), nullable=False)  # Origem vinculada
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id', ondelete='CASCADE'), nullable=False)  # Script vinculado
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False)  # Destino vinculado
    cron_expression = db.Column(db.String, nullable=False)  # Expressão CRON para o agendamento
    active = db.Column(db.Boolean, default=True)  # Status do agendamento (ativo/inativo)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)  # Data de criação
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)  # Data de atualização

    # Relacionamentos
    origin = db.relationship('Origin', backref='schedules')  # Relacionamento com Origem
    script = db.relationship('Script', backref='schedules')  # Relacionamento com Script
    destination = db.relationship('Destination', backref='schedules')  # Relacionamento com Destino

    @staticmethod
    def has_conflict(origin_id, script_id, destination_id, cron_expression, schedule_id=None):
        """Verificar se já existe um agendamento com os mesmos parâmetros, ignorando o próprio ao editar."""
        query = Schedule.query.filter(
            Schedule.active == True,
            Schedule.origin_id == origin_id,
            Schedule.script_id == script_id,
            Schedule.destination_id == destination_id,
            Schedule.cron_expression == cron_expression
        )
        if schedule_id:
            query = query.filter(Schedule.id != schedule_id)
        return query.first() is not None

class Script(db.Model):
    __tablename__ = 'scripts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)  # Nome do script
    content = db.Column(db.Text, nullable=False)  # Conteúdo do script
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)  # Data de criação
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)  # Data de atualização

class ScriptParameter(db.Model):
    __tablename__ = 'script_parameters'
    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String, nullable=False)
    value = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # Relacionamento com Script
    script = db.relationship('Script', backref='parameters', cascade='all, delete-orphan', single_parent=True)

class Destination(db.Model):
    __tablename__ = 'destinations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, nullable=True)
    keyfile = db.Column(db.String, nullable=True)  # Caminho do arquivo JSON
    project_id = db.Column(db.String, nullable=True)  # ID do projeto BigQuery
    dataset_id = db.Column(db.String, nullable=True)  # ID do dataset BigQuery
    table_id = db.Column(db.String, nullable=True)  # ID da tabela BigQuery
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

class Origin(db.Model):
    __tablename__ = 'origins'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)  # Nome da origem
    description = db.Column(db.Text, nullable=True)  # Descrição da origem
    dsn = db.Column(db.String, nullable=False)  # Caminho completo para o banco de dados
    user = db.Column(db.String, nullable=True)  # Usuário para autenticação
    password = db.Column(db.String, nullable=True)  # Senha para autenticação
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)  # Data de criação
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)  # Data de atualização

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    origin_id = db.Column(db.Integer, db.ForeignKey('origins.id', ondelete='CASCADE'), nullable=False)
    script_id = db.Column(db.Integer, db.ForeignKey('scripts.id', ondelete='CASCADE'), nullable=False)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # Relacionamentos
    user = db.relationship('User', backref='permissions')
    origin = db.relationship('Origin', backref='permissions')
    script = db.relationship('Script', backref='permissions')
    destination = db.relationship('Destination', backref='permissions')