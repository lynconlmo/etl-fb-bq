import os
import sys
import logging
import customtkinter as ctk
from database.db_utils import DB_PATH, resource_path
# sys.path.append(os.path.abspath(os.path.dirname(__file__)))

os.environ['PATH'] = os.path.abspath("libs") + ";" + os.environ['PATH']

LOG_FILE = resource_path("logs/controlador.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

def check_and_create_database():
    """Verificar se o banco de dados existe e criá-lo se necessário."""
    if not os.path.exists(DB_PATH):
        logging.info(f"Banco de dados não encontrado em: {DB_PATH}")
        logging.info("Criando banco de dados...")
        try:
            from database.create_database import makedir, initialize_default_user
            # Criar o diretório do banco de dados, se não existir
            makedir()
            # Importar o app Flask e os modelos após garantir que o diretório existe
            from web.monitor import app
            from database.models import db
            # Criar o banco de dados e as tabelas
            with app.app_context():
                db.create_all()
                initialize_default_user()
            logging.info(f"Banco de dados criado em: {DB_PATH}")
        except Exception as e:
            logging.error(f"Erro ao criar o banco de dados: {e}")
            sys.exit(1)

def main():
    """Iniciar a interface gráfica com Tkinter."""
    # Verificar e criar o banco de dados, se necessário
    check_and_create_database()
    # Inicializa os agendamentos
    from web.monitor import initialize_schedules
    initialize_schedules()

    # Importar o controlador apenas após garantir que o banco de dados foi criado
    from server.controlador import MonitorControllerApp

    # Iniciar a interface gráfica
    root = ctk.CTk()
    gui = MonitorControllerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()