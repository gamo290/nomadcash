from database import engine
from sqlalchemy import text
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Viaggio:
    def __init__(self, id, nome, date, itinerario):
        self.id_viaggio = id 
        self.nome = nome 
        self.data_p = date
        self.data_f = None
        self.descrizione = itinerario


        
    def create(self, email_creatore):
        if self.data_f < self.data_p:
            raise ValueError("Errore database: La data di fine precede la data di inizio.")
            
        query_viaggio = text("""INSERT INTO viaggi (nome_viaggio, data_partenza, data_fine, descrizione_itinerario)
                        VALUES (:n, :p, :f, :d)""")
        
        #La query per il ponte logico
        query_partecipante = text("""INSERT INTO partecipanti (id_viaggio, email_utente)
                                     VALUES (:id_v, :email)""")
        
        with engine.begin() as conn:
            # Salva il viaggio e recupera il suo nuovo ID
            result = conn.execute(query_viaggio, {"n": self.nome, "p": self.data_p, "f": self.data_f, "d": self.descrizione})
            self.id_viaggio = result.lastrowid
            
            # Collega subito l'ID del viaggio all'email del creatore!
            conn.execute(query_partecipante, {"id_v": self.id_viaggio, "email": email_creatore})

    def read(self):
        query = text("SELECT * FROM viaggi WHERE id_viaggio = :id")
        with engine.connect() as conn:
            res = conn.execute(query, {"id": self.id_viaggio}).mappings().fetchone()
            return dict(res) if res else None

    def update(self):
        query = text("""UPDATE viaggi SET nome_viaggio = :n, descrizione_itinerario = :d 
        WHERE id_viaggio = :id """)
        with engine.begin() as conn:
            conn.execute(query, {"n": self.nome, "d": self.descrizione, "id": self.id_viaggio})

    def delete(self):
        with engine.begin() as conn:
            check = conn.execute(text("SELECT COUNT(*) FROM spese WHERE id_viaggio=:id"), {"id": self.id_viaggio}).scalar()
            if check > 0:
                raise Exception("Cancellazione bloccata: esistono spese collegate.")
            conn.execute(text("DELETE FROM viaggi WHERE id_viaggio=:id"), {"id": self.id_viaggio})

    @staticmethod
    def find_viaggio_attivo():
        oggi = datetime.now().date()
        query = text("SELECT * FROM viaggi WHERE data_fine >= :oggi ORDER BY data_partenza ASC LIMIT 1")
        with engine.connect() as conn:
            res = conn.execute(query, {"oggi": oggi}).mappings().fetchone()
            return dict(res) if res else None 
    @staticmethod
    def get_tutti_viaggi():
        query = text("SELECT * FROM viaggi ORDER BY data_partenza DESC")
        with engine.connect() as conn:
            risultati = conn.execute(query).mappings().fetchall()
            return [dict(r) for r in risultati]
             
