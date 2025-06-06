from flask import Blueprint, request, jsonify
from database.models import db, Permission
import logging

permissions_bp = Blueprint('permissions', __name__)

@permissions_bp.route('/permissions', methods=['POST'])
def add_permission():
    """Adicionar uma permissão para um usuário."""
    data = request.json
    user_id = data.get('user_id')
    origin_id = data.get('origin_id')
    script_id = data.get('script_id')
    destination_id = data.get('destination_id')

    permission = Permission(
        user_id=user_id,
        origin_id=origin_id,
        script_id=script_id,
        destination_id=destination_id
    )
    db.session.add(permission)
    db.session.commit()
    logging.info(f"Permissão adicionada: User {user_id}, Origin {origin_id}, Script {script_id}, Destination {destination_id}")
    return jsonify({"message": "Permissão adicionada com sucesso!"}), 201

@permissions_bp.route('/<int:user_id>', methods=['GET'])
def get_user_permissions(user_id):
    """Listar todas as permissões de um usuário."""
    permissions = Permission.query.filter_by(user_id=user_id).all()
    return jsonify([{
        "origin_id": p.origin_id,
        "script_id": p.script_id,
        "destination_id": p.destination_id
    } for p in permissions])

@permissions_bp.route('/get_allowed_origins/<int:user_id>', methods=['GET'])
def get_allowed_origins(user_id):
    from database.db_utils import get_user_allowed_origins
    return jsonify(get_user_allowed_origins(user_id))
    