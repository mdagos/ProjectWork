# Simulatore di Produzione Agricola

### *Progetto per il Corso di Laurea in Informatica per le Aziende Digitali (L-31)*


## Descrizione del progetto

Il presente progetto, sviluppato nell'ambito del **Project Work** del Corso di Laurea in **Informatica per le Aziende Digitali (L-31)**, ha come obiettivo la realizzazione di un simulatore di processi produttivi nel settore primario, con particolare riferimento al settore agricolo.

L'applicazione consente di simulare la produzione di tre diverse colture (grano, pomodoro e girasole) generando casualmente le quantità prodotte e calcolando i tempi di raccolta secondo due diverse sequenze operative (parallela e sequenziale). Il sistema offre un'ampia gamma di opzioni configurabili per riflettere possibili scenari produttivi, consentendo all'utente di modificare parametri quali la capacità giornaliera di raccolta, le superfici coltivate, i coefficienti climatici e l'attivazione degli eventi meteorologici.

Il simulatore è stato arricchito con:
- **Interfaccia grafica** sviluppata con Tkinter per facilitare l'interazione utente
- **Persistenza dei dati** su database SQLite per la memorizzazione permanente delle simulazioni
- **Programmazione asincrona** con asyncio per garantire la reattività dell'interfaccia
- **Analisi economica** integrata con calcolo di ricavi, costi, profitto e margine
- **Reportistica PDF** con ReportLab per l'esportazione dei risultati
- **Grafici** generati con matplotlib per la visualizzazione immediata dei risultati


## Funzionalità principali

