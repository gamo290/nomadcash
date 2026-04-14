from database import engine
from sqlalchemy import text
from datetime import datetime
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash

class Viaggio:
    def __init__(self, id, nome, date, itinerario, destinazione_nome="Sconosciuta", lat=0.0, lng=0.0):
        self.id_viaggio = id 
        self.nome = nome 
        self.data_p = date
        self.data_f = None
        self.descrizione = itinerario
        self.destinazione_nome = destinazione_nome
        self.lat = lat
        self.lng = lng


        
    def create(self, email_creatore):
        if self.data_f < self.data_p:
            raise ValueError("Errore database: La data di fine precede la data di inizio.")
            
        query_viaggio = text("""INSERT INTO viaggi (nome_viaggio, data_partenza, data_fine, descrizione_itinerario, destinazione_nome, lat, lng)
                        VALUES (:n, :p, :f, :d, :dest, :lat, :lng)""")
        
        #La query per il ponte logico
        query_partecipante = text("""INSERT INTO partecipanti (id_viaggio, email_utente, ruolo_admin)
                                     VALUES (:id_v, :email, True)""")
        
        with engine.begin() as conn:
            # Salva il viaggio e recupera il suo nuovo ID
            result = conn.execute(query_viaggio, {"n": self.nome, "p": self.data_p, "f": self.data_f, "d": self.descrizione, "dest": self.destinazione_nome, "lat": self.lat, "lng": self.lng})
            self.id_viaggio = result.lastrowid
            
            # Collega subito l'ID del viaggio all'email del creatore!
            conn.execute(query_partecipante, {"id_v": self.id_viaggio, "email": email_creatore})

    def read(self):
        query = text("SELECT * FROM viaggi WHERE id_viaggio = :id")
        with engine.connect() as conn:
            res = conn.execute(query, {"id": self.id_viaggio}).mappings().fetchone()
            return dict(res) if res else None

    def update(self):
        query = text("""UPDATE viaggi SET nome_viaggio = :n, descrizione_itinerario = :d, destinazione_nome = :dest, lat = :lat, lng = :lng 
        WHERE id_viaggio = :id """)
        with engine.begin() as conn:
            conn.execute(query, {"n": self.nome, "d": self.descrizione, "id": self.id_viaggio, "dest": self.destinazione_nome, "lat": self.lat, "lng": self.lng})

    def delete(self):
        with engine.begin() as conn:
            # Elimina prima le spese associate e le partecipazioni per non avere errori di foreign key
            conn.execute(text("DELETE FROM spese WHERE id_viaggio=:id"), {"id": self.id_viaggio})
            conn.execute(text("DELETE FROM tappe WHERE id_viaggio=:id"), {"id": self.id_viaggio})
            conn.execute(text("DELETE FROM partecipanti WHERE id_viaggio=:id"), {"id": self.id_viaggio})
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

    def set_admin(self, email_target, stato):
        query = text("UPDATE partecipanti SET ruolo_admin = :s WHERE id_viaggio = :id_v AND email_utente = :em")
        with engine.begin() as conn:
            conn.execute(query, {"s": stato, "id_v": self.id_viaggio, "em": email_target})

    def conferma_bilancio(self):
        # Recuperiamo il totale storico delle spese e il numero di partecipanti
        query_data = text("""
            SELECT 
                (SELECT COALESCE(SUM(importo), 0) FROM spese WHERE id_viaggio = :id) as totale,
                (SELECT COUNT(*) FROM partecipanti WHERE id_viaggio = :id) as n_p
        """)
        
        query_update = text("""
            UPDATE viaggi 
            SET bilancio_confermato = 1, 
                tassa_totale = CASE 
                    WHEN :tot > 300 THEN tassa_totale + (0.50 * :num_p)
                    ELSE tassa_totale 
                END 
            WHERE id_viaggio = :id
        """)
        with engine.begin() as conn:
            res = conn.execute(query_data, {"id": self.id_viaggio}).mappings().fetchone()
            totale = res['totale']
            num_p = res['n_p']
            conn.execute(query_update, {"id": self.id_viaggio, "tot": totale, "num_p": num_p})

    def riapri_bilancio(self):
        query = text("UPDATE viaggi SET bilancio_confermato = 0 WHERE id_viaggio = :id")
        with engine.begin() as conn:
            conn.execute(query, {"id": self.id_viaggio})

    @staticmethod
    def get_partecipanti(id_viaggio):
        query = text("""
            SELECT u.nome, u.email FROM utenti u
            JOIN partecipanti p ON u.email = p.email_utente
            WHERE p.id_viaggio = :id_v
        """)
        with engine.connect() as conn:
            risultati = conn.execute(query, {"id_v": id_viaggio}).mappings().fetchall()
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
            SELECT v.*, p.ruolo_admin FROM viaggi v
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


