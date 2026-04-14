import streamlit as st
from modelli import Utente, Viaggio, Spesa, Amicizia
from sqlalchemy import text
from database import engine

st.set_page_config(page_title="NomadCash", layout="wide")

# --- INIZIALIZZAZIONE SESSIONE ---
if 'utente_loggato' not in st.session_state:
    st.session_state.utente_loggato = None

if 'pagina_attiva' not in st.session_state:
    st.session_state.pagina_attiva = "Viaggi in corso"

if 'viaggio_selezionato' not in st.session_state:
    st.session_state.viaggio_selezionato = None

def cambia_pagina(nuova_pagina):
    st.session_state.pagina_attiva = nuova_pagina

# --- LOGICA DI ACCESSO ---
if st.session_state.utente_loggato is None:
    st.title("NomadCash - Accesso")
    tab_login, tab_registrazione = st.tabs(["Login", "Registrazione"])
    
    with tab_login:
        st.header("Accedi")
        email_login = st.text_input("Email", key="login_email")
        password_login = st.text_input("Password", type="password", key="login_pw")
        if st.button("Entra"):
            if email_login and password_login:
                utente = Utente.login(email_login, password_login)
                if utente:
                    st.session_state.utente_loggato = utente
                    st.rerun()
                else:
                    st.error("Email o password non validi.")
            else:
                st.warning("Inserisci tutti i dati.")
                
    with tab_registrazione:
        st.header("Nuovo Utente")
        nome_reg = st.text_input("Nome")
        email_reg = st.text_input("Email")
        avatar_reg = st.selectbox("Avatar", ["Avatar 1", "Avatar 2", "Avatar 3"])
        password_reg = st.text_input("Password", type="password")
        if st.button("Registrati"):
            if nome_reg and email_reg and password_reg:
                try:
                    nuovo_utente = Utente(nome=nome_reg, email=email_reg, avatar=avatar_reg, password=password_reg, admin=False)
                    nuovo_utente.create()
                    st.success("Registrazione completata. Ora puoi fare il login.")
                except ValueError as e:
                    st.error(str(e))
            else:
                st.warning("Compila tutti i campi.")

