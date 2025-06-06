from sqlalchemy import create_engine
import logging
import sys
import os
from werkzeug.security import generate_password_hash

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.db_utils import DB_PATH, resource_path
from database.models import db, User  # Importar os modelos do models.py

LOG_FILE = resource_path("logs/controlador.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configuração do SQLAlchemy
engine = create_engine(f"sqlite:///{DB_PATH}")

# Inserir um usuário padrão no banco de dados
def initialize_default_user():
    """Criar um usuário padrão no banco de dados."""
    logging.info("Inicializando usuário padrão...")
    default_user = User(
        username="admin",
        password_hash=generate_password_hash("admin123"),  # Senha padrão
        is_admin=True
    )
    try:
        with db.session.begin():
            db.session.add(default_user)
        logging.info("Usuário padrão 'admin' criado com sucesso. A senha padrão é 'admin123'.")
        logging.info("Por favor, altere a senha após o primeiro login.")
    except Exception as e:
        logging.error(f"Erro ao criar o usuário padrão: {e}")

# Criar o diretório do banco de dados, se não existir
def makedir():
    """Criar o diretório do banco de dados, se não existir."""
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
    logging.info(f"Diretório do banco de dados criado em: {os.path.dirname(DB_PATH)}")

# Criar o banco de dados e as tabelas
if __name__ == "__main__":
    makedir()
    db.create_all()  # Usar os modelos do models.py para criar as tabelas
    initialize_default_user()
    logging.info(f"Banco de dados criado em: {DB_PATH}")