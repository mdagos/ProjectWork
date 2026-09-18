import asyncio
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import aiosqlite
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import threading
import os

# =========================================
# CLASSE RISORSA CONDIVISA
# =========================================
class RisorsaCondivisa:
    """
    Modella una risorsa condivisa con capacità limitata
    e sistema di priorità per l'allocazione tra i diversi prodotti.
    """
    def __init__(self, nome="Mezzo di raccolta", capacita_oraria=8, tempo_setup=0.5):
        self.nome = nome
        self.capacita_oraria = capacita_oraria
        self.tempo_setup = tempo_setup
        self.coda_priorita = []
        self.ultima_pianificazione = None

    def calcola_priorita(self, prodotto, quantita, prezzo, tempo_raccolta, giorni_scadenza=10):
        """
        Calcola il punteggio di priorità per un prodotto secondo valutazioni realistiche.

        Formula:
        priorità = (prezzo_vendita / tempo_raccolta_base) * fattore_deperibilità * fattore_quantità

        - prezzo_vendita / tempo_raccolta_base: valore economico per ora di utilizzo
        - fattore_deperibilità: cresce con la vicinanza alla scadenza
        - fattore_quantità: tiene conto della quantità prodotta
        """
        if tempo_raccolta <= 0:
            return 0

        valore_orario = prezzo / tempo_raccolta

        # Fattore deperibilità: più giorni rimanenti, minore urgenza
        fattore_deperibilita = 1 + (1 / (giorni_scadenza + 1))

        # Fattore quantità: logaritmico per smorzare l'effetto di grandi quantità
        fattore_quantita = 1 + (quantita / 100)

        priorita = valore_orario * fattore_deperibilita * fattore_quantita
        return round(priorita, 2)

    def assegna_risorsa(self, richieste):
        """
        Assegna la risorsa ai prodotti in base alla priorità.

        richieste: lista di tuple (prodotto, ore_necessarie, priorita)
        Restituisce un dizionario con l'ordine di esecuzione e i tempi.
        """
        # Ordina per priorità decrescente (coda di priorità)
        richieste_ordinate = sorted(richieste, key=lambda x: x[2], reverse=True)

        pianificazione = []
        tempo_totale = 0
        prodotto_precedente = None

        for prodotto, ore, priorita in richieste_ordinate:
            # Aggiungi tempo di setup se il prodotto cambia
            setup = 0
            if prodotto_precedente is not None and prodotto_precedente != prodotto:
                setup = self.tempo_setup
                tempo_totale += setup

            tempo_inizio = tempo_totale
            tempo_totale += ore

            pianificazione.append({
                "prodotto": prodotto,
                "ore_raccolta": round(ore, 2),
                "priorita": priorita,
                "setup": setup,
                "tempo_inizio": round(tempo_inizio, 2),
                "tempo_fine": round(tempo_totale, 2)
            })
            prodotto_precedente = prodotto

        risultato = {
            "pianificazione": pianificazione,
            "tempo_totale_ore": round(tempo_totale, 2),
            "giorni_necessari": round(tempo_totale / self.capacita_oraria, 2),
            "ordine_prodotti": [p["prodotto"] for p in pianificazione]
        }
        self.ultima_pianificazione = risultato
        return risultato

    def reset(self):
        """Ripristina lo stato della risorsa."""
        self.coda_priorita = []
        self.ultima_pianificazione = None


