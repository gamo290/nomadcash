import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from modelli import Utente, Viaggio, Spesa, Amicizia
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'nomadcash_secret_key_super_secure')

@app.context_processor
def inject_user():
    utente = None
    if 'utente_email' in session:
        utente = {
            'nome': session.get('utente_nome'),
            'email': session.get('utente_email')
        }
    return dict(utente_loggato=utente)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'utente_email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def dashboard():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    
    # Dati per la Dashboard
    stats = utente_obj.get_stats()
    amici_frequenti = utente_obj.get_amici_frequenti(limit=4)
    viaggi_in_corso = utente_obj.get_miei_viaggi(filter_type='in_corso')
    viaggi_recenti = utente_obj.get_miei_viaggi(filter_type='recenti')
    
    # Selezioniamo il viaggio più imminente/in corso come "In evidenza"
    viaggio_evidenza = viaggi_in_corso[0] if viaggi_in_corso else None
    
    return render_template('dashboard.html', 
                           stats=stats, 
                           amici_frequenti=amici_frequenti, 
                           viaggi_in_corso=viaggi_in_corso,
                           viaggi_recenti=viaggi_recenti,
                           viaggio_evidenza=viaggio_evidenza)



@app.route('/login', methods=['GET', 'POST'])
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/viaggi')
@login_required
def viaggi():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    lista_viaggi = utente_obj.get_miei_viaggi(filter_type='tutti')
    return render_template('viaggi.html', viaggi=lista_viaggi, oggi=datetime.now().date())


@app.route('/viaggi/recenti')
@login_required
def viaggi_recenti():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    lista_viaggi = utente_obj.get_miei_viaggi(filter_type='recenti')
    # Calcoliamo un resoconto periodico veloce (es: totale speso negli ultimi viaggi)
    totale_storico = 0
    for v in lista_viaggi:
        b = Spesa.bilancio_utente_viaggio(v['id_viaggio'], session['utente_email'])
        totale_storico += b['pagato']
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
        
    bilancio = Spesa.divisione_equa(id_viaggio)
    
    # Calcolo riepilogo individuale
    from sqlalchemy import text
    from database import engine
    query_partecipanti = text("""
        SELECT u.nome, u.email 
        FROM utenti u
        JOIN partecipanti p ON u.email = p.email_utente
        WHERE p.id_viaggio = :id_v
    """)
    dettagli_partecipanti = []
    with engine.connect() as conn:
        pts = conn.execute(query_partecipanti, {"id_v": id_viaggio}).fetchall()
        for p in pts:
            b_utente = Spesa.bilancio_utente_viaggio(id_viaggio, p[1])
            dettagli_partecipanti.append({
                "nome": p[0],
                "email": p[1],
                "pagato": b_utente["pagato"],
                "netto": b_utente["netto"]
            })
            
    return render_template('dettaglio_viaggio.html', 
                           viaggio=viaggio, 
                           bilancio=bilancio, 
                           partecipanti_stats=dettagli_partecipanti,
                           oggi=datetime.now().date())


@app.route('/viaggi/crea', methods=['GET', 'POST'])
@login_required
def crea_viaggio():
    if request.method == 'POST':
        nome = request.form.get('nome')
        d_partenza = request.form.get('data_partenza')
        d_fine = request.form.get('data_fine')
        desc = request.form.get('descrizione')
        amici_invitati = request.form.getlist('invitati') # Lista di email inviate
        
        try:
            nuovo_v = Viaggio(None, nome, datetime.strptime(d_partenza, '%Y-%m-%d').date(), desc)
            nuovo_v.data_f = datetime.strptime(d_fine, '%Y-%m-%d').date()
            if nuovo_v.data_f < nuovo_v.data_p:
               flash("La data di fine scade prima della partenza.", "warning")
               return redirect(url_for('crea_viaggio'))
               
            nuovo_v.create(email_creatore=session['utente_email'])
            
            # TODO: inserisci invitati in backend
            from sqlalchemy import text
            from database import engine
            if amici_invitati:
                with engine.begin() as conn:
                    for em_amico in amici_invitati:
                        conn.execute(text("INSERT IGNORE INTO partecipanti (id_viaggio, email_utente) VALUES (:id_v, :em)"), 
                                     {"id_v": nuovo_v.id_viaggio, "em": em_amico})
                                     
            flash("Viaggio creato con successo!", "success")
            return redirect(url_for('viaggi'))
        except Exception as e:
            flash(str(e), "danger")
            
    # GET logic: Amici invitatibili
    from sqlalchemy import text
    from database import engine
    query_amici = text("""
        SELECT u.nome, u.email FROM utenti u
        JOIN amicizie a ON (u.email = a.richiedente OR u.email = a.ricevente)
        WHERE (a.richiedente = :me OR a.ricevente = :me) 
        AND u.email != :me AND a.stato = 'accettata'
    """)
    with engine.connect() as conn:
        amici = conn.execute(query_amici, {"me": session['utente_email']}).mappings().fetchall()
        
    return render_template('crea_viaggio.html', amici=amici)

