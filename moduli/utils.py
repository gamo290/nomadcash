from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'utente_email' not in session:
            # Nota: Il nome della rotta cambierà in 'auth.login' dopo la modularizzazione
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
