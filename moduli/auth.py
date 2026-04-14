import streamlit as st
from modelli import Utente

def mostra_pagina_login():
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