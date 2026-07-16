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

# ==========================================
# CLASSE DI SIMULAZIONE
# ==========================================
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
            "eventi_meteo_attivi": True
        }
        self.storico = []

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

    async def simula(self, sequenza="parallela", var_perc=20):
        await asyncio.sleep(0.3)
        evento = self.genera_evento_meteo()
        quantita, _ = self.genera_quantita_casuali(var_perc, evento)
        tempi = self.calcola_tempi(quantita)
        if sequenza == "sequenziale":
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

# ==========================================
# GESTIONE DATABASE SQLITE (ASINCRONA)
# ==========================================
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
                round(risultato["ore_totali"], 2),
                risultato["giorni_totali"],
                risultato["economia"]["profitto"],
                risultato["economia"]["margine_profitto"]
            ))
            id_sim = cursor.lastrowid
            for prodotto, dati in risultato["tempi"].items():
                await db.execute("""
                    INSERT INTO dettagli_simulazione 
                    (id_sim, prodotto, quantita_t, ore_raccolta, giorni_raccolta)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    id_sim, prodotto, dati["tonnellate"],
                    dati["ore_lavorative"], dati["giorni_lavorativi"]
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
                data = []
                for row in rows:
                    data.append(dict(row))
                return pd.DataFrame(data)
            return pd.DataFrame()

    async def reset_database(self):
        """Ripristina il database (elimina tutti i dati)."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            self._initialized = False
            await self._init_db()

# ==========================================
# INTERFACCIA GRAFICA
# ==========================================
class AppAgricola:
    def __init__(self, root, loop):
        self.root = root
        self.loop = loop
        self.root.title("🌾 Simulatore Agricolo - SQLite")
        self.root.geometry("1200x750")
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
        self.tab_storico = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_storico, text="Storico")
        self.tab_grafici = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_grafici, text="Grafici")

        self.build_tab_sim()
        self.build_tab_storico()
        self.build_tab_grafici()

        self.aggiorna_storico()

    # -------------------- TAB SIMULAZIONE --------------------
    def build_tab_sim(self):
        frame = self.tab_sim
        cfg_frame = ttk.LabelFrame(frame, text="Parametri di configurazione")
        cfg_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

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

        sup_frame = ttk.LabelFrame(frame, text="Superfici (ettari)")
        sup_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.entry_sup = {}
        prodotti = ["grano", "pomodoro", "girasole"]
        for i, p in enumerate(prodotti):
            ttk.Label(sup_frame, text=p.capitalize()+":").grid(row=0, column=i*2, padx=5, pady=5, sticky="w")
            e = ttk.Entry(sup_frame, width=8)
            e.insert(0, str(self.simulatore.config["superficie_ettari"][p]))
            e.grid(row=0, column=i*2+1, padx=5, pady=5)
            self.entry_sup[p] = e

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, pady=15)
        self.btn_avvia = ttk.Button(btn_frame, text="Avvia Simulazione", command=self.avvia_simulazione)
        self.btn_avvia.pack(side="left", padx=10)
        self.btn_salva = ttk.Button(btn_frame, text="Salva su DB", command=self.salva_su_db)
        self.btn_salva.pack(side="left", padx=10)

        self.tree = ttk.Treeview(frame, columns=("Prodotto", "Quantità (t)", "Ore", "Giorni"), show="headings", height=5)
        self.tree.heading("Prodotto", text="Prodotto")
        self.tree.heading("Quantità (t)", text="Quantità (t)")
        self.tree.heading("Ore", text="Ore")
        self.tree.heading("Giorni", text="Giorni")
        self.tree.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.label_riepilogo = ttk.Label(frame, text="", font=("Arial", 10, "bold"))
        self.label_riepilogo.grid(row=4, column=0, pady=5)
        self.label_economia = ttk.Label(frame, text="", font=("Arial", 10))
        self.label_economia.grid(row=5, column=0, pady=5)

    # -------------------- TAB STORICO --------------------
    def build_tab_storico(self):
        frame = self.tab_storico
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Aggiorna Storico", command=self.aggiorna_storico).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Reset Database", command=self.reset_database).pack(side="left", padx=5)

        self.tree_storico = ttk.Treeview(frame, columns=("ID", "Data", "Azienda", "Sequenza", "Evento", "Profitto (€)", "Margine %"), show="headings")
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
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(10, 4))
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
        except ValueError:
            messagebox.showerror("Errore", "Inserisci valori numerici validi")
            return

        self.btn_avvia.config(state="disabled", text="Simulazione in corso...")
        sequenza = "parallela" if messagebox.askyesno("Sequenza", "Usare sequenza PARALLELA?") else "sequenziale"

        async def esegui():
            risultato = await self.simulatore.simula(sequenza=sequenza, var_perc=20)
            self.root.after(0, lambda: self._mostra_risultato(risultato))

        self.task_simulazione = asyncio.run_coroutine_threadsafe(esegui(), self.loop)

    def _mostra_risultato(self, risultato):
        self.risultato_corrente = risultato
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p, dati in risultato["tempi"].items():
            self.tree.insert("", "end", values=(p.capitalize(), dati["tonnellate"], dati["ore_lavorative"], dati["giorni_lavorativi"]))

        eco = risultato["economia"]
        self.label_riepilogo.config(text=f"📌 Sequenza: {risultato['sequenza'].upper()}  |  Evento: {risultato['evento_meteo']}  |  Tempo totale: {risultato['ore_totali']:.2f} ore ({risultato['giorni_totali']} giorni)")
        self.label_economia.config(text=f"💰 Ricavi: {eco['ricavi_totali']:.2f} €  |  Profitto: {eco['profitto']:.2f} €  |  Margine: {eco['margine_profitto']:.1f}%")
        self.aggiorna_grafici()
        self.btn_avvia.config(state="normal", text="▶ Avvia Simulazione")

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
        for row in self.tree_storico.get_children():
            self.tree_storico.delete(row)
        if df.empty:
            return
        for _, row in df.iterrows():
            self.tree_storico.insert("", "end", values=(
                row["id_sim"],
                row["data_sim"].strftime("%d/%m/%Y %H:%M"),
                row["nome_azienda"],
                row["sequenza"],
                row["evento_meteo"],
                f"{row['profitto']:.2f}",
                f"{row['margine']:.1f}"
            ))

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
            self.ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5, f"{q:.1f}", ha='center', va='bottom', fontweight='bold')

        eco = self.risultato_corrente["economia"]
        labels = ["Ricavi", "Costi", "Profitto"]
        values = [eco["ricavi_totali"], eco["costi_totali"], eco["profitto"]]
        colori2 = ["#2ECC71", "#E74C3C", "#3498DB"]
        bars2 = self.ax2.bar(labels, values, color=colori2, edgecolor="black")
        self.ax2.set_title("Analisi Economica (€)")
        for bar, v in zip(bars2, values):
            self.ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 50, f"{v:.0f}", ha='center', va='bottom', fontweight='bold')
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

        data = [["Prodotto", "Quantità (t)", "Ore", "Giorni"]]
        for p, d in self.risultato_corrente["tempi"].items():
            data.append([p.capitalize(), f"{d['tonnellate']:.2f}", f"{d['ore_lavorative']:.2f}", f"{d['giorni_lavorativi']:.2f}"])
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

        doc.build(story)
        messagebox.showinfo("Report", f"Report salvato in {file_path}")

# ==========================================
# AVVIO APPLICAZIONE
# ==========================================
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