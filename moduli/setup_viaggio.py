from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from modelli import Viaggio, Tappa, Utente
from database import engine
from sqlalchemy import text
from datetime import datetime
from moduli.utils import login_required

setup_viaggio_bp = Blueprint('setup_viaggio', __name__)

@setup_viaggio_bp.route('/viaggi/crea', methods=['GET', 'POST'])
@login_required
def crea_viaggio():
    if request.method == 'POST':
        nome = request.form.get('nome')
        d_partenza = request.form.get('data_partenza')
        d_fine = request.form.get('data_fine')
        desc = request.form.get('descrizione')
        dest = request.form.get('destinazione_nome', 'Sconosciuta')
        try:
            lat = float(request.form.get('lat', 0.0) or 0.0)
            lng = float(request.form.get('lng', 0.0) or 0.0)
        except ValueError:
            lat, lng = 0.0, 0.0
            
        amici_invitati = request.form.getlist('invitati') 
        
        try:
            nuovo_v = Viaggio(None, nome, datetime.strptime(d_partenza, '%Y-%m-%d').date(), desc, destinazione_nome=dest, lat=lat, lng=lng)
            nuovo_v.data_f = datetime.strptime(d_fine, '%Y-%m-%d').date()
            if nuovo_v.data_f < nuovo_v.data_p:
               flash("La data di fine scade prima della partenza.", "warning")
               return redirect(url_for('setup_viaggio.crea_viaggio'))
               
            nuovo_v.create(email_creatore=session['utente_email'])
            
            if amici_invitati:
                with engine.begin() as conn:
                    for em_amico in amici_invitati:
                        conn.execute(text("INSERT IGNORE INTO partecipanti (id_viaggio, email_utente) VALUES (:id_v, :em)"), 
                                     {"id_v": nuovo_v.id_viaggio, "em": em_amico})
                                     
            flash("Viaggio creato con successo!", "success")
            return redirect(url_for('viaggi'))
        except Exception as e:
            flash(str(e), "danger")
            
    query_amici = text("""
        SELECT u.nome, u.email FROM utenti u
        JOIN amicizie a ON (u.email = a.richiedente OR u.email = a.ricevente)
        WHERE (a.richiedente = :me OR a.ricevente = :me) 
        AND u.email != :me AND a.stato = 'accettata'
    """)
    with engine.connect() as conn:
        amici = conn.execute(query_amici, {"me": session['utente_email']}).mappings().fetchall()
        
    return render_template('set_up_viaggio.html', amici=amici)

@setup_viaggio_bp.route('/viaggio/<int:id_viaggio>/modifica', methods=['GET', 'POST'])
@login_required
def modifica_viaggio(id_viaggio):
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    lista_viaggi = utente_obj.get_miei_viaggi()
    viaggio = next((v for v in lista_viaggi if v['id_viaggio'] == id_viaggio), None)
    
    if not viaggio:
        flash("Viaggio non trovato o non autorizzato.", "danger")
        return redirect(url_for('viaggi'))

    with engine.connect() as conn:
        is_admin = conn.execute(text("SELECT ruolo_admin FROM partecipanti WHERE id_viaggio = :id_v AND email_utente = :me"), {"id_v": id_viaggio, "me": session['utente_email']}).scalar()

    if not is_admin:
        flash("Non hai i permessi di amministratore per modificare questo viaggio.", "danger")
        return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

    if request.method == 'POST':
        nome = request.form.get('nome')
        d_partenza = request.form.get('data_partenza')
        d_fine = request.form.get('data_fine')
        desc = request.form.get('descrizione')
        dest = request.form.get('destinazione_nome', 'Sconosciuta')
        try:
            lat = float(request.form.get('lat', 0.0) or 0.0)
            lng = float(request.form.get('lng', 0.0) or 0.0)
        except ValueError:
            lat, lng = 0.0, 0.0
        
        try:
            viaggio_da_modificare = Viaggio(id_viaggio, nome, datetime.strptime(d_partenza, '%Y-%m-%d').date(), desc, destinazione_nome=dest, lat=lat, lng=lng)
            viaggio_da_modificare.data_f = datetime.strptime(d_fine, '%Y-%m-%d').date()
            viaggio_da_modificare.update()
            flash("Informazioni viaggio aggiornate!", "success")
            return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))
        except Exception as e:
            flash(f"Errore durante la modifica: {e}", "danger")

    return render_template('modifica_viaggio.html', viaggio=viaggio)

