from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from modelli import Utente
from database import engine
from sqlalchemy import text

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'utente_email' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'login':
            email = request.form.get('email')
            password = request.form.get('password')
            utente = Utente.login(email, password)
            if utente:
                session['utente_email'] = utente['email']
                session['utente_nome'] = utente['nome']
                return redirect(url_for('dashboard'))
            else:
                flash("Email o password non validi.", "danger")
                
        elif action == 'register':
            nome = request.form.get('nome')
            email = request.form.get('email')
            password = request.form.get('password')
            
            avatar_file = request.files.get('avatar')
            avatar_bytes = None
            if avatar_file and avatar_file.filename != '':
                avatar_bytes = avatar_file.read()
            
            try:
                nuovo_utente = Utente(nome=nome, email=email, avatar=avatar_bytes, password=password, admin=False)
                nuovo_utente.create()
                flash("Registrazione completata. Ora puoi accedere.", "success")
            except ValueError as e:
                flash(str(e), "danger")
                
    return render_template('auth.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/avatar/<email>')
def get_avatar(email):
    query = text("SELECT avatar FROM utenti WHERE email = :e")
    with engine.connect() as conn:
        res = conn.execute(query, {"e": email}).fetchone()
        if res and res[0]:
            return Response(res[0], mimetype='image/jpeg')
        # Fallback se non c'è avatar
        return redirect(url_for('static', filename='default_avatar.png'))