@app.route('/viaggio/<int:id_viaggio>/modifica', methods=['GET', 'POST'])
@login_required
def modifica_viaggio(id_viaggio):
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    lista_viaggi = utente_obj.get_miei_viaggi()
    viaggio = next((v for v in lista_viaggi if v['id_viaggio'] == id_viaggio), None)
    
    if not viaggio:
        flash("Viaggio non trovato o non autorizzato.", "danger")
        return redirect(url_for('viaggi'))

    from sqlalchemy import text
    from database import engine

    if request.method == 'POST':
        nome = request.form.get('nome')
        d_partenza = request.form.get('data_partenza')
        d_fine = request.form.get('data_fine')
        desc = request.form.get('descrizione')
        amici_invitati = request.form.getlist('invitati') 
        
        try:
            viaggio_da_modificare = Viaggio(id_viaggio, nome, datetime.strptime(d_partenza, '%Y-%m-%d').date(), desc)
            viaggio_da_modificare.data_f = datetime.strptime(d_fine, '%Y-%m-%d').date()
            if viaggio_da_modificare.data_f < viaggio_da_modificare.data_p:
               flash("La data di fine scade prima della partenza.", "warning")
               return redirect(url_for('modifica_viaggio', id_viaggio=id_viaggio))
               
            viaggio_da_modificare.id_viaggio = id_viaggio
            viaggio_da_modificare.update()
            
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM partecipanti WHERE id_viaggio = :id_v AND email_utente != :me"), {"id_v": id_viaggio, "me": session['utente_email']})
                if amici_invitati:
                    for em_amico in amici_invitati:
                        conn.execute(text("INSERT IGNORE INTO partecipanti (id_viaggio, email_utente) VALUES (:id_v, :em)"), 
                                     {"id_v": id_viaggio, "em": em_amico})
                                     
            flash("Viaggio modificato con successo!", "success")
            return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))
        except Exception as e:
            flash(str(e), "danger")
            
    query_amici = text("""
        SELECT u.nome, u.email FROM utenti u
        JOIN amicizie a ON (u.email = a.richiedente OR u.email = a.ricevente)
        WHERE (a.richiedente = :me OR a.ricevente = :me) 
        AND u.email != :me AND a.stato = 'accettata'
    """)
    query_partecipanti = text("SELECT email_utente FROM partecipanti WHERE id_viaggio = :id_v")
    
    with engine.connect() as conn:
        amici = conn.execute(query_amici, {"me": session['utente_email']}).mappings().fetchall()
        partecipanti_attuali = [row[0] for row in conn.execute(query_partecipanti, {"id_v": id_viaggio}).fetchall()]
        
    return render_template('modifica_viaggio.html', viaggio=viaggio, amici=amici, partecipanti=partecipanti_attuali)


