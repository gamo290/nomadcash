import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from modelli import Utente, Viaggio, Spesa, Amicizia, Tappa
from datetime import datetime
from sqlalchemy import text
from database import engine

# Import dei moduli
from moduli.utils import login_required
from moduli.auth import auth_bp
from moduli.setup_viaggio import setup_viaggio_bp
from moduli.chat_spese import chat_spese_bp

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nomadcash_secret_key_super_secure')

# Registrazione Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(setup_viaggio_bp)
app.register_blueprint(chat_spese_bp)

@app.context_processor
def inject_user():
    utente = None
    if 'utente_email' in session:
        utente = {
            'nome': session.get('utente_nome'),
            'email': session.get('utente_email')
        }
    return dict(utente_loggato=utente)

@app.route('/')
@login_required
def dashboard():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    stats = utente_obj.get_stats()
    amici_frequenti = utente_obj.get_amici_frequenti(limit=4)
    viaggi_in_corso = utente_obj.get_miei_viaggi(filter_type='in_corso')
    viaggi_recenti = utente_obj.get_miei_viaggi(filter_type='recenti')
    viaggio_evidenza = viaggi_in_corso[0] if viaggi_in_corso else None
    
    return render_template('dashboard.html', 
                           stats=stats, 
                           amici_frequenti=amici_frequenti, 
                           viaggi_in_corso=viaggi_in_corso,
                           viaggi_recenti=viaggi_recenti,
                           viaggio_evidenza=viaggio_evidenza)

@app.route('/viaggi')
@login_required
def viaggi():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    lista_viaggi = utente_obj.get_miei_viaggi(filter_type='tutti')
    return render_template('viaggi.html', viaggi=lista_viaggi, oggi=datetime.now().date())

@app.route('/viaggi_recenti')
@login_required
def viaggi_recenti():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    lista_viaggi = utente_obj.get_viaggi_conclusi()
    totale_storico = 0
    for v in lista_viaggi:
        id_v = v['id_viaggio']
        query_speso = text("SELECT SUM(importo) FROM spese WHERE id_viaggio = :id AND email_utente = :em")
        with engine.connect() as conn:
            speso = conn.execute(query_speso, {"id": id_v, "em": session['utente_email']}).scalar() or 0
            totale_storico += speso
    return render_template('viaggi_recenti.html', viaggi=lista_viaggi, totale_storico=totale_storico)

@app.route('/viaggio/<int:id_viaggio>')
@login_required
def dettaglio_viaggio(id_viaggio):
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    lista_viaggi = utente_obj.get_miei_viaggi()
    viaggio = next((v for v in lista_viaggi if v['id_viaggio'] == id_viaggio), None)
    if not viaggio:
        flash("Viaggio non trovato o non autorizzato.", "danger")
        return redirect(url_for('viaggi'))
    
    risultato_bilancio = Spesa.get_bilancio_completo(id_viaggio)
    if isinstance(risultato_bilancio, str):
        bilancio_info = {"totale_da_saldare": 0, "quota_a_testa": 0, "tassa_individuale": 0}
        stats_partecipanti = []
    else:
        bilancio_info = risultato_bilancio["info_generali"]
        stats_partecipanti = risultato_bilancio["partecipanti_bilancio"]
    
    if not stats_partecipanti:
        query_admin = text("SELECT ruolo_admin FROM partecipanti WHERE id_viaggio = :id AND email_utente = :em")
        with engine.connect() as conn:
            is_admin = conn.execute(query_admin, {"id": id_viaggio, "em": session['utente_email']}).scalar() or False
    else:
        is_admin = any(p['email'] == session['utente_email'] and p['ruolo_admin'] for p in stats_partecipanti)
            
    tappe_viaggio = Tappa.get_tappe_by_viaggio(id_viaggio)
    cronologia = Spesa.get_spese_per_viaggio(id_viaggio)
    
    # Inseriamo la tassa NomadCash nella cronologia se presente
    if not isinstance(risultato_bilancio, str) and risultato_bilancio["info_generali"]["tassa_totale"] > 0:
        tassa_entry = {
            'nome_utente': 'NomadCash',
            'email_utente': 'sistema@nomadcash.com',
            'data_spesa': 'Sistema',
            'testo_messaggio': 'Commissione servizio NomadCash (calcolata per partecipante)',
            'importo': risultato_bilancio["info_generali"]["tassa_totale"],
            'categoria': 'Sistema',
            'pagata': True,
            'id_spesa': 0
        }
        cronologia.insert(0, tassa_entry)

    return render_template('dettaglio_viaggio.html', 
                           viaggio=viaggio, 
                           bilancio=bilancio_info, 
                           partecipanti_stats=stats_partecipanti,
                           oggi=datetime.now().date(),
                           is_admin=is_admin,
                           tappe=tappe_viaggio,
                           spese_cronologia=cronologia)