| Funzionalità | Descrizione |
|--------------|-------------|
| **Generazione casuale delle quantità** | Le quantità prodotte vengono generate casualmente considerando resa base, superficie, coefficiente climatico, variazione percentuale ed eventi meteorologici |
| **Due sequenze produttive** | Sequenza parallela (raccolta contemporanea) e sequenziale (raccolta uno dopo l'altro) |
| **Parametri configurabili** | Capacità giornaliera, costo manodopera, superfici coltivate, coefficienti climatici, attivazione eventi meteo |
| **Analisi economica** | Calcolo di ricavi, costi di produzione, costi di manodopera, costi dei mezzi, profitto e margine |
| **Interfaccia grafica** | Organizzata in tre schede: Simulazione, Storico e Grafici |
| **Persistenza su SQLite** | Salvataggio automatico delle simulazioni su database SQLite |
| **Report PDF** | Esportazione dei risultati in formato PDF professionale |
| **Grafici** | Visualizzazione delle quantità prodotte e dell'analisi economica |


## Tecnologie utilizzate

| Tecnologia | Versione | Descrizione |
|------------|----------|-------------|
| **Python** | 3.11+ | Linguaggio di programmazione principale |
| **Tkinter** | Standard | Libreria per l'interfaccia grafica |
| **asyncio** | Standard | Libreria per la programmazione asincrona |
| **aiosqlite** | 0.19.0+ | Driver asincrono per SQLite |
| **matplotlib** | 3.7.0+ | Libreria per la generazione di grafici |
| **pandas** | 2.0.0+ | Libreria per l'elaborazione dei dati |
| **reportlab** | 4.0.0+ | Libreria per la generazione di report PDF |


## Installazione

### 1. Installazione di Python

**Windows:**
1. Scaricare Python 3.11 o superiore dal sito ufficiale: [python.org](https://www.python.org/downloads/)
2. Eseguire il file di installazione
3. **Importante:** Spuntare l'opzione "Add Python to PATH" durante l'installazione
4. Verificare l'installazione aprendo il Prompt dei Comandi e digitando:
   ```bash
   python --version
   ```

**macOS:**
```bash
brew install python@3.11
```
oppure scaricare da [python.org](https://www.python.org/downloads/)

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

### 2. Creazione dell'ambiente virtuale

L'uso di un ambiente virtuale è consigliato per isolare le dipendenze del progetto.

**Windows:**
```bash
# Navigare nella cartella del progetto
cd percorso/del/progetto

# Creare l'ambiente virtuale
python -m venv ProjectWork

# Attivare l'ambiente virtuale
venv\Scripts\activate
```

**macOS/Linux:**
```bash
# Navigare nella cartella del progetto
cd percorso/del/progetto

# Creare l'ambiente virtuale
python3 -m venv ProjectWork

# Attivare l'ambiente virtuale
source venv/bin/activate
```

### 3. Installazione delle dipendenze

Con l'ambiente virtuale attivato, installare le librerie necessarie:

```bash
pip install aiosqlite matplotlib pandas reportlab
```

**Verifica delle installazioni:**
```bash
pip list
```

Dovresti vedere le librerie installate nell'output del comando.

### 4. Creazione del file requirements.txt (opzionale)

Per facilitare la riproduzione dell'ambiente, creare un file `requirements.txt`:

```bash
pip freeze > requirements.txt
```

In futuro, per installare tutte le dipendenze:

```bash
pip install -r requirements.txt
```


## Configurazione del database

Il progetto utilizza SQLite, un database embedded che non richiede configurazioni aggiuntive. Il database verrà creato automaticamente al primo avvio dell'applicazione nella stessa cartella del progetto con il nome `simulazione_agricola.db`.

**Schema del database (creazione automatica):**

```sql
-- Tabella delle configurazioni
CREATE TABLE IF NOT EXISTS configurazioni (
    id_config INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_azienda TEXT,
    capacita_giornaliera_ore REAL,
    costo_manodopera_ora REAL,
    costo_mezzi_giorno REAL,
    eventi_meteo_attivi INTEGER,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella delle simulazioni
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
);

-- Tabella dei dettagli delle simulazioni
CREATE TABLE IF NOT EXISTS dettagli_simulazione (
    id_dett INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sim INTEGER,
    prodotto TEXT,
    quantita_t REAL,
    ore_raccolta REAL,
    giorni_raccolta REAL,
    FOREIGN KEY (id_sim) REFERENCES simulazioni(id_sim)
);
```


## Utilizzo dell'applicazione

### Avvio dell'applicazione

Con l'ambiente virtuale attivato, eseguire:

```bash
python main.py
```


### Utilizzo dell'interfaccia grafica

L'applicazione è organizzata in tre schede principali:

**1. Scheda "Simulazione"**
- Configurare i parametri di produzione (capacità giornaliera, costo manodopera, superfici coltivate)
- Attivare/disattivare gli eventi meteorologici
- Premere "Avvia Simulazione" per eseguire la simulazione
- Visualizzare i risultati in tabella e nei riepiloghi

**2. Scheda "Storico"**
- Visualizzare tutte le simulazioni salvate nel database
- Utilizzare "Aggiorna Storico" per ricaricare i dati

**3. Scheda "Grafici"**
- Visualizzare i grafici delle quantità prodotte e dell'analisi economica
- I grafici si aggiornano automaticamente dopo ogni simulazione

**Esportazione report PDF:**
- Dal menu "File" → "Esporta Report PDF"
- Scegliere la posizione e il nome del file

**Reset database:**
- Dal menu "File" → "Reset Database" per eliminare tutti i dati


## Struttura del progetto

```
simulazione_agricola/
│
├── main.py                   # File principale dell'applicazione
├── requirements.txt          # Dipendenze del progetto
├── README.md                 # Questa documentazione
│
├── simulazione_agricola.db   # Database SQLite (creato automaticamente)
│
├── report_YYYYMMDD_HHMMSS.pdf # Report PDF generati
├── grafico_YYYYMMDD_HHMMSS.png # Grafici generati
│
└── log_YYYYMMDD_HHMMSS.txt   # File di log delle operazioni
```


## 📚 Riferimenti

- **Documentazione Python:** [docs.python.org](https://docs.python.org/3/)
- **Documentazione Tkinter:** [docs.python.org/3/library/tkinter.html](https://docs.python.org/3/library/tkinter.html)
- **Documentazione asyncio:** [docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)
- **Documentazione aiosqlite:** [aiosqlite.readthedocs.io](https://aiosqlite.readthedocs.io/)
- **Documentazione matplotlib:** [matplotlib.org](https://matplotlib.org/stable/contents.html)
- **Documentazione ReportLab:** [reportlab.com/docs](https://www.reportlab.com/docs/reportlab-userguide.pdf)
