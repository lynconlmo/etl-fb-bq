import os
import sys
from sqlalchemy import create_engine, text

def resource_path(relative_path):
    """Obter o caminho absoluto do recurso, compatível com PyInstaller."""
    try:
        base_path = sys._MEIPASS  # Diretório temporário usado pelo PyInstaller
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Caminho para o banco de dados SQLite
DB_PATH = resource_path("database/instance/etl_monitor.db")

# Criar a conexão com o banco de dados
engine = create_engine(f"sqlite:///{DB_PATH}")

# Métodos para gerenciar scripts
def get_all_scripts():
    """Recuperar todos os scripts do banco de dados."""
    with engine.connect() as connection:
        query = text("SELECT id, name, content FROM scripts")
        result = connection.execute(query).mappings()
        return [(row["id"], row["name"], row["content"]) for row in result]

def get_script_by_id(script_id):
    """Recuperar um script pelo ID."""
    with engine.connect() as connection:
        query = text("SELECT id, name, content FROM scripts WHERE id = :id")
        result = connection.execute(query, {"id": script_id}).fetchone()
        return result

def add_script(name, content):
    """Adicionar um novo script ao banco de dados."""
    with engine.begin() as connection:
        query = text("""
            INSERT INTO scripts (name, content)
            VALUES (:name, :content)
        """)
        connection.execute(query, {"name": name, "content": content})

def edit_script(script_id):
    """Recuperar os detalhes de um script para edição."""
    with engine.connect() as connection:
        query = text("""
            SELECT id, name, content
            FROM scripts
            WHERE id = :id
        """)
        result = connection.execute(query, {"id": script_id}).mappings().fetchone()
        if result:
            return {
                "id": result["id"],
                "name": result["name"],
                "content": result["content"]
            }
        else:
            raise ValueError(f"Script com ID {script_id} não encontrado.")

def update_script(script_id, name, content):
    """Atualizar um script existente."""
    with engine.begin() as connection:
        query = text("""
            UPDATE scripts
            SET name = :name, content = :content
            WHERE id = :id
        """)
        connection.execute(query, {"id": script_id, "name": name, "content": content})

def delete_script(script_id):
    """Excluir um script do banco de dados."""
    with engine.begin() as connection:
        query = text("DELETE FROM scripts WHERE id = :id")
        connection.execute(query, {"id": script_id})
        
def get_all_destinations():
    """Recuperar todos os destinos do banco de dados."""
    with engine.connect() as connection:
        query = text("SELECT id, name FROM destinations")
        result = connection.execute(query).mappings()
        return [(row["id"], row["name"]) for row in result]

def add_destination(name, description, project_id, dataset_id, table_id, keyfile):
    """Adicionar um novo destino ao banco de dados."""
    with engine.begin() as connection:
        query = text("""
            INSERT INTO destinations (name, description, project_id, dataset_id, table_id, keyfile)
            VALUES (:name, :description, :project_id, :dataset_id, :table_id, :keyfile)
        """)
        connection.execute(query, {"name": name, "description": description, "project_id": project_id, "dataset_id": dataset_id, "table_id": table_id, "keyfile": keyfile})

def update_destination(dest_id, name, description, project_id, dataset_id, table_id, keyfile):
    """Atualizar um destino existente."""
    with engine.begin() as connection:
        query = text("""
            UPDATE destinations
            SET name = :name, description = :description, project_id = :project_id, dataset_id = :dataset_id, table_id = :table_id, keyfile = :keyfile
            WHERE id = :id
        """)
        connection.execute(query, {"id": dest_id, "name": name, "description": description, "project_id": project_id, "dataset_id": dataset_id, "table_id": table_id, "keyfile": keyfile})

def get_destination_by_id(dest_id):
    """Recuperar um destino pelo ID."""
    with engine.connect() as connection:
        query = text("SELECT id, name, description, project_id, dataset_id, table_id, keyfile FROM destinations WHERE id = :id")
        return connection.execute(query, {"id": dest_id}).fetchone()

def delete_destination(dest_id):
    """Excluir um destino do banco de dados."""
    with engine.begin() as connection:
        query = text("DELETE FROM destinations WHERE id = :id")
        connection.execute(query, {"id": dest_id})

def get_destinations_by_user(user_id):
    """Retorna os destinos vinculados a um usuário."""
    query = text("""
        SELECT destination_id 
        FROM user_destinations 
        WHERE user_id = :user_id
    """)
    with engine.connect() as connection:
        result = connection.execute(query, {"user_id": user_id})
        return [row["destination_id"] for row in result]