@app.route('/compagni')
@login_required
def compagni():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    amici = utente_obj.get_tutti_amici()
    richieste = utente_obj.get_richieste_amicizia()
    return render_template('compagni.html', amici=amici, richieste=richieste)

@app.route('/amico/<email_amico>')
@login_required
def dettaglio_compagno(email_amico):
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    info_amico = Utente.get_by_email(email_amico)
    if not info_amico:
        flash("Compagno non trovato.", "warning")
        return redirect(url_for('compagni'))
    viaggi_comune = utente_obj.get_viaggi_in_comune(email_amico)
    return render_template('dettaglio_compagno.html', amico=info_amico, viaggi=viaggi_comune)

@app.route('/accetta_amicizia/<email_richiedente>')
@login_required
def accetta_amicizia(email_richiedente):
    Amicizia.accetta(email_richiedente, session['utente_email'])
    flash(f"Richiesta di amicizia accettata!", "success")
    return redirect(url_for('compagni'))

@app.route('/richiedi_amicizia', methods=['POST'])
@login_required
def richiedi_amicizia():
    email_dest = request.form.get('email')
    try:
        Amicizia.invia_richiesta(session['utente_email'], email_dest)
        flash(f"Richiesta inviata a {email_dest}!", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('compagni'))

@app.route('/rimuovi_amico/<email_amico>', methods=['POST'])
@login_required
def rimuovi_amico(email_amico):
    Amicizia.rimuovi(session['utente_email'], email_amico)
    flash("Compagno rimosso correttamente.", "success")
    return redirect(url_for('compagni'))

@app.route('/impostazioni', methods=['GET', 'POST'])
@login_required
def impostazioni():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    if request.method == 'POST':
        azione = request.form.get('azione')
        if azione == 'aggiorna':
            nuovo_nome = request.form.get('nome')
            nuova_email = request.form.get('email')
            avatar_file = request.files.get('avatar')
            nuovo_avatar_bytes = None
            if avatar_file and avatar_file.filename != '':
                nuovo_avatar_bytes = avatar_file.read()
            try:
                vecchia_email = utente_obj.email
                utente_obj.nome = nuovo_nome
                utente_obj.update_full(nuova_email, nuovo_avatar=nuovo_avatar_bytes)
                session['utente_nome'] = nuovo_nome
                if nuova_email != vecchia_email:
                    flash("Email aggiornata. Per favore effettua nuovamente il login.", "success")
                    return redirect(url_for('auth.logout'))
                flash("Profilo aggiornato!", "success")
                return redirect(url_for('impostazioni'))
            except Exception as e:
                flash(f"Errore: {e}", "danger")
        elif azione == 'elimina_account':
            try:
                utente_obj.delete_full()
                flash("Account eliminato definitivamente!", "info")
                return redirect(url_for('auth.logout'))
            except Exception as e:
                flash(f"Impossibile eliminare l'account: {e}", "danger")
    return render_template('impostazioni.html', utente=utente_obj)

@app.route('/api/viaggi_comune/<email_amico>')
@login_required
def api_viaggi_comune(email_amico):
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    viaggi = utente_obj.get_viaggi_in_comune(email_amico)
    return {'viaggi': viaggi}

@app.route('/api/bilancio_viaggio/<int:id_viaggio>')
@login_required
def api_bilancio_viaggio(id_viaggio):
    b = Spesa.bilancio_utente_viaggio(id_viaggio, session['utente_email'])
    return b

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(debug=debug_mode, use_reloader=debug_mode, port=5000)