class Utente:
    def __init__(self, nome, email, avatar, password, admin=False):
        self.nome = nome 
        self.email = email 
        self.avatar = avatar
        self.password = password
        self.admin = admin
        
    def create(self):
        query_controllo = text("SELECT COUNT(*) FROM utenti WHERE email = :e")
        query_inserimento = text("""INSERT INTO utenti (email, nome, avatar, password_hash, admin)
                                    VALUES (:e, :n, :av, :pw, :ad)""")
        
        with engine.begin() as conn:
            check = conn.execute(query_controllo, {"e": self.email}).scalar()
            
            if check > 0:
                raise ValueError("Questa email è già registrata nel sistema!")
            
            password_crittografata = generate_password_hash(self.password)
            
            # self.avatar conterrà i bytes dell'immagine caricata
            conn.execute(query_inserimento, {
                "e": self.email,
                "n": self.nome,
                "av": self.avatar,
                "pw": password_crittografata,
                "ad": self.admin
            })

            
    @staticmethod
    def login(email_inserita, password_inserita):
        query = text("SELECT * FROM utenti WHERE email = :e")
        
        with engine.connect() as conn:
            utente_trovato = conn.execute(query, {"e": email_inserita}).mappings().fetchone()
            
            if not utente_trovato:
                return False
                
            if check_password_hash(utente_trovato['password_hash'], password_inserita):
                return dict(utente_trovato) 
            else:
                return False
        
    def read(self):
        query = text("SELECT * FROM utenti WHERE email = :em")
        with engine.connect() as conn:
            res = conn.execute(query, {"em": self.email}).mappings().fetchone()
            return dict(res) if res else None

    def update_full(self, nuova_email, nuovo_avatar=None):
        queries = [
            text("UPDATE partecipanti SET email_utente = :new WHERE email_utente = :old"),
            text("UPDATE amicizie SET richiedente = :new WHERE richiedente = :old"),
            text("UPDATE amicizie SET ricevente = :new WHERE ricevente = :old"),
            text("UPDATE utenti SET nome = :n, email = :new WHERE email = :old"),
            text("UPDATE spese SET email_utente = :new WHERE email_utente = :old")
        ]
        with engine.begin() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            conn.execute(queries[0], {"new": nuova_email, "old": self.email})
            conn.execute(queries[1], {"new": nuova_email, "old": self.email})
            conn.execute(queries[2], {"new": nuova_email, "old": self.email})
            conn.execute(queries[4], {"new": nuova_email, "old": self.email})
            conn.execute(queries[3], {"n": self.nome, "new": nuova_email, "old": self.email})
            
            if nuovo_avatar:
                conn.execute(text("UPDATE utenti SET avatar = :av WHERE email = :new"), {"av": nuovo_avatar, "new": nuova_email})
                self.avatar = nuovo_avatar
                
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        self.email = nuova_email


    def delete_full(self):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM partecipanti WHERE email_utente = :em"), {"em": self.email})
            conn.execute(text("DELETE FROM amicizie WHERE richiedente = :em OR ricevente = :em"), {"em": self.email})
            # ON DELETE CASCADE gestirà le spese collegate in 'spese'
            conn.execute(text("DELETE FROM utenti WHERE email = :em"), {"em": self.email})


    def diventa_admin(self):
        if self.admin == True:
            raise Exception("Operazione negata: L'utente è già un amministratore.")

        oggi = datetime.now().date()
        query_viaggio_attivo = text("""
            SELECT COUNT(*) FROM spese 
            JOIN viaggi ON spese.id_viaggio = viaggi.id_viaggio
            WHERE spese.email_utente = :em AND viaggi.data_fine >= :oggi
        """)
        
        with engine.connect() as conn:
            check_viaggi = conn.execute(query_viaggio_attivo, {"em": self.email, "oggi": oggi}).scalar()
            
            if check_viaggi > 0:
                raise Exception("Operazione negata: L'utente è già coinvolto in un altro viaggio attivo.")

        self.admin = True
        with engine.begin() as conn:
            conn.execute(text("UPDATE utenti SET admin = True WHERE email = :em"), {"em": self.email})

    def diventa_non_admin(self, id_viaggio):
        if self.admin == False:
            raise Exception("Operazione ignorata: L'utente non è un amministratore.")

        oggi = datetime.now().date()
        
        with engine.connect() as conn:
            viaggio = conn.execute(
                text("SELECT data_fine FROM viaggi WHERE id_viaggio = :id"), 
                {"id": id_viaggio}
            ).fetchone()
            
            if not viaggio:
                raise Exception("Errore: Viaggio non trovato nel database.")
                
            data_fine_viaggio = viaggio[0]
            
            if isinstance(data_fine_viaggio, str):
                data_fine_viaggio = datetime.strptime(data_fine_viaggio, '%Y-%m-%d').date()
            
            if oggi <= data_fine_viaggio:
                raise Exception("Operazione bloccata: Il viaggio è ancora in corso! Dimissioni negate.")

            spese_non_pagate = conn.execute(
                text("SELECT COUNT(*) FROM spese WHERE id_viaggio = :id AND pagata = False"), 
                {"id": id_viaggio}
            ).scalar()
            
            if spese_non_pagate > 0:
                raise Exception(f"Operazione bloccata: Ci sono ancora {spese_non_pagate} spese da saldare nel gruppo!")

        self.admin = False
        with engine.begin() as conn:
            conn.execute(text("UPDATE utenti SET admin = False WHERE email = :em"), {"em": self.email})

    
    def get_miei_viaggi(self, filter_type='tutti'):
        oggi = datetime.now().date()
        cond = ""
        if filter_type == 'in_corso':
            cond = "AND v.data_fine >= :oggi"
        elif filter_type == 'recenti':
            cond = "AND v.data_fine < :oggi"
            
        query = text(f"""
            SELECT v.* FROM viaggi v
            JOIN partecipanti p ON v.id_viaggio = p.id_viaggio
            WHERE p.email_utente = :em {cond}
            ORDER BY v.data_partenza DESC
        """)
        with engine.connect() as conn:
            risultati = conn.execute(query, {"em": self.email, "oggi": oggi}).mappings().fetchall()
            return [dict(r) for r in risultati]

        
      
    def get_compagni(self):
        query = text("""
            SELECT u.nome, u.email, u.avatar
            FROM utenti u
            JOIN amicizie a ON (u.email = a.richiedente OR u.email = a.ricevente)
            WHERE (a.richiedente = :mia_email OR a.ricevente = :mia_email) 
            AND u.email != :mia_email AND a.stato = 'accettata'
        """)
        with engine.connect() as conn:
            risultati = conn.execute(query, {"mia_email": self.email}).mappings().fetchall()
            return [dict(r) for r in risultati]

    def get_viaggi_in_comune(self, email_amico):
        query = text("""
            SELECT DISTINCT v.id_viaggio, v.nome_viaggio, v.data_partenza
            FROM viaggi v
            JOIN partecipanti p1 ON v.id_viaggio = p1.id_viaggio
            JOIN partecipanti p2 ON v.id_viaggio = p2.id_viaggio
            WHERE p1.email_utente = :mia_email AND p2.email_utente = :email_amico
        """)
        with engine.connect() as conn:
            risultati = conn.execute(query, {"mia_email": self.email, "email_amico": email_amico}).mappings().fetchall()
            return [dict(r) for r in risultati]

    def get_stats(self):
        oggi = datetime.now().date()
        with engine.connect() as conn:
            # Viaggi in corso
            attivi = conn.execute(text("""
                SELECT COUNT(*) FROM partecipanti p 
                JOIN viaggi v ON p.id_viaggio = v.id_viaggio 
                WHERE p.email_utente = :em AND v.data_fine >= :oggi
            """), {"em": self.email, "oggi": oggi}).scalar()
            
            # Amici totali
            amici = conn.execute(text("""
                SELECT COUNT(*) FROM amicizie 
                WHERE (richiedente = :em OR ricevente = :em) AND stato = 'accettata'
            """), {"em": self.email}).scalar()
            
            # Spesa totale storica
            spesa = conn.execute(text("""
                SELECT SUM(importo) FROM spese WHERE email_utente = :em
            """), {"em": self.email}).scalar()
            
            return {
                "viaggi_attivi": attivi or 0,
                "amici_totali": amici or 0,
                "spesa_storica": float(spesa) if spesa else 0.0
            }

    def get_amici_frequenti(self, limit=5):
        query = text("""
            SELECT u.nome, u.email, COUNT(p2.id_viaggio) as viaggi_comune
            FROM partecipanti p1
            JOIN partecipanti p2 ON p1.id_viaggio = p2.id_viaggio
            JOIN utenti u ON p2.email_utente = u.email
            WHERE p1.email_utente = :em AND p2.email_utente != :em
            GROUP BY u.email, u.nome
            ORDER BY viaggi_comune DESC
            LIMIT :lim
        """)
        with engine.connect() as conn:
            risultati = conn.execute(query, {"em": self.email, "lim": limit}).mappings().fetchall()
            return [dict(r) for r in risultati]