def get_all_users():
    """Retorna todos os usuários cadastrados."""
    query = text("""
        SELECT id, username 
        FROM user
    """)
    with engine.connect() as connection:
        result = connection.execute(query).mappings()
        return [(row["id"], row["username"]) for row in result]

def update_user_destinations(user_id, destination_ids):
    """Atualiza os destinos vinculados a um usuário."""
    with engine.begin() as connection:
        # Remover os destinos existentes
        delete_query = text("""
            DELETE FROM user_destinations 
            WHERE user_id = :user_id
        """)
        connection.execute(delete_query, {"user_id": user_id})

        # Inserir os novos destinos
        insert_query = text("""
            INSERT INTO user_destinations (user_id, destination_id) 
            VALUES (:user_id, :destination_id)
        """)
        for destination_id in destination_ids:
            connection.execute(insert_query, {"user_id": user_id, "destination_id": destination_id})

def add_origin(name, dsn, user, password):
    """Adicionar uma nova origem ao banco de dados."""
    with engine.begin() as connection:
        query = text("""
            INSERT INTO origins (name, dsn, user, password)
            VALUES (:name, :dsn, :user, :password)
        """)
        connection.execute(query, {"name": name, "dsn": dsn, "user": user, "password": password})

def update_origin(origin_id, name, dsn, user, password):
    """Atualizar uma origem existente."""
    with engine.begin() as connection:
        query = text("""
            UPDATE origins
            SET name = :name, dsn = :dsn, user = :user, password = :password
            WHERE id = :id
        """)
        connection.execute(query, {"id": origin_id, "name": name, "dsn": dsn, "user": user, "password": password})

def edit_origin(origin_id):
    """Recuperar os detalhes de uma origem para edição."""
    with engine.connect() as connection:
        query = text("""
            SELECT id, name, dsn, user, password
            FROM origins
            WHERE id = :id
        """)
        result = connection.execute(query, {"id": origin_id}).mappings().fetchone()
        if result:
            return {
                "id": result["id"],
                "name": result["name"],
                "dsn": result["dsn"],
                "user": result["user"],
                "password": result["password"]
            }
        else:
            raise ValueError(f"Origem com ID {origin_id} não encontrada.")

def delete_origin(origin_id):
    """Excluir uma origem do banco de dados."""
    with engine.begin() as connection:
        query = text("DELETE FROM origins WHERE id = :id")
        connection.execute(query, {"id": origin_id})

def get_all_origins():
    """Recuperar todas as origens do banco de dados."""
    with engine.connect() as connection:
        query = text("SELECT id, name FROM origins")
        result = connection.execute(query).mappings()
        return [(row["id"], row["name"]) for row in result]

def add_script_parameter(script_id, name, value):
    """Adicionar um novo parâmetro ao script."""
    with engine.begin() as connection:
        query = text("""
            INSERT INTO script_parameters (script_id, name, value)
            VALUES (:script_id, :name, :value)
        """)
        connection.execute(query, {"script_id": script_id, "name": name, "value": value})

def update_script_parameter(parameter_id, name, value):
    """Atualizar um parâmetro de script existente."""
    with engine.begin() as connection:
        query = text("""
            UPDATE script_parameters
            SET name = :name, value = :value
            WHERE id = :id
        """)
        connection.execute(query, {"id": parameter_id, "name": name, "value": value})

def edit_script_parameter(parameter_id):
    """Recuperar os detalhes de um parâmetro de script para edição."""
    with engine.connect() as connection:
        query = text("""
            SELECT id, script_id, name, value
            FROM script_parameters
            WHERE id = :id
        """)
        result = connection.execute(query, {"id": parameter_id}).mappings().fetchone()
        if result:
            return {
                "id": result["id"],
                "script_id": result["script_id"],
                "name": result["name"],
                "value": result["value"]
            }
        else:
            raise ValueError(f"Parâmetro com ID {parameter_id} não encontrado.")

def delete_script_parameter(parameter_id):
    """Excluir um parâmetro de script do banco de dados."""
    with engine.begin() as connection:
        query = text("DELETE FROM script_parameters WHERE id = :id")
        connection.execute(query, {"id": parameter_id})

def get_script_parameters(script_id):
    """Recuperar todos os parâmetros de um script."""
    with engine.connect() as connection:
        query = text("SELECT id, name, value FROM script_parameters WHERE script_id = :script_id")
        return connection.execute(query, {"script_id": script_id}).fetchall()

