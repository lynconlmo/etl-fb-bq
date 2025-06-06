from flask import jsonify, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from database.models import User
from . import auth_bp

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos!', 'danger')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'success')
    return redirect(url_for('auth.login'))

def validate_user_input(username, password):
    if not username or not password:
        return jsonify({'error': 'Usuário e senha são obrigatórios!'}), 400