class Spesa:
    def __init__(self, id_viaggio, email_utente, testo_messaggio, importo, categoria, data_spesa):
        self.id_spesa = None 
        self.id_viaggio = id_viaggio
        self.email_utente = email_utente
        self.testo_messaggio = testo_messaggio
        
        if importo <= 0:
            raise ValueError("Errore: L'importo della spesa deve essere maggiore di zero.")
        self.importo = importo
        
        self.categoria = categoria
        self.data_spesa = data_spesa
        self.pagata = False
        self.data_pagamento = None

    def create(self):
        query = text("""
            INSERT INTO spese (id_viaggio, email_utente, testo_messaggio, importo, categoria, data_spesa, pagata, data_pagamento)
            VALUES (:iv, :eu, :tm, :imp, :cat, :ds, :pag, :dp)
        """)
        with engine.begin() as conn:
            res = conn.execute(query, {
                "iv": self.id_viaggio, "eu": self.email_utente, "tm": self.testo_messaggio,
                "imp": self.importo, "cat": self.categoria, "ds": self.data_spesa,
                "pag": self.pagata, "dp": self.data_pagamento
            })
            self.id_spesa = res.lastrowid

    def read(self):
        query = text("SELECT * FROM spese WHERE id_spesa = :id")
        with engine.connect() as conn:
            res = conn.execute(query, {"id": self.id_spesa}).mappings().fetchone()
            return dict(res) if res else None

    def delete(self):
        if self.pagata:
            raise Exception("Impossibile eliminare: questa spesa è già stata saldata e chiusa.")
            
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM spese WHERE id_spesa = :id"), {"id": self.id_spesa})

    def segna_come_pagata(self):
        if self.pagata:
            raise Exception("Questa spesa risulta già pagata!")
            
        oggi = datetime.now().date()
        query = text("UPDATE spese SET pagata = True, data_pagamento = :oggi WHERE id_spesa = :id")
        
        with engine.begin() as conn:
            conn.execute(query, {"oggi": oggi, "id": self.id_spesa})
            
        self.pagata = True
        self.data_pagamento = oggi

    @staticmethod
    def numero_viaggiatori(id_viaggio):
        query = text("SELECT COUNT(email_utente) FROM partecipanti WHERE id_viaggio = :id")
        with engine.connect() as conn:
            totale_viaggiatori = conn.execute(query, {"id": id_viaggio}).scalar()
            return totale_viaggiatori if totale_viaggiatori else 0

    @staticmethod
    def divisione_equa(id_viaggio):
        n_viaggiatori = Spesa.numero_viaggiatori(id_viaggio)
        if n_viaggiatori == 0:
            return "Nessun viaggiatore registrato per questo viaggio."
            
        query_totale = text("SELECT SUM(importo) FROM spese WHERE id_viaggio = :id AND pagata = False")
        with engine.connect() as conn:
            totale_spese = conn.execute(query_totale, {"id": id_viaggio}).scalar()
            
        if not totale_spese:
            return "Non ci sono spese da saldare per questo viaggio."
            
        quota_individuale = totale_spese / n_viaggiatori
        
        return {
            "totale_da_saldare": totale_spese,
            "numero_viaggiatori": n_viaggiatori,
            "quota_a_testa": round(quota_individuale, 2)
        }
        
    @staticmethod
    def bilancio_utente_viaggio(id_viaggio, email_utente):
        info_generali = Spesa.divisione_equa(id_viaggio)
        if isinstance(info_generali, str):
            return {"pagato": 0, "quota": 0, "netto": 0}

        quota_a_testa = info_generali['quota_a_testa']

        
        query_pagato = text("SELECT SUM(importo) FROM spese WHERE id_viaggio = :id AND email_utente = :em AND pagata = False")
        with engine.connect() as conn:
            pagato = conn.execute(query_pagato, {"id": id_viaggio, "em": email_utente}).scalar()

        if not pagato:
            pagato = 0

        
        netto = round(pagato - quota_a_testa, 2)

        return {
            "pagato": round(pagato, 2),
            "quota": quota_a_testa,
            "netto": netto
        }

