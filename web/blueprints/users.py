from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database.models import db, User

users_bp = Blueprint('users', __name__)

def is_admin():
    if not current_user.is_admin:
        return jsonify({'error': 'Acesso negado!'}), 403

@users_bp.route('/manage_users')
@login_required
def manage_users():
    is_admin()
    users = User.query.all()
    headers = ['ID', 'Usuário', 'Administrador', 'Ações']
    return render_template('manage_users.html', users=users, headers=headers)

@users_bp.route('/create_user', methods=['POST'])
@login_required
def create_user():
    is_admin()
    username = request.form.get('username')
    password = request.form.get('password')
    is_admin_flag = request.form.get('is_admin') == 'true'

    if not username or not password:
        return jsonify({'error': 'Usuário e senha são obrigatórios!'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Usuário já existe!'}), 400

    new_user = User(username=username, is_admin=is_admin_flag)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Usuário criado com sucesso!'})

@users_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    is_admin()
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return jsonify({'error': 'Você não pode excluir a si mesmo!'}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Usuário excluído com sucesso!'})

@users_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Permitir que o usuário altere sua própria senha."""
    new_password = request.form.get('new_password')

    if not new_password:
        flash('Nova senha é obrigatória!', 'danger')
        return redirect(url_for('users.change_password_page'))

    current_user.set_password(new_password)
    db.session.commit()
    flash('Senha alterada com sucesso!', 'success')
    return redirect(url_for('dashboard'))

@users_bp.route('/change_password_page', methods=['GET'])
@login_required
def change_password_page():
    """Exibir a página de troca de senha."""
    return render_template('change_password.html')

@users_bp.route('/change_user_password/<int:user_id>', methods=['POST'])
@login_required
def change_user_password(user_id):
    """Permitir que administradores alterem a senha de outros usuários."""
    is_admin()
    new_password = request.form.get('new_password')

    if not new_password:
        flash('Nova senha é obrigatória!', 'danger')
        return redirect(url_for('users.manage_users'))

    user = User.query.get_or_404(user_id)
    user.set_password(new_password)
    db.session.commit()
    flash(f'Senha do usuário {user.username} alterada com sucesso!', 'success')
    return redirect(url_for('users.manage_users'))