def add_permission(user_id, origin_id, script_id, destination_id):
    """Adicionar uma nova permissão ao banco de dados."""
    with engine.begin() as connection:
        query = text("""
            INSERT INTO permissions (user_id, origin_id, script_id, destination_id)
            VALUES (:user_id, :origin_id, :script_id, :destination_id)
        """)
        connection.execute(query, {
            "user_id": user_id,
            "origin_id": origin_id,
            "script_id": script_id,
            "destination_id": destination_id
        })

def update_permission(permission_id, user_id, origin_id, script_id, destination_id):
    """Atualizar uma permissão existente."""
    with engine.begin() as connection:
        query = text("""
            UPDATE permissions
            SET user_id = :user_id, origin_id = :origin_id, script_id = :script_id, destination_id = :destination_id
            WHERE id = :id
        """)
        connection.execute(query, {
            "id": permission_id,
            "user_id": user_id,
            "origin_id": origin_id,
            "script_id": script_id,
            "destination_id": destination_id
        })

def delete_permission(permission_id):
    """Excluir uma permissão do banco de dados."""
    with engine.begin() as connection:
        query = text("DELETE FROM permissions WHERE id = :id")
        connection.execute(query, {"id": permission_id})

def get_all_permissions():
    """Recuperar todas as permissões do banco de dados."""
    with engine.connect() as connection:
        query = text("""
            SELECT id, user_id, origin_id, script_id, destination_id
            FROM permissions
        """)
        result = connection.execute(query).mappings()
        return [row for row in result]

def has_permission(user_id, origin_id, script_id, destination_id):
    """Verificar se uma permissão existe."""
    with engine.connect() as connection:
        query = text("""
            SELECT 1
            FROM permissions
            WHERE user_id = :user_id AND origin_id = :origin_id AND script_id = :script_id AND destination_id = :destination_id
        """)
        result = connection.execute(query, {
            "user_id": user_id,
            "origin_id": origin_id,
            "script_id": script_id,
            "destination_id": destination_id
        }).fetchone()
        return result is not None

def get_user_allowed_origins(user_id):
    with engine.connect() as connection:
        query = text("""
            SELECT DISTINCT o.id, o.name
            FROM origins o
            JOIN permissions p ON o.id = p.origin_id
            WHERE p.user_id = :user_id
        """)
        result = connection.execute(query, {"user_id": user_id}).mappings().fetchall()
        return [{"id": row["id"], "name": row["name"]} for row in result]

def get_user_allowed_destinations(user_id):
    with engine.connect() as connection:
        query = text("""
            SELECT DISTINCT d.id, d.name
            FROM destinations d
            JOIN permissions p ON d.id = p.destination_id
            WHERE p.user_id = :user_id
        """)
        result = connection.execute(query, {"user_id": user_id}).mappings().fetchall()
        return [{"id": row["id"], "name": row["name"]} for row in result]

def get_user_allowed_scripts(user_id):
    with engine.connect() as connection:
        query = text("""
            SELECT DISTINCT s.id, s.name
            FROM scripts s
            JOIN permissions p ON s.id = p.script_id
            WHERE p.user_id = :user_id
        """)
        result = connection.execute(query, {"user_id": user_id}).mappings().fetchall()
        return [{"id": row["id"], "name": row["name"]} for row in result]
    
def get_user_allowed_scripts_for_origin(user_id, origin_id):
    with engine.connect() as connection:
        query = text("""
            SELECT DISTINCT s.id, s.name
            FROM scripts s
            JOIN permissions p ON s.id = p.script_id
            WHERE p.user_id = :user_id AND p.origin_id = :origin_id
        """)
        result = connection.execute(query, {"user_id": user_id, "origin_id": origin_id}).mappings().fetchall()
        return [{"id": row["id"], "name": row["name"]} for row in result]
    
def get_user_allowed_destinations_for_origin_script(user_id, origin_id, script_id):
    with engine.connect() as connection:
        query = text("""
            SELECT DISTINCT d.id, d.name
            FROM destinations d
            JOIN permissions p ON d.id = p.destination_id
            WHERE p.user_id = :user_id AND p.origin_id = :origin_id AND p.script_id = :script_id
        """)
        result = connection.execute(query, {"user_id": user_id, "origin_id": origin_id, "script_id": script_id}).mappings().fetchall()
        return [{"id": row["id"], "name": row["name"]} for row in result]