class Amicizia:
    @staticmethod
    def invia_richiesta(richiedente_email, ricevente_email):
        query_check = text("SELECT COUNT(*) FROM utenti WHERE email = :em")
        with engine.connect() as conn:
            check = conn.execute(query_check, {"em": ricevente_email}).scalar()
            if check == 0:
                raise ValueError("Errore: Utente non trovato.")
                
        # Check if they are the same
        if richiedente_email == ricevente_email:
            raise ValueError("Non puoi inviare una richiesta a te stesso.")
            
        # Check if friendship or request already exists
        query_exist = text("""
            SELECT COUNT(*) FROM amicizie 
            WHERE (richiedente = :r1 AND ricevente = :r2) OR (richiedente = :r2 AND ricevente = :r1)
        """)
        with engine.connect() as conn:
            check = conn.execute(query_exist, {"r1": richiedente_email, "r2": ricevente_email}).scalar()
            if check > 0:
                raise ValueError("Esiste già una richiesta pendente o un compagno con questa email.")
                
        query = text("""
            INSERT INTO amicizie (richiedente, ricevente, stato)
            VALUES (:rich, :ricev, 'in attesa')
        """)
        with engine.begin() as conn:
            conn.execute(query, {"rich": richiedente_email, "ricev": ricevente_email})
            
    @staticmethod
    def get_richieste_ricevute(email_utente):
        query = text("""
            SELECT a.id_amicizia, a.richiedente, u.nome
            FROM amicizie a
            JOIN utenti u ON a.richiedente = u.email
            WHERE a.ricevente = :em AND a.stato = 'in attesa'
        """)
        with engine.connect() as conn:
            risultati = conn.execute(query, {"em": email_utente}).mappings().fetchall()
            return [dict(r) for r in risultati]

    @staticmethod
    def accetta_richiesta(id_amicizia):
        query = text("UPDATE amicizie SET stato = 'accettata' WHERE id_amicizia = :id")
        with engine.begin() as conn:
            conn.execute(query, {"id": id_amicizia})

    @staticmethod
    def rifiuta_richiesta(id_amicizia):
        query = text("DELETE FROM amicizie WHERE id_amicizia = :id")
        with engine.begin() as conn:
            conn.execute(query, {"id": id_amicizia})

    @staticmethod
    def rimuovi(email1, email2):
        query = text("""
            DELETE FROM amicizie 
            WHERE ((richiedente = :e1 AND ricevente = :e2) OR (richiedente = :e2 AND ricevente = :e1))
            AND stato = 'accettata'
        """)
        with engine.begin() as conn:
            conn.execute(query, {"e1": email1, "e2": email2})