else:
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("NomadCash")
        st.caption(f"Bentornato, {st.session_state.utente_loggato['nome']}!")
        st.divider()
        
        # Creiamo l'oggetto utente per recuperare i suoi dati reali
        utente_obj = Utente(
            st.session_state.utente_loggato['nome'],
            st.session_state.utente_loggato['email'],
            None, None
        )

        with st.expander("I miei viaggi", expanded=True):
            st.button("✈️ Viaggi in corso", 
                      type="primary" if st.session_state.pagina_attiva == "Viaggi in corso" else "secondary", 
                      use_container_width=True, on_click=cambia_pagina, args=("Viaggi in corso",))
            
            st.button("✨ Crea nuovo", 
                      type="primary" if st.session_state.pagina_attiva == "Crea nuovo" else "secondary", 
                      use_container_width=True, on_click=cambia_pagina, args=("Crea nuovo",))
            
            st.button("💳 Spese", 
                      type="primary" if st.session_state.pagina_attiva == "Spese" else "secondary", 
                      use_container_width=True, on_click=cambia_pagina, args=("Spese",))
            
            st.button("👥 Compagni di viaggio", 
                      type="primary" if st.session_state.pagina_attiva == "Compagni di viaggio" else "secondary", 
                      use_container_width=True, on_click=cambia_pagina, args=("Compagni di viaggio",))

            # LISTA VIAGGI FILTRATA (PRIVACY)
            miei_viaggi = utente_obj.get_miei_viaggi()
            if miei_viaggi:
                st.divider()
                st.caption("Viaggi salvati")
                for v in miei_viaggi:
                    is_active = (st.session_state.pagina_attiva == "Viaggio Specifico" and 
                                 st.session_state.viaggio_selezionato == v['nome_viaggio'])
                    if st.button(v['nome_viaggio'], key=f"side_{v['id_viaggio']}", 
                                 type="primary" if is_active else "secondary", use_container_width=True):
                        st.session_state.pagina_attiva = "Viaggio Specifico"
                        st.session_state.viaggio_selezionato = v['nome_viaggio']
                        st.rerun()

        st.divider()
        st.button("📦 Archivio", 
                  type="primary" if st.session_state.pagina_attiva == "Archivio" else "secondary", 
                  use_container_width=True, on_click=cambia_pagina, args=("Archivio",))
        
        st.button("⚙️ Impostazioni", 
                  type="primary" if st.session_state.pagina_attiva == "Impostazioni" else "secondary", 
                  use_container_width=True, on_click=cambia_pagina, args=("Impostazioni",))
            
        st.divider()
        if st.button("🚪 Esci dall'account", type="secondary", use_container_width=True):
            st.session_state.utente_loggato = None
            st.session_state.viaggio_selezionato = None
            st.session_state.pagina_attiva = "Viaggi in corso"
            st.rerun()

    # --- CONTENUTO PRINCIPALE ---
    scelta_attiva = st.session_state.pagina_attiva

    if scelta_attiva == "Viaggi in corso":
        st.title("I tuoi Viaggi")
        
        # Peschiamo solo i viaggi dell'utente (utente_obj è definito nella sidebar)
        lista_viaggi = utente_obj.get_miei_viaggi()
        
        if lista_viaggi:
            nomi_viaggi = [v['nome_viaggio'] for v in lista_viaggi]
            
            indice_default = 0
            if st.session_state.viaggio_selezionato in nomi_viaggi:
                indice_default = nomi_viaggi.index(st.session_state.viaggio_selezionato)
                
            viaggio_selezionato_nome = st.selectbox("🌍 Seleziona il viaggio da visualizzare:", nomi_viaggi, index=indice_default)
            viaggio_attivo = next((v for v in lista_viaggi if v['nome_viaggio'] == viaggio_selezionato_nome), None)
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("Data Partenza", str(viaggio_attivo['data_partenza']))
            col2.metric("Data Ritorno", str(viaggio_attivo['data_fine']))
            
            try:
                giorni_totali = (viaggio_attivo['data_fine'] - viaggio_attivo['data_partenza']).days
                col3.metric("Durata (giorni)", giorni_totali)
            except: pass
                
            st.divider()
            st.subheader("Itinerario")
            st.write(viaggio_attivo['descrizione_itinerario'])
            
            st.divider()
            st.subheader("Riepilogo Spese")
            bilancio = Spesa.divisione_equa(viaggio_attivo['id_viaggio'])
            
            if isinstance(bilancio, str):
                st.info(bilancio)
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Totale da saldare", f"€ {bilancio['totale_da_saldare']}")
                c2.metric("Viaggiatori", bilancio['numero_viaggiatori'])
                c3.metric("Quota a testa", f"€ {bilancio['quota_a_testa']}")
                
            st.write("") 
            if st.button("➕ Aggiungi nuova spesa", type="primary", use_container_width=True):
                st.session_state.pagina_attiva = "Spese"
                st.session_state.viaggio_selezionato = viaggio_selezionato_nome
                st.rerun()
                
            st.divider()
            with st.expander("🚨 Zona di Pericolo", expanded=False):
                if st.button("🗑️ Elimina questo viaggio", use_container_width=True):
                    viaggio_da_eliminare = Viaggio(viaggio_attivo['id_viaggio'], viaggio_attivo['nome_viaggio'], None, None)
                    try:
                        viaggio_da_eliminare.delete()
                        st.session_state.viaggio_selezionato = None
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        else:
            st.info("Non hai ancora registrato nessun viaggio.")
            if st.button("Pianifica un nuovo viaggio", type="primary"):
                st.session_state.pagina_attiva = "Crea nuovo"
                st.rerun()

    elif scelta_attiva == "Viaggio Specifico":
        st.title(f"Dettagli viaggio: {st.session_state.viaggio_selezionato}")
        st.info("Visualizza i dettagli completi nella sezione 'Viaggi in corso'.")

    elif scelta_attiva == "Crea nuovo":
        st.title("Organizza un nuovo viaggio")
        nome_v = st.text_input("Nome del Viaggio")
        col1, col2 = st.columns(2)
        with col1: d_partenza = st.date_input("Data di Partenza")
        with col2: d_fine = st.date_input("Data di Fine", min_value=d_partenza)
        desc = st.text_area("Itinerario")
        
        st.divider()
        st.subheader("Invita Amici")
        # Query per amici confermati
        query_amici = text("""
            SELECT u.nome, u.email FROM utenti u
            JOIN amicizie a ON (u.email = a.richiedente OR u.email = a.ricevente)
            WHERE (a.richiedente = :me OR a.ricevente = :me) 
            AND u.email != :me AND a.stato = 'accettata'
        """)
        with engine.connect() as conn:
            amici = conn.execute(query_amici, {"me": st.session_state.utente_loggato['email']}).mappings().fetchall()
        
        invitati = []
        if amici:
            for am in amici:
                if st.checkbox(f"{am['nome']} ({am['email']})", key=f"inv_{am['email']}"):
                    invitati.append(am['email'])
        else:
            st.caption("Nessun amico trovato da invitare.")

        if st.button("Salva Viaggio", type="primary"):
            if nome_v and desc:
                nuovo_v = Viaggio(None, nome_v, d_partenza, desc)
                nuovo_v.data_f = d_fine
                nuovo_v.create(email_creatore=st.session_state.utente_loggato['email'])
                
                # Aggiungiamo gli invitati
                if invitati:
                    with engine.begin() as conn:
                        for em_amico in invitati:
                            conn.execute(text("INSERT IGNORE INTO partecipanti (id_viaggio, email_utente) VALUES (:id_v, :em)"), 
                                         {"id_v": nuovo_v.id_viaggio, "em": em_amico})
                
                st.session_state.viaggio_selezionato = nome_v
                st.session_state.pagina_attiva = "Viaggi in corso"
                st.rerun()
            else:
                st.warning("Compila i campi obbligatori.")

    elif scelta_attiva == "Spese":
        st.title("💸 Gestione Spese")
        # Logica caricamento viaggi per tendina
        m_viaggi = utente_obj.get_miei_viaggi()
        if m_viaggi:
            n_v = [v['nome_viaggio'] for v in m_viaggi]
            idx = n_v.index(st.session_state.viaggio_selezionato) if st.session_state.viaggio_selezionato in n_v else 0
            v_scelto_n = st.selectbox("Viaggio:", n_v, index=idx)
            v_att = next(v for v in m_viaggi if v['nome_viaggio'] == v_scelto_n)
            
            st.divider()
            t_utenti = Utente.get_tutti_utenti() # Qui potresti filtrare solo per i partecipanti del viaggio!
            l_utenti = [f"{u['nome']} ({u['email']})" for u in t_utenti]
            pagatore = st.selectbox("Chi ha pagato?", l_utenti)
            
            c1, c2 = st.columns(2)
            imp = c1.number_input("Importo (€)", min_value=0.0)
            cat = c1.selectbox("Cat.", ["Cibo", "Trasporti", "Alloggio", "Altro"])
            dat = c2.date_input("Data")
            des = c2.text_input("Cosa?")
            
            if st.button("Salva", use_container_width=True):
                email_p = pagatore.split("(")[1].replace(")", "")
                n_spesa = Spesa(v_att['id_viaggio'], email_p, des, imp, cat, dat)
                n_spesa.create()
                st.success("Spesa salvata!")
        else:
            st.warning("Crea un viaggio prima di inserire spese.")

    elif scelta_attiva == "Compagni di viaggio":
        st.title("👥 Compagni di viaggio")
        richieste = Amicizia.get_richieste_ricevute(st.session_state.utente_loggato['email'])
        t1, t2, t3 = st.tabs(["I miei Compagni", "➕ Aggiungi", f"🔔 Richieste ({len(richieste)})"])
        
        with t2:
            em_ricerca = st.text_input("Email dell'amico")
            if st.button("Invia Richiesta"):
                try:
                    Amicizia.invia_richiesta(st.session_state.utente_loggato['email'], em_ricerca)
                    st.success("Inviata!")
                except Exception as e: st.error(str(e))
        
        with t3:
            for r in richieste:
                col, b1, b2 = st.columns([3,1,1])
                col.write(f"Richiesta da {r['nome']}")
                if b1.button("✅", key=f"acc_{r['id_amicizia']}"):
                    Amicizia.accetta_richiesta(r['id_amicizia']); st.rerun()
                if b2.button("❌", key=f"rif_{r['id_amicizia']}"):
                    Amicizia.rifiuta_richiesta(r['id_amicizia']); st.rerun()
        
        with t1:
            compagni = utente_obj.get_compagni()
            if compagni:
                sel = st.selectbox("Amico:", [f"{c['nome']} ({c['email']})" for c in compagni])
                em_amico = sel.split("(")[1].replace(")", "")
                v_comuni = utente_obj.get_viaggi_in_comune(em_amico)
                if v_comuni:
                    v_sel = st.selectbox("Bilancio Viaggio:", [v['nome_viaggio'] for v in v_comuni])
                    v_info = next(v for v in v_comuni if v['nome_viaggio'] == v_sel)
                    b_mio = Spesa.bilancio_utente_viaggio(v_info['id_viaggio'], st.session_state.utente_loggato['email'])
                    st.metric("Tuo Netto", f"€ {b_mio['netto']}")
            else: st.info("Ancora nessun compagno.")

    elif scelta_attiva == "Archivio":
        st.title("Archivio Viaggi")
        st.write("Sezione in sviluppo.")

    elif scelta_attiva == "Impostazioni":
        st.title("Impostazioni")
        st.write(f"Email: {st.session_state.utente_loggato['email']}")