# =========================================
# CLASSE DI SIMULAZIONE
# =========================================
class ProduzioneAgricola:
    def __init__(self, nome_azienda="AgroVerde Bio"):
        self.nome_azienda = nome_azienda
        self.data_simulazione = datetime.now()
        self.prodotti = {
            "grano": {"resa_base": 6.5, "tempo_raccolta_base": 0.8, "costo_produzione": 120, "prezzo_vendita": 250},
            "pomodoro": {"resa_base": 45.0, "tempo_raccolta_base": 0.3, "costo_produzione": 80, "prezzo_vendita": 180},
            "girasole": {"resa_base": 2.8, "tempo_raccolta_base": 1.2, "costo_produzione": 150, "prezzo_vendita": 400}
        }
        self.config = {
            "superficie_ettari": {"grano": 20, "pomodoro": 15, "girasole": 15},
            "coefficiente_climatico": {"grano": 1.0, "pomodoro": 1.0, "girasole": 1.0},
            "capacita_giornaliera_ore": 8,
            "costo_orario_manodopera": 25,
            "costo_manutenzione_mezzi": 500,
            "eventi_meteo_attivi": True,
            "giorni_scadenza": {"grano": 12, "pomodoro": 5, "girasole": 8}
        }
        self.storico = []
        # Estensione: risorsa condivisa
        self.risorsa = RisorsaCondivisa()

    def genera_evento_meteo(self):
        if not self.config["eventi_meteo_attivi"]:
            return ("Normale", 1.0, "Condizioni standard")
        eventi = [
            ("Grandine", 0.7, "Perdita 30%"),
            ("Siccità", 0.6, "Perdita 40%"),
            ("Alluvione", 0.5, "Perdita 50%"),
            ("Piogge", 0.85, "Riduzione 15%"),
            ("Clima perfetto", 1.2, "Aumento 20%"),
            ("Ventoso", 0.9, "Rallentamento"),
            ("Normale", 1.0, "Standard")
        ]
        if random.random() < 0.5:
            return eventi[6]
        return random.choice(eventi[:-1])

    def genera_quantita_casuali(self, var_perc=20, evento=None):
        if evento is None:
            evento = self.genera_evento_meteo()
        tipo, fattore, desc = evento
        quantita = {}
        for p, dati in self.prodotti.items():
            resa_base = dati["resa_base"]
            sup = self.config["superficie_ettari"][p]
            coeff = self.config["coefficiente_climatico"][p]
            var = random.uniform(1 - var_perc/100, 1 + var_perc/100)
            resa = resa_base * coeff * var * fattore
            quantita[p] = round(resa * sup, 2)
        return quantita, evento

    def calcola_tempi(self, quantita):
        tempi = {}
        for p, q in quantita.items():
            ore = q * self.prodotti[p]["tempo_raccolta_base"]
            giorni = ore / self.config["capacita_giornaliera_ore"]
            tempi[p] = {"tonnellate": q, "ore_lavorative": round(ore, 2), "giorni_lavorativi": round(giorni, 2)}
        return tempi

    def calcola_economia(self, quantita, tempi):
        ricavi = sum(quantita[p] * self.prodotti[p]["prezzo_vendita"] for p in quantita)
        costi_prod = sum(quantita[p] * self.prodotti[p]["costo_produzione"] for p in quantita)
        ore_tot = sum(d["ore_lavorative"] for d in tempi.values())
        costo_mano = ore_tot * self.config["costo_orario_manodopera"]
        giorni_tot = max(d["giorni_lavorativi"] for d in tempi.values())
        costo_mezzi = giorni_tot * self.config["costo_manutenzione_mezzi"]
        costi_tot = costi_prod + costo_mano + costo_mezzi
        profitto = ricavi - costi_tot
        margine = (profitto / ricavi * 100) if ricavi > 0 else 0
        return {
            "ricavi_totali": round(ricavi, 2),
            "costi_produzione": round(costi_prod, 2),
            "costi_manodopera": round(costo_mano, 2),
            "costi_mezzi": round(costo_mezzi, 2),
            "costi_totali": round(costi_tot, 2),
            "profitto": round(profitto, 2),
            "margine_profitto": round(margine, 2)
        }

    # =========================================
    # SIMULAZIONE CON RISORSA CONDIVISA
    # =========================================
    def simula_con_risorsa(self, var_perc=20, evento=None):
        """
        Esegue la simulazione considerando una risorsa condivisa
        con allocazione basata su priorità.
        """
        if evento is None:
            evento = self.genera_evento_meteo()

        quantita, _ = self.genera_quantita_casuali(var_perc, evento)
        tempi = self.calcola_tempi(quantita)

        # Preparo le richieste per la risorsa
        richieste = []
        dettagli_priorita = []
        for prodotto, qta in quantita.items():
            ore_necessarie = qta * self.prodotti[prodotto]["tempo_raccolta_base"]
            prezzo = self.prodotti[prodotto]["prezzo_vendita"]
            tempo_base = self.prodotti[prodotto]["tempo_raccolta_base"]
            giorni_scadenza = self.config["giorni_scadenza"].get(prodotto, 10)
            priorita = self.risorsa.calcola_priorita(
                prodotto, qta, prezzo, tempo_base, giorni_scadenza
            )
            richieste.append((prodotto, ore_necessarie, priorita))
            dettagli_priorita.append({
                "prodotto": prodotto,
                "quantita": qta,
                "valore_orario": round(prezzo / tempo_base, 2),
                "giorni_scadenza": giorni_scadenza,
                "priorita": priorita
            })

        # Assegna la risorsa
        risultato_risorsa = self.risorsa.assegna_risorsa(richieste)

        # Calcolo economia basata sulle quantità totali
        economia = self.calcola_economia(quantita, tempi)

        risultato = {
            "timestamp": self.data_simulazione.isoformat(),
            "sequenza": "Risorsa Condivisa",
            "evento_meteo": evento[0],
            "fattore_evento": evento[1],
            "quantita": quantita,
            "tempi": tempi,
            "economia": economia,
            "pianificazione_risorsa": risultato_risorsa["pianificazione"],
            "tempo_totale_risorsa": risultato_risorsa["tempo_totale_ore"],
            "giorni_risorsa": risultato_risorsa["giorni_necessari"],
            "ordine_prodotti": risultato_risorsa["ordine_prodotti"],
            "dettagli_priorita": dettagli_priorita
        }
        self.storico.append(risultato)
        return risultato

    async def simula(self, sequenza="Parallela", var_perc=20):
        await asyncio.sleep(0.3)
        evento = self.genera_evento_meteo()
        quantita, _ = self.genera_quantita_casuali(var_perc, evento)
        tempi = self.calcola_tempi(quantita)
        if sequenza == "Sequenziale":
            ore_tot = sum(d["ore_lavorative"] for d in tempi.values())
        else:
            ore_tot = max(d["ore_lavorative"] for d in tempi.values())
        giorni_tot = ore_tot / self.config["capacita_giornaliera_ore"]
        economia = self.calcola_economia(quantita, tempi)
        risultato = {
            "timestamp": self.data_simulazione.isoformat(),
            "sequenza": sequenza,
            "evento_meteo": evento[0],
            "fattore_evento": evento[1],
            "quantita": quantita,
            "tempi": tempi,
            "ore_totali": ore_tot,
            "giorni_totali": round(giorni_tot, 2),
            "economia": economia
        }
        self.storico.append(risultato)
        return risultato