@setup_viaggio_bp.route('/viaggio/<int:id_viaggio>/aggiungi_tappa', methods=['POST'])
@login_required
def aggiungi_tappa(id_viaggio):
    with engine.connect() as conn:
        is_admin = conn.execute(text("SELECT ruolo_admin FROM partecipanti WHERE id_viaggio = :id_v AND email_utente = :me"), {"id_v": id_viaggio, "me": session['utente_email']}).scalar()
    
    if not is_admin:
        flash("Non hai i permessi per aggiungere tappe.", "danger")
        return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

    nome_tappa = request.form.get('destinazione_nome')
    try:
        lat = float(request.form.get('lat', 0.0) or 0.0)
        lng = float(request.form.get('lng', 0.0) or 0.0)
    except ValueError:
        lat, lng = 0.0, 0.0
    
    if nome_tappa and lat != 0.0 and lng != 0.0:
        nuova_tappa = Tappa(None, id_viaggio, nome_tappa, lat, lng)
        nuova_tappa.create()
        flash(f"Tappa '{nome_tappa}' aggiunta!", "success")
    else:
        flash("Dati tappa non validi.", "danger")
        
    return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

@setup_viaggio_bp.route('/elimina_tappa/<int:id_tappa>', methods=['POST'])
@login_required
def elimina_tappa(id_tappa):
    id_viaggio = request.form.get('id_viaggio')
    with engine.connect() as conn:
        is_admin = conn.execute(text("SELECT ruolo_admin FROM partecipanti WHERE id_viaggio = :id_v AND email_utente = :me"), {"id_v": id_viaggio, "me": session['utente_email']}).scalar()
    
    if not is_admin:
        flash("Non hai i permessi per eliminare tappe.", "danger")
        return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

    t = Tappa(id_tappa, None, None, None, None)
    try:
        t.delete()
        flash("Tappa eliminata.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

@setup_viaggio_bp.route('/viaggio/<int:id_viaggio>/elimina', methods=['POST'])
@login_required
def elimina_viaggio(id_viaggio):
    with engine.connect() as conn:
        is_admin = conn.execute(text("SELECT ruolo_admin FROM partecipanti WHERE id_viaggio = :id_v AND email_utente = :me"), {"id_v": id_viaggio, "me": session['utente_email']}).scalar()
    
    if not is_admin:
        flash("Solo gli amministratori possono eliminare il viaggio.", "danger")
        return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

    try:
        viaggio = Viaggio(id_viaggio, None, None, None)
        viaggio.delete()
        flash("Viaggio eliminato correttamente.", "info")
        return redirect(url_for('viaggi'))
    except Exception as e:
        flash(f"Impossibile eliminare il viaggio: {e}", "danger")
        return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

@setup_viaggio_bp.route('/viaggio/<int:id_viaggio>/imposta_admin', methods=['POST'])
@login_required
def imposta_admin(id_viaggio):
    with engine.connect() as conn:
        is_admin = conn.execute(text("SELECT ruolo_admin FROM partecipanti WHERE id_viaggio = :id_v AND email_utente = :me"), {"id_v": id_viaggio, "me": session['utente_email']}).scalar()
    
    if not is_admin:
        flash("Non hai i permessi per modificare i ruoli.", "danger")
        return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

    email_target = request.form.get('email_target')
    azione = request.form.get('azione')
    
    v = Viaggio(id_viaggio, None, None, None)
    try:
        if azione == 'promuovi':
            v.set_admin(email_target, True)
            flash(f"Utente {email_target} promosso a Admin.", "success")
        else:
            v.set_admin(email_target, False)
            flash(f"Permessi Admin rimossi a {email_target}.", "info")
    except Exception as e:
        flash(f"Errore: {e}", "danger")
        
    return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

@setup_viaggio_bp.route('/viaggio/<int:id_viaggio>/concludi_bilancio', methods=['POST'])
@login_required
def concludi_bilancio(id_viaggio):
    with engine.connect() as conn:
        is_admin = conn.execute(text("SELECT ruolo_admin FROM partecipanti WHERE id_viaggio = :id_v AND email_utente = :me"), {"id_v": id_viaggio, "me": session['utente_email']}).scalar()
    
    if not is_admin:
        flash("Solo gli amministratori possono concludere il bilancio.", "danger")
        return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

    try:
        viaggio = Viaggio(id_viaggio, None, None, None)
        viaggio.conferma_bilancio()
        flash("Bilancio confermato! La divisione equa è stata calcolata includendo la tassa NomadCash.", "success")
    except Exception as e:
        flash(f"Errore nella conferma: {e}", "danger")
    
    return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

@setup_viaggio_bp.route('/viaggio/<int:id_viaggio>/riapri_bilancio', methods=['POST'])
@login_required
def riapri_bilancio(id_viaggio):
    with engine.connect() as conn:
        is_admin = conn.execute(text("SELECT ruolo_admin FROM partecipanti WHERE id_viaggio = :id_v AND email_utente = :me"), {"id_v": id_viaggio, "me": session['utente_email']}).scalar()
    
    if not is_admin:
        flash("Solo gli amministratori possono riaprire il bilancio.", "danger")
        return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))

    try:
        viaggio = Viaggio(id_viaggio, None, None, None)
        viaggio.riapri_bilancio()
        flash("Bilancio riaperto. Ora puoi aggiungere nuove spese o ricalcolare.", "info")
    except Exception as e:
        flash(f"Errore nella riapertura: {e}", "danger")
    
    return redirect(url_for('dettaglio_viaggio', id_viaggio=id_viaggio))