@app.route('/viaggio/<int:id_viaggio>/elimina', methods=['POST'])
@login_required
def elimina_viaggio(id_viaggio):
    viaggio_da_eliminare = Viaggio(id_viaggio, None, None, None)
    try:
        viaggio_da_eliminare.delete()
        flash("Viaggio eliminato.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('viaggi'))

@app.route('/spese', methods=['GET', 'POST'])
@login_required
def spese():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    miei_viaggi = utente_obj.get_miei_viaggi()
    
    if request.method == 'POST':
        id_viaggio = request.form.get('id_viaggio')
        email_pagatore = request.form.get('email_pagatore')
        importo = float(request.form.get('importo'))
        categoria = request.form.get('categoria')
        data_spesa = request.form.get('data_spesa')
        descrizione = request.form.get('descrizione')
        
        try:
            n_spesa = Spesa(id_viaggio, email_pagatore, descrizione, importo, categoria, data_spesa=data_spesa if data_spesa else datetime.now().date())
            n_spesa.create()
            flash("Spesa salvata!", "success")
        except Exception as e:
            flash(str(e), "danger")
        return redirect(url_for('spese'))
        
    id_v_selezionato = request.args.get('id_viaggio', type=int)
    partecipanti = []
    if id_v_selezionato:
        from sqlalchemy import text
        from database import engine
        with engine.connect() as conn:
            partecipanti = conn.execute(text("""
                SELECT u.email, u.nome FROM utenti u 
                JOIN partecipanti p ON u.email = p.email_utente 
                WHERE p.id_viaggio = :id_v
            """), {"id_v": id_v_selezionato}).mappings().fetchall()


    return render_template('spese.html', viaggi=miei_viaggi, partecipanti=partecipanti, id_v_selezionato=id_v_selezionato)


@app.route('/compagni', methods=['GET', 'POST'])
@login_required
def compagni():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    
    if request.method == 'POST':
        azione = request.form.get('azione')
        if azione == 'invia_richiesta':
            email_amico = request.form.get('email_amico')
            try:
                Amicizia.invia_richiesta(session['utente_email'], email_amico)
                flash("Richiesta inviata!", "success")
            except Exception as e:
                flash(str(e), "danger")
        elif azione == 'accetta':
            id_amicizia = request.form.get('id_amicizia')
            Amicizia.accetta_richiesta(id_amicizia)
            flash("Richiesta accettata!", "success")
        elif azione == 'rifiuta':
            id_amicizia = request.form.get('id_amicizia')
            Amicizia.rifiuta_richiesta(id_amicizia)
            flash("Richiesta rifiutata.", "info")
            
        return redirect(url_for('compagni'))

    richieste = Amicizia.get_richieste_ricevute(session['utente_email'])
    compagni_list = utente_obj.get_compagni()
    
    return render_template('compagni.html', richieste=richieste, compagni=compagni_list)

@app.route('/compagno/<email_amico>')
@login_required
def dettaglio_compagno(email_amico):
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    # Check if they are actually friends
    amici = utente_obj.get_compagni()
    amico = next((a for a in amici if a['email'] == email_amico), None)
    
    if not amico:
        flash("Compagno non trovato o non sei più suo amico.", "warning")
        return redirect(url_for('compagni'))
        
    viaggi_comune = utente_obj.get_viaggi_in_comune(email_amico)
    return render_template('dettaglio_compagno.html', amico=amico, viaggi=viaggi_comune)

@app.route('/compagni/rimuovi', methods=['POST'])
@login_required
def rimuovi_compagno():
    email_amico = request.form.get('email_amico')
    if email_amico:
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
                
                # Update session
                session['utente_nome'] = nuovo_nome
                
                if nuova_email != vecchia_email:
                    flash("Email aggiornata. Per favore effettua nuovamente il login.", "success")
                    return redirect(url_for('logout'))
                    
                flash("Profilo aggiornato!", "success")
                return redirect(url_for('impostazioni'))
            except Exception as e:
                flash(f"Errore: {e}", "danger")
                
        elif azione == 'elimina_account':
            try:
                utente_obj.delete_full()
                flash("Account eliminato definitivamente. Ci dispiace vederti andare via!", "info")
                return redirect(url_for('logout'))
            except Exception as e:
                flash(f"Impossibile eliminare l'account: {e}", "danger")
                
    return render_template('impostazioni.html', utente=utente_obj)

@app.route('/avatar/<email>')
def get_avatar(email):
    from database import engine
    from sqlalchemy import text
    query = text("SELECT avatar FROM utenti WHERE email = :e")
    with engine.connect() as conn:
        res = conn.execute(query, {"e": email}).fetchone()
        if res and res[0]:
            return Response(res[0], mimetype='image/jpeg')
        # Fallback se non c'è avatar: carichiamo una statica o generiamo placeholder
        return redirect(url_for('static', filename='default_avatar.png'))



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
