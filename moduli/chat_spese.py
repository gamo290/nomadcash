from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from modelli import Spesa, Utente, Viaggio
from moduli.utils import login_required
from datetime import datetime

chat_spese_bp = Blueprint('chat_spese', __name__)

@chat_spese_bp.route('/spese', methods=['GET', 'POST'])
@login_required
def spese():
    utente_obj = Utente(session['utente_nome'], session['utente_email'], None, None)
    miei_viaggi = utente_obj.get_miei_viaggi()
    
    id_v_selezionato = request.args.get('id_viaggio', type=int)
    
    if request.method == 'POST':
        id_v = request.form.get('id_viaggio')
        descrizione = request.form.get('descrizione')
        try:
            importo = float(request.form.get('importo', 0))
        except ValueError:
            importo = 0
        email_pagatore = request.form.get('email_pagatore')
        cat = request.form.get('categoria')
        data_s = request.form.get('data_spesa')
        id_tappa = request.form.get('id_tappa')
        if not id_tappa:
            id_tappa = None
        
        try:
            nuova_spesa = Spesa(id_v, email_pagatore, descrizione, importo, cat, data_s, id_tappa=id_tappa)
            nuova_spesa.create()
            flash("Spesa registrata correttamente!", "success")
            return redirect(url_for('chat_spese.spese', id_viaggio=id_v))
        except Exception as e:
            flash(f"Errore nella registrazione: {e}", "danger")

    spese_viaggio = []
    bilancio = None
    viaggio_selezionato = None
    tappe = []
    partecipanti = []

    if id_v_selezionato:
        viaggio_selezionato = next((v for v in miei_viaggi if v['id_viaggio'] == id_v_selezionato), None)
        if viaggio_selezionato:
            from modelli import Tappa
            spese_viaggio = Spesa.get_spese_per_viaggio(id_v_selezionato)
            bilancio = Spesa.divisione_equa(id_v_selezionato)
            tappe = Tappa.get_tappe_by_viaggio(id_v_selezionato)
            partecipanti = Viaggio.get_partecipanti(id_v_selezionato)
            
            # Inseriamo la tassa NomadCash nella cronologia se presente
            if bilancio and not isinstance(bilancio, str) and bilancio["info_generali"]["tassa_totale"] > 0:
                spese_viaggio.append({
                    'nome_utente': 'NomadCash',
                    'email_utente': 'sistema@nomadcash.com',
                    'data_spesa': 'Sempre attivo',
                    'testo_messaggio': 'Commissione per il servizio NomadCash (calcolata per partecipante)',
                    'importo': bilancio["info_generali"]["tassa_totale"],
                    'categoria': 'Sistema',
                    'pagata': True,
                    'id_spesa': 0
                })

    return render_template('spese.html', 
                           viaggi=miei_viaggi, 
                           spese=spese_viaggio, 
                           bilancio=bilancio,
                           viaggio_selezionato=viaggio_selezionato,
                           id_v_selezionato=id_v_selezionato,
                           tappe=tappe,
                           partecipanti=partecipanti)

@chat_spese_bp.route('/paga_spesa/<int:id_spesa>')
@login_required
def paga_spesa(id_spesa):
    id_viaggio = request.args.get('id_viaggio')
    s = Spesa(id_spesa, None, None, None, None, None, None)
    try:
        s.paga()
        flash("Spesa saldata con successo!", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('chat_spese.spese', id_viaggio=id_viaggio))

@chat_spese_bp.route('/elimina_spesa/<int:id_spesa>')
@login_required
def elimina_spesa(id_spesa):
    id_viaggio = request.args.get('id_viaggio')
    s = Spesa(id_spesa, None, None, None, None, None, None)
    try:
        s.delete()
        flash("Spesa eliminata.", "info")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('chat_spese.spese', id_viaggio=id_viaggio))