class Tappa:
    def __init__(self, id_tappa, id_viaggio, nome_tappa, lat, lng):
        self.id_tappa = id_tappa
        self.id_viaggio = id_viaggio
        self.nome_tappa = nome_tappa
        self.lat = lat
        self.lng = lng
        
    def create(self):
        query = text("""
            INSERT INTO tappe (id_viaggio, nome_tappa, lat, lng)
            VALUES (:id_v, :nome, :lat, :lng)
        """)
        with engine.begin() as conn:
            res = conn.execute(query, {
                "id_v": self.id_viaggio, "nome": self.nome_tappa, 
                "lat": self.lat, "lng": self.lng
            })
            self.id_tappa = res.lastrowid
            
    def delete(self):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM tappe WHERE id_tappa = :id"), {"id": self.id_tappa})
            
    @staticmethod
    def get_tappe_by_viaggio(id_viaggio):
        query = text("""
            SELECT t.*, COALESCE(SUM(s.importo), 0) as totale_speso
            FROM tappe t
            LEFT JOIN spese s ON t.id_tappa = s.id_tappa
            WHERE t.id_viaggio = :id_v
            GROUP BY t.id_tappa, t.id_viaggio, t.nome_tappa, t.lat, t.lng
        """)
        with engine.connect() as conn:
            risultati = conn.execute(query, {"id_v": id_viaggio}).mappings().fetchall()
            return [dict(r) for r in risultati]

class Spesa:
    def __init__(self, id_viaggio, email_utente, testo_messaggio, importo, categoria, data_spesa, id_tappa=None):
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
        self.id_tappa = id_tappa

    def create(self):
        query = text("""
            INSERT INTO spese (id_viaggio, email_utente, testo_messaggio, importo, categoria, data_spesa, pagata, data_pagamento, id_tappa)
            VALUES (:iv, :eu, :tm, :imp, :cat, :ds, :pag, :dp, :idt)
        """)
        with engine.begin() as conn:
            res = conn.execute(query, {
                "iv": self.id_viaggio, "eu": self.email_utente, "tm": self.testo_messaggio,
                "imp": self.importo, "cat": self.categoria, "ds": self.data_spesa,
                "pag": self.pagata, "dp": self.data_pagamento, "idt": self.id_tappa
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
    def get_bilancio_completo(id_viaggio):
        """
        Ottimizzazione Pro: Recupera tutto il bilancio del viaggio e di ogni partecipante
        con solo 2 query al database.
        
        Ritorna un dizionario con:
        - info_generali: (totale_da_saldare, totale_storico, tassa, quota_a_testa)
        - partecipanti_bilancio: lista di dict con i dati di spesa di ogni utente
        """
        n_viaggiatori = Spesa.numero_viaggiatori(id_viaggio)
        if n_viaggiatori == 0:
            return "Nessun viaggiatore registrato."

        # 1. Query per i Totali del Viaggio e Stato Bilancio
        query_totali = text("""
            SELECT 
                COALESCE(SUM(importo), 0) as totale_storico,
                COALESCE(SUM(CASE WHEN pagata = 0 THEN importo ELSE 0 END), 0) as totale_da_saldare,
                (SELECT bilancio_confermato FROM viaggi WHERE id_viaggio = :id) as confermato,
                (SELECT tassa_totale FROM viaggi WHERE id_viaggio = :id) as tassa_accumulata
            FROM spese 
            WHERE id_viaggio = :id
        """)
        
        # 2. Query per il bilancio di ogni singolo partecipante (già aggregato per email)
        query_partecipanti = text("""
            SELECT 
                u.nome, u.email, p.ruolo_admin,
                COALESCE(SUM(CASE WHEN s.pagata = 0 AND s.id_viaggio = :id THEN s.importo ELSE 0 END), 0) as pagato_da_utente
            FROM utenti u
            JOIN partecipanti p ON u.email = p.email_utente
            LEFT JOIN spese s ON u.email = s.email_utente AND s.id_viaggio = :id
            WHERE p.id_viaggio = :id
            GROUP BY u.nome, u.email, p.ruolo_admin
        """)

        with engine.connect() as conn:
            totali = conn.execute(query_totali, {"id": id_viaggio}).mappings().fetchone()
            pts = conn.execute(query_partecipanti, {"id": id_viaggio}).mappings().fetchall()

        t_storico = Decimal(totali['totale_storico'] or 0)
        t_da_saldare = Decimal(totali['totale_da_saldare'] or 0)
        confermato = bool(totali['confermato'])
        tassa_totale = Decimal(totali['tassa_accumulata'] or 0)

        # La tassa individuale è la tassa totale accumulata divisa per i viaggiatori (solo se confermato)
        tassa_ind = (tassa_totale / n_viaggiatori) if n_viaggiatori > 0 and confermato else Decimal('0')
        
        quota_base = (t_da_saldare / n_viaggiatori) if n_viaggiatori > 0 else Decimal('0')
        quota_fin = round(quota_base + tassa_ind, 2)

        # Costruiamo la lista dei partecipanti con il loro netto individuale
        partecipanti_list = []
        for r in pts:
            pagato_da_r = Decimal(r['pagato_da_utente'] or 0)
            # Il netto è: quanto hai pagato - quanto avresti dovuto pagare
            netto = pagato_da_r - quota_fin
            partecipanti_list.append({
                "nome": r['nome'],
                "email": r['email'],
                "ruolo_admin": r['ruolo_admin'],
                "pagato": round(pagato_da_r, 2),
                "netto": round(netto, 2)
            })

        return {
            "info_generali": {
                "totale_da_saldare": round(t_da_saldare, 2),
                "totale_storico": round(t_storico, 2),
                "tassa_individuale": round(tassa_ind, 2),
                "tassa_totale": round(tassa_totale, 2),
                "quota_a_testa": round(quota_fin, 2),
                "confermato": confermato
            },
            "partecipanti_bilancio": partecipanti_list
        }

    @staticmethod
    def divisione_equa(id_viaggio):
        """Deprecated: Usare get_bilancio_completo per performance migliori."""
        res = Spesa.get_bilancio_completo(id_viaggio)
        return res["info_generali"] if isinstance(res, dict) else res

    @staticmethod
    def bilancio_utente_viaggio(id_viaggio, email_utente):
        """Deprecated: Usare get_bilancio_completo per caricare tutto in una volta."""
        res = Spesa.get_bilancio_completo(id_viaggio)
        if isinstance(res, str): return {"pagato": 0, "quota": 0, "netto": 0}
        
        for p in res["partecipanti_bilancio"]:
            if p["email"] == email_utente:
                return {
                    "pagato": p["pagato"],
                    "quota": res["info_generali"]["quota_a_testa"],
                    "netto": p["netto"]
                }
        return {"pagato": 0, "quota": 0, "netto": 0}

    @staticmethod
    def get_spese_per_viaggio(id_viaggio):
        query = text("""
            SELECT s.*, u.nome as nome_utente, u.email as email_utente
            FROM spese s
            JOIN utenti u ON s.email_utente = u.email
            WHERE s.id_viaggio = :id_v
            ORDER BY s.data_spesa DESC, s.id_spesa DESC
        """)
        with engine.connect() as conn:
            risultati = conn.execute(query, {"id_v": id_viaggio}).mappings().fetchall()
            return [dict(r) for r in risultati]

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
