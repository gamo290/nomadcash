# 🎓 NomadCash Academy: Il Manuale Integrale

Benvenuto studente! Questa è la guida definitiva che spiega ogni singolo ingranaggio di **NomadCash**. Se vuoi imparare a programmare applicazioni web reali, sei nel posto giusto. Analizzeremo il codice file per file, funzione per funzione.

---

## 📂 1. La Struttura del Progetto
Immagina l'app come una casa:
- **`database.py`**: Sono le fondamenta (la connessione alla terraferma).
- **`modelli.py`**: Sono i pilastri e i muri (la logica che tiene in piedi tutto).
- **`app.py`**: È il sistema elettrico e idraulico (comunica e sposta le informazioni).
- **`templates/`**: Sono le vernici e l'arredamento (ciò che l'utente vede).
- **`static/`**: Sono gli accessori (icone, foto, stili grafici).

---

## 🏗️ 2. Il Database (`database.py`)
Questo file è piccolissimo ma vitale. Crea il **Ponte** tra il codice Python e il Database MySQL.
```python
engine = create_engine(DB_URL)
```
- **`create_engine`**: Dice a Python "Ehi, usa questo indirizzo per parlare con il database!". Senza questo, l'app non avrebbe memoria.

---

## ❤️ 3. Il Cuore Logico (`modelli.py`)
Qui usiamo le **Classi** (Programmazione a Oggetti). Ogni classe rappresenta un pezzo del nostro mondo.

### 👤 Classe `Utente`
Gestisce le persone che usano l'app.
- **`generate_password_hash`**: **Sicurezza prima di tutto!** Non salviamo mai la password vera nel database, ma una versione "criptata" (l'hash). Anche se un hacker entrasse nel database, non vedrebbe la tua password.
- **`get_miei_viaggi`**: Questa funzione fa un "JOIN" (un'unione) tra la tabella Utenti e la tabella Partecipanti per dirti a quali viaggi sei iscritto.

### 🗺️ Classe `Viaggio`
Gestisce l'itinerario e chi comanda.
- **`id_viaggio`**: Ogni viaggio ha un numero unico (ID). È come il codice fiscale del viaggio.
- **Gestore Admin**: Abbiamo funzioni speciali per aggiungere o rimuovere altri amministratori, permettendo a più persone di gestire lo stesso viaggio.

### 💰 Classe `Spesa` (La più complessa!)
È il motore finanziario. 
- **`get_bilancio_completo`**: Questa è una funzione **Super Ottimizzata**. Invece di chiedere dati al database mille volte, fa una sola grande domanda organizzata e riceve tutto il bilancio in un colpo solo.
- **La Tassa NomadCash**: Qui abbiamo inserito la logica `int(totale // 300) * 0.50`. È un esempio di come la matematica si trasforma in codice per gestire costi aziendali o commissioni.

### 📌 Classe `Tappa`
Gestisce la mappa geografica. Salva il nome del luogo e le sue coordinate (**Latitudine e Longitudine**). Queste servono al Javascript per mettere i "puntini" sulla mappa.

---

## 🧠 4. Il Centro di Controllo (`app.py`)
Usa **Flask** per gestire il traffico.

### I Decoratori (`@app.route`)
Immagina un centralino:
- Se chiedi `/spese`, il centralino ti manda alla funzione `spese()`.
- **`@login_required`**: È il "buttafuori". Controlla se hai fatto il login. Se non sei loggato, ti rispedisce alla porta (la pagina di login).

### La Sessione (`session`)
È un piccolo zainetto virtuale che ogni utente porta con sé. Dentro ci salviamo:
- La tua email.
- Il tuo nome.
Questo ci permette di "ricordarti" mentre passi da una pagina all'altra senza dover rifare il login ogni secondo.

---

## 🎨 5. Il Frontend (`templates/`)
Usiamo **Jinja2**, il linguaggio che permette a Python di "scrivere" l'HTML.

### `base.html`
È il file "madre". Contiene la Navbar (la barra in alto) e i loghi. Tutti gli altri file (come `dashboard.html`) dicono `{% extends "base.html" %}`, il che significa "Prendi la base e aggiungi solo il mio pezzo speciale al centro".

### `dettaglio_viaggio.html` (Mappe e Chat)
Qui succede la magia:
- **Leaflet.js**: Una libreria Javascript che disegna la mappa usando i dati di `Tappa`.
- **Modals (Pop-up)**: Usiamo i "modals" di Bootstrap per mostrare la cronologia delle spese in stile chat senza dover cambiare pagina.
- **Filtri Jinja2**: Ad esempio `{{ "%.2f"|format(numero) }}` serve a dire a HTML: "Mostra questo numero con solo due cifre decimali, come i veri prezzi in Euro".

---

## 💡 6. Concetti Chiave per Imparare

1.  **Il Ciclo Richiesta-Risposta**: Tu clicchi un bottone (Richiesta) -> Flask (`app.py`) legge i dati -> Interroga il database (`modelli.py`) -> Restituisce una pagina disegnata (`templates`).
2.  **CRUD**: È l'acronimo di Create, Read, Update, Delete. In quasi tutte le classi vedrai queste quattro operazioni. È l'ABC della programmazione web.
3.  **Ottimizzazione**: Mai chiedere al database la stessa cosa due volte nello stesso momento. Cerca sempre di raggruppare le richieste (come abbiamo fatto per il bilancio).

*Spero che questo manuale ti aiuti a diventare un grande programmatore. Guarda il codice, prova a cambiare una riga e vedi cosa succede: è il modo migliore per imparare!* 🚀✈️💻