# =========================================
# GESTIONE DATABASE SQLITE (ASINCRONA)
# =========================================
class DatabaseManagerAsync:
    def __init__(self, db_path="simulazione_agricola.db"):
        self.db_path = db_path
        self._initialized = False

    async def _init_db(self):
        """Crea le tabelle se non esistono."""
        if self._initialized:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS configurazioni (
                    id_config INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_azienda TEXT,
                    capacita_giornaliera_ore REAL,
                    costo_manodopera_ora REAL,
                    costo_mezzi_giorno REAL,
                    eventi_meteo_attivi INTEGER,
                    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS simulazioni (
                    id_sim INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_config INTEGER,
                    sequenza TEXT,
                    evento_meteo TEXT,
                    fattore_evento REAL,
                    data_sim TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ore_totali REAL,
                    giorni_totali REAL,
                    profitto REAL,
                    margine REAL,
                    FOREIGN KEY (id_config) REFERENCES configurazioni(id_config)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS dettagli_simulazione (
                    id_dett INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_sim INTEGER,
                    prodotto TEXT,
                    quantita_t REAL,
                    ore_raccolta REAL,
                    giorni_raccolta REAL,
                    priorita REAL,
                    FOREIGN KEY (id_sim) REFERENCES simulazioni(id_sim)
                )
            """)
            await db.commit()
        self._initialized = True

    async def salva_configurazione(self, config, nome_azienda):
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO configurazioni 
                (nome_azienda, capacita_giornaliera_ore, costo_manodopera_ora, 
                 costo_mezzi_giorno, eventi_meteo_attivi)
                VALUES (?, ?, ?, ?, ?)
            """, (
                nome_azienda,
                config["capacita_giornaliera_ore"],
                config["costo_orario_manodopera"],
                config["costo_manutenzione_mezzi"],
                1 if config["eventi_meteo_attivi"] else 0
            ))
            await db.commit()
            return cursor.lastrowid

    async def salva_simulazione(self, risultato, id_config):
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            ore_totali = risultato.get("ore_totali", risultato.get("tempo_totale_risorsa", 0))
            giorni_totali = risultato.get("giorni_totali", risultato.get("giorni_risorsa", 0))
            cursor = await db.execute("""
                INSERT INTO simulazioni 
                (id_config, sequenza, evento_meteo, fattore_evento, 
                 ore_totali, giorni_totali, profitto, margine)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                id_config,
                risultato["sequenza"],
                risultato["evento_meteo"],
                risultato["fattore_evento"],
                round(ore_totali, 2),
                giorni_totali,
                risultato["economia"]["profitto"],
                risultato["economia"]["margine_profitto"]
            ))
            id_sim = cursor.lastrowid
            for prodotto, dati in risultato["tempi"].items():
                priorita = None
                for det in risultato.get("dettagli_priorita", []):
                    if det["prodotto"] == prodotto:
                        priorita = det["priorita"]
                        break
                await db.execute("""
                    INSERT INTO dettagli_simulazione 
                    (id_sim, prodotto, quantita_t, ore_raccolta, giorni_raccolta, priorita)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    id_sim, prodotto, dati["tonnellate"],
                    dati["ore_lavorative"], dati["giorni_lavorativi"],
                    priorita
                ))
            await db.commit()
            return id_sim

    async def carica_storico(self):
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT s.*, c.nome_azienda 
                FROM simulazioni s
                JOIN configurazioni c ON s.id_config = c.id_config
                ORDER BY s.data_sim DESC
            """)
            rows = await cursor.fetchall()
            if rows:
                return pd.DataFrame([dict(row) for row in rows])
            return pd.DataFrame()

    async def reset_database(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            self._initialized = False
            await self._init_db()


# =========================================
# INTERFACCIA GRAFICA
# =========================================
class AppAgricola:
    def __init__(self, root, loop):
        self.root = root
        self.loop = loop
        self.root.title("🌾 Simulatore Agricolo - SQLite con Risorsa Condivisa")
        self.root.geometry("1250x800")
        self.db = DatabaseManagerAsync()
        self.simulatore = ProduzioneAgricola()
        self.risultato_corrente = None
        self.task_simulazione = None

        # Menu
        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Esporta Report PDF", command=self.esporta_report_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="Reset Database", command=self.reset_database)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        root.config(menu=menubar)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_sim = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sim, text="Simulazione")
        self.tab_priorita = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_priorita, text="Priorità Risorsa")
        self.tab_storico = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_storico, text="Storico")
        self.tab_grafici = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_grafici, text="Grafici")

        self.build_tab_sim()
        self.build_tab_priorita()
        self.build_tab_storico()
        self.build_tab_grafici()
        self.aggiorna_storico()

    # -------------------- TAB SIMULAZIONE --------------------
    def build_tab_sim(self):
        frame = self.tab_sim

        # Frame risorsa condivisa
        risorsa_frame = ttk.LabelFrame(frame, text="Risorsa condivisa")
        risorsa_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        ttk.Label(risorsa_frame, text="Nome:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_risorsa_nome = ttk.Entry(risorsa_frame, width=15)
        self.entry_risorsa_nome.insert(0, "Mietitrebbia")
        self.entry_risorsa_nome.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(risorsa_frame, text="Capacità (ore/giorno):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_cap_risorsa = ttk.Entry(risorsa_frame, width=8)
        self.entry_cap_risorsa.insert(0, "8")
        self.entry_cap_risorsa.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(risorsa_frame, text="Setup (ore):").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.entry_setup_risorsa = ttk.Entry(risorsa_frame, width=8)
        self.entry_setup_risorsa.insert(0, "0.5")
        self.entry_setup_risorsa.grid(row=0, column=5, padx=5, pady=5)

        # Frame configurazione parametri
        cfg_frame = ttk.LabelFrame(frame, text="Parametri di configurazione")
        cfg_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        ttk.Label(cfg_frame, text="Capacità giornaliera (ore):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_cap = ttk.Entry(cfg_frame, width=10)
        self.entry_cap.insert(0, "8")
        self.entry_cap.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(cfg_frame, text="Costo manodopera (€/ora):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_mano = ttk.Entry(cfg_frame, width=10)
        self.entry_mano.insert(0, "25")
        self.entry_mano.grid(row=0, column=3, padx=5, pady=5)

        self.var_meteo = tk.BooleanVar(value=True)
        ttk.Checkbutton(cfg_frame, text="Eventi meteo attivi", variable=self.var_meteo).grid(row=0, column=4, padx=10, pady=5)

        # Superfici
        sup_frame = ttk.LabelFrame(frame, text="Superfici (ettari) e giorni scadenza")
        sup_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.entry_sup = {}
        self.entry_scadenza = {}
        prodotti = ["grano", "pomodoro", "girasole"]
        for i, p in enumerate(prodotti):
            ttk.Label(sup_frame, text=p.capitalize()+":").grid(row=i, column=0, padx=5, pady=5, sticky="w")
            e = ttk.Entry(sup_frame, width=8)
            e.insert(0, str(self.simulatore.config["superficie_ettari"][p]))
            e.grid(row=i, column=1, padx=5, pady=5)
            self.entry_sup[p] = e
            ttk.Label(sup_frame, text="gg scad:").grid(row=i, column=2, padx=2, pady=5, sticky="w")
            s = ttk.Entry(sup_frame, width=5)
            s.insert(0, str(self.simulatore.config["giorni_scadenza"][p]))
            s.grid(row=i, column=3, padx=5, pady=5)
            self.entry_scadenza[p] = s

        # Pulsanti
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, pady=10)
        self.btn_avvia = ttk.Button(btn_frame, text="Avvia Simulazione", command=self.avvia_simulazione)
        self.btn_avvia.pack(side="left", padx=10)
        self.btn_salva = ttk.Button(btn_frame, text="Salva su DB", command=self.salva_su_db)
        self.btn_salva.pack(side="left", padx=10)

        # Tabella risultati
        self.tree = ttk.Treeview(frame, columns=("Prodotto", "Quantità (t)", "Ore", "Giorni"), show="headings", height=5)
        self.tree.heading("Prodotto", text="Prodotto")
        self.tree.heading("Quantità (t)", text="Quantità (t)")
        self.tree.heading("Ore", text="Ore")
        self.tree.heading("Giorni", text="Giorni")
        self.tree.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        self.label_riepilogo = ttk.Label(frame, text="", font=("Arial", 10, "bold"))
        self.label_riepilogo.grid(row=5, column=0, pady=5)
        self.label_economia = ttk.Label(frame, text="", font=("Arial", 10))
        self.label_economia.grid(row=6, column=0, pady=5)

    # -------------------- TAB PRIORITÀ RISORSA --------------------
    def build_tab_priorita(self):
        frame = self.tab_priorita

        ttk.Label(frame, text="Pianificazione allocazione risorsa condivisa",
                  font=("Arial", 12, "bold")).pack(pady=10)

        # Tabella priorità
        self.tree_priorita = ttk.Treeview(
            frame,
            columns=("Prodotto", "Quantità (t)", "Valore orario (€/h)", "Giorni scadenza", "Priorità"),
            show="headings", height=8
        )
        self.tree_priorita.heading("Prodotto", text="Prodotto")
        self.tree_priorita.heading("Quantità (t)", text="Quantità (t)")
        self.tree_priorita.heading("Valore orario (€/h)", text="Valore orario (€/h)")
        self.tree_priorita.heading("Giorni scadenza", text="Giorni scadenza")
        self.tree_priorita.heading("Priorità", text="Priorità")
        self.tree_priorita.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Pianificazione temporale della risorsa",
                  font=("Arial", 12, "bold")).pack(pady=10)

        # Tabella pianificazione
        self.tree_pianificazione = ttk.Treeview(
            frame,
            columns=("Prodotto", "Ore", "Setup (h)", "Inizio (h)", "Fine (h)"),
            show="headings", height=5
        )
        self.tree_pianificazione.heading("Prodotto", text="Prodotto")
        self.tree_pianificazione.heading("Ore", text="Ore")
        self.tree_pianificazione.heading("Setup (h)", text="Setup (h)")
        self.tree_pianificazione.heading("Inizio (h)", text="Inizio (h)")
        self.tree_pianificazione.heading("Fine (h)", text="Fine (h)")
        self.tree_pianificazione.pack(fill="both", expand=True, padx=10, pady=10)

        self.label_risorsa = ttk.Label(frame, text="", font=("Arial", 10, "bold"))
        self.label_risorsa.pack(pady=5)

        ttk.Button(frame, text="Esegui Simulazione con Risorsa",
                   command=self.avvia_simulazione_con_risorsa).pack(pady=10)

    # -------------------- TAB STORICO --------------------
    def build_tab_storico(self):
        frame = self.tab_storico
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Aggiorna Storico", command=self.aggiorna_storico).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Reset Database", command=self.reset_database).pack(side="left", padx=5)

        self.tree_storico = ttk.Treeview(
            frame,
            columns=("ID", "Data", "Azienda", "Sequenza", "Evento", "Profitto (€)", "Margine %"),
            show="headings"
        )
        self.tree_storico.heading("ID", text="ID")
        self.tree_storico.heading("Data", text="Data")
        self.tree_storico.heading("Azienda", text="Azienda")
        self.tree_storico.heading("Sequenza", text="Sequenza")
        self.tree_storico.heading("Evento", text="Evento")
        self.tree_storico.heading("Profitto (€)", text="Profitto (€)")
        self.tree_storico.heading("Margine %", text="Margine %")
        self.tree_storico.pack(fill="both", expand=True, padx=10, pady=10)

    # -------------------- TAB GRAFICI --------------------
    def build_tab_grafici(self):
        frame = self.tab_grafici
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(11, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(frame, text="Aggiorna Grafici", command=self.aggiorna_grafici).pack(pady=5)

    # -------------------- FUNZIONI DI LOGICA --------------------
    def avvia_simulazione(self):
        try:
            cap = float(self.entry_cap.get())
            mano = float(self.entry_mano.get())
            self.simulatore.config["capacita_giornaliera_ore"] = cap
            self.simulatore.config["costo_orario_manodopera"] = mano
            self.simulatore.config["eventi_meteo_attivi"] = self.var_meteo.get()
            for p, entry in self.entry_sup.items():
                self.simulatore.config["superficie_ettari"][p] = float(entry.get())
                self.simulatore.config["giorni_scadenza"][p] = int(self.entry_scadenza[p].get())
        except ValueError:
            messagebox.showerror("Errore", "Inserisci valori numerici validi")
            return

        self.btn_avvia.config(state="disabled", text="⏳ Simulazione in corso...")
        sequenza = "Parallela" if messagebox.askyesno("Sequenza", "Usare sequenza PARALLELA?") else "Sequenziale"

        async def esegui():
            risultato = await self.simulatore.simula(sequenza=sequenza, var_perc=20)
            self.root.after(0, lambda: self._mostra_risultato(risultato))

        self.task_simulazione = asyncio.run_coroutine_threadsafe(esegui(), self.loop)

    # Simulazione con risorsa condivisa
    def avvia_simulazione_con_risorsa(self):
        try:
            # Configura risorsa
            self.simulatore.risorsa.nome = self.entry_risorsa_nome.get()
            self.simulatore.risorsa.capacita_oraria = float(self.entry_cap_risorsa.get())
            self.simulatore.risorsa.tempo_setup = float(self.entry_setup_risorsa.get())

            # Configura parametri
            self.simulatore.config["capacita_giornaliera_ore"] = float(self.entry_cap.get())
            self.simulatore.config["costo_orario_manodopera"] = float(self.entry_mano.get())
            self.simulatore.config["eventi_meteo_attivi"] = self.var_meteo.get()
            for p, entry in self.entry_sup.items():
                self.simulatore.config["superficie_ettari"][p] = float(entry.get())
                self.simulatore.config["giorni_scadenza"][p] = int(self.entry_scadenza[p].get())
        except ValueError:
            messagebox.showerror("Errore", "Inserisci valori numerici validi")
            return

        risultato = self.simulatore.simula_con_risorsa(var_perc=20)
        self.risultato_corrente = risultato

        # Popola tabella priorità
        for row in self.tree_priorita.get_children():
            self.tree_priorita.delete(row)
        for det in risultato["dettagli_priorita"]:
            self.tree_priorita.insert("", "end", values=(
                det["prodotto"].capitalize(),
                det["quantita"],
                det["valore_orario"],
                det["giorni_scadenza"],
                det["priorita"]
            ))

        # Popola tabella pianificazione
        for row in self.tree_pianificazione.get_children():
            self.tree_pianificazione.delete(row)
        for pian in risultato["pianificazione_risorsa"]:
            self.tree_pianificazione.insert("", "end", values=(
                pian["prodotto"].capitalize(),
                pian["ore_raccolta"],
                pian["setup"],
                pian["tempo_inizio"],
                pian["tempo_fine"]
            ))

        self.label_risorsa.config(text=(
            f"Ordine di priorità: {' → '.join([p.capitalize() for p in risultato['ordine_prodotti']])}\n"
            f"Tempo totale risorsa: {risultato['tempo_totale_risorsa']:.2f} ore "
            f"({risultato['giorni_risorsa']:.2f} giorni)"
        ))

        # Aggiorna anche la scheda Simulazione con i risultati
        self._mostra_risultato(risultato)
        messagebox.showinfo("Simulazione completata",
                            "Simulazione con risorsa condivisa eseguita con successo!\n"
                            "Controlla la scheda 'Priorità Risorsa' per i dettagli.")

    def _mostra_risultato(self, risultato):
        self.risultato_corrente = risultato
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p, dati in risultato["tempi"].items():
            self.tree.insert("", "end", values=(
                p.capitalize(), dati["tonnellate"],
                dati["ore_lavorative"], dati["giorni_lavorativi"]
            ))

        eco = risultato["economia"]
        ore_tot = risultato.get("ore_totali", risultato.get("tempo_totale_risorsa", 0))
        giorni_tot = risultato.get("giorni_totali", risultato.get("giorni_risorsa", 0))

        self.label_riepilogo.config(text=(
            f"Sequenza: {risultato['sequenza'].upper()} | "
            f"Evento: {risultato['evento_meteo']} | "
            f"Tempo totale: {ore_tot:.2f} ore ({giorni_tot} giorni)"
        ))
        self.label_economia.config(text=(
            f"Ricavi: {eco['ricavi_totali']:.2f} € | "
            f"Profitto: {eco['profitto']:.2f} € | "
            f"Margine: {eco['margine_profitto']:.1f}%"
        ))
        self.aggiorna_grafici()
        self.btn_avvia.config(state="normal", text="Avvia Simulazione")

    def salva_su_db(self):
        if self.risultato_corrente is None:
            messagebox.showwarning("Nessuna simulazione", "Esegui prima una simulazione")
            return

        async def do_save():
            try:
                id_config = await self.db.salva_configurazione(self.simulatore.config, self.simulatore.nome_azienda)
                id_sim = await self.db.salva_simulazione(self.risultato_corrente, id_config)
                self.root.after(0, lambda: messagebox.showinfo("Salvato", f"Simulazione salvata con ID {id_sim}"))
                self.root.after(0, self.aggiorna_storico)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Errore DB", str(e)))

        asyncio.run_coroutine_threadsafe(do_save(), self.loop)

    def aggiorna_storico(self):
        async def do_load():
            try:
                df = await self.db.carica_storico()
                self.root.after(0, lambda: self._popola_storico(df))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Errore caricamento", str(e)))

        asyncio.run_coroutine_threadsafe(do_load(), self.loop)

    def _popola_storico(self, df):
        try:
            for row in self.tree_storico.get_children():
                self.tree_storico.delete(row)
            if df.empty:
                return
            for _, row in df.iterrows():
                # Gestisce data_sim sia come stringa che come datetime
                data_sim = row["data_sim"]
                if hasattr(data_sim, 'strftime'):
                    data_str = data_sim.strftime("%d/%m/%Y %H:%M")
                else:
                    data_str = str(data_sim)

                self.tree_storico.insert("", "end", values=(
                    row["id_sim"],
                    data_str,
                    row["nome_azienda"],
                    row["sequenza"],
                    row["evento_meteo"],
                    f"{row['profitto']:.2f}" if pd.notna(row['profitto']) else "",
                    f"{row['margine']:.1f}" if pd.notna(row['margine']) else ""
                ))
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Errore popolamento storico", f"{type(e).__name__}: {str(e)}")

    def reset_database(self):
        if messagebox.askyesno("Conferma", "Eliminare tutti i dati salvati nel database?"):
            async def do_reset():
                await self.db.reset_database()
                self.root.after(0, lambda: messagebox.showinfo("Reset", "Database ripristinato"))
                self.root.after(0, self.aggiorna_storico)
            asyncio.run_coroutine_threadsafe(do_reset(), self.loop)

    def aggiorna_grafici(self):
        self.ax1.clear()
        self.ax2.clear()
        if self.risultato_corrente is None:
            self.ax1.text(0.5, 0.5, "Esegui una simulazione", ha='center', va='center', transform=self.ax1.transAxes)
            self.ax2.text(0.5, 0.5, "Esegui una simulazione", ha='center', va='center', transform=self.ax2.transAxes)
            self.canvas.draw()
            return

        prodotti = list(self.risultato_corrente["quantita"].keys())
        quantita = [self.risultato_corrente["quantita"][p] for p in prodotti]
        colori = ["#FFD700", "#FF6347", "#FFA500"]
        bars = self.ax1.bar(prodotti, quantita, color=colori, edgecolor="black")
        self.ax1.set_title("Quantità prodotte (tonnellate)")
        for bar, q in zip(bars, quantita):
            self.ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                         f"{q:.1f}", ha='center', va='bottom', fontweight='bold')

        eco = self.risultato_corrente["economia"]
        labels = ["Ricavi", "Costi", "Profitto"]
        values = [eco["ricavi_totali"], eco["costi_totali"], eco["profitto"]]
        colori2 = ["#2ECC71", "#E74C3C", "#3498DB"]
        bars2 = self.ax2.bar(labels, values, color=colori2, edgecolor="black")
        self.ax2.set_title("Analisi Economica (€)")
        for bar, v in zip(bars2, values):
            self.ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 50,
                         f"{v:.0f}", ha='center', va='bottom', fontweight='bold')
        self.canvas.draw()

    def esporta_report_pdf(self):
        if self.risultato_corrente is None:
            messagebox.showwarning("Nessuna simulazione", "Esegui prima una simulazione")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not file_path:
            return

        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Report Simulazione Produzione Agricola", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Azienda: {self.simulatore.nome_azienda}", styles["Normal"]))
        story.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Parametri di configurazione:", styles["Heading4"]))
        config_text = f"""
        Capacità giornaliera: {self.simulatore.config['capacita_giornaliera_ore']} ore<br/>
        Eventi meteo: {'Attivi' if self.simulatore.config['eventi_meteo_attivi'] else 'Disattivi'}<br/>
        Sequenza: {self.risultato_corrente['sequenza'].upper()}<br/>
        Evento meteo: {self.risultato_corrente['evento_meteo']} (x{self.risultato_corrente['fattore_evento']})
        """
        story.append(Paragraph(config_text, styles["Normal"]))
        story.append(Spacer(1, 12))

        # Tabella dettagli
        data = [["Prodotto", "Quantità (t)", "Ore", "Giorni"]]
        for p, d in self.risultato_corrente["tempi"].items():
            data.append([p.capitalize(), f"{d['tonnellate']:.2f}",
                         f"{d['ore_lavorative']:.2f}", f"{d['giorni_lavorativi']:.2f}"])
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        # Analisi economica
        eco = self.risultato_corrente["economia"]
        econ_data = [
            ["Ricavi totali", f"{eco['ricavi_totali']:.2f} €"],
            ["Costi produzione", f"{eco['costi_produzione']:.2f} €"],
            ["Costi manodopera", f"{eco['costi_manodopera']:.2f} €"],
            ["Costi mezzi", f"{eco['costi_mezzi']:.2f} €"],
            ["Costi totali", f"{eco['costi_totali']:.2f} €"],
            ["Profitto", f"{eco['profitto']:.2f} €"],
            ["Margine", f"{eco['margine_profitto']:.1f}%"]
        ]
        econ_table = Table(econ_data, colWidths=[200, 100])
        econ_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('ALIGN', (1,0), (1,-1), 'RIGHT')
        ]))
        story.append(Paragraph("Analisi Economica:", styles["Heading4"]))
        story.append(econ_table)

        # Sezione risorsa (se presente)
        if "dettagli_priorita" in self.risultato_corrente:
            story.append(Spacer(1, 12))
            story.append(Paragraph("Allocazione Risorsa Condivisa:", styles["Heading4"]))

            # Tabella priorità
            prior_data = [["Prodotto", "Quantità (t)", "Valore orario (€/h)", "Priorità"]]
            for det in self.risultato_corrente["dettagli_priorita"]:
                prior_data.append([
                    det["prodotto"].capitalize(),
                    f"{det['quantita']:.2f}",
                    f"{det['valore_orario']:.2f}",
                    f"{det['priorita']:.2f}"
                ])
            prior_table = Table(prior_data)
            prior_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            story.append(prior_table)
            story.append(Spacer(1, 6))

            # Tabella pianificazione
            pian_data = [["Prodotto", "Ore", "Setup (h)", "Inizio (h)", "Fine (h)"]]
            for pian in self.risultato_corrente["pianificazione_risorsa"]:
                pian_data.append([
                    pian["prodotto"].capitalize(),
                    f"{pian['ore_raccolta']:.2f}",
                    f"{pian['setup']:.2f}",
                    f"{pian['tempo_inizio']:.2f}",
                    f"{pian['tempo_fine']:.2f}"
                ])
            pian_table = Table(pian_data)
            pian_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkgreen),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            story.append(pian_table)

        doc.build(story)
        messagebox.showinfo("Report", f"Report salvato in {file_path}")


# =========================================
# AVVIO APPLICAZIONE
# =========================================
def run_app():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    root = tk.Tk()
    app = AppAgricola(root, loop)

    def run_loop():
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    root.mainloop()
    loop.call_soon_threadsafe(loop.stop)


if __name__ == "__main__":
    run_app()