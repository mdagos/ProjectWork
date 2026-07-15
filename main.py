import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import os
from typing import Dict, Tuple, List, Optional

class ProduzioneAgricolaAvanzata:
    def __init__(self, nome_azienda: str = "AgroVerde Bio"):
        self.nome_azienda = nome_azienda
        self.data_simulazione = datetime.now()
        
        # Prodotti: nome, resa_base (t/ettaro), tempo_raccolta_base (ore/t), 
        # costo_produzione (€/t), prezzo_vendita (€/t)
        self.prodotti = {
            "grano": {
                "resa_base": 6.5,
                "tempo_raccolta_base": 0.8,
                "costo_produzione": 120,  # €/tonnellata
                "prezzo_vendita": 250,    # €/tonnellata
                "colore": "#FFD700"
            },
            "pomodoro": {
                "resa_base": 45.0,
                "tempo_raccolta_base": 0.3,
                "costo_produzione": 80,
                "prezzo_vendita": 180,
                "colore": "#FF6347"
            },
            "girasole": {
                "resa_base": 2.8,
                "tempo_raccolta_base": 1.2,
                "costo_produzione": 150,
                "prezzo_vendita": 400,
                "colore": "#FFD700"
            }
        }
        
        # Configurazioni personalizzabili
        self.config = {
            "superficie_ettari": {"grano": 20, "pomodoro": 15, "girasole": 15},
            "coefficiente_climatico": {"grano": 1.0, "pomodoro": 1.0, "girasole": 1.0},
            "capacita_giornaliera_ore": 8,  # ore di raccolta al giorno
            "costo_orario_manodopera": 25,  # €/ora
            "costo_manutenzione_mezzi": 500,  # €/giorno
            "eventi_meteo_attivi": True
        }
        
        # Storico simulazioni
        self.storico_simulazioni = []
        
        # Logger
        self.log_file = f"log_{self.data_simulazione.strftime('%Y%m%d_%H%M%S')}.txt"
        
    def log(self, messaggio: str):
        """Registra un evento nel file di log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {messaggio}\n")
        print(messaggio)
    
    def genera_evento_meteo(self) -> Tuple[str, float, str]:
        """
        Genera un evento meteorologico casuale che influisce sulla produzione.
        Restituisce: (tipo_evento, fattore_moltiplicativo_rese, descrizione)
        """
        if not self.config["eventi_meteo_attivi"]:
            return ("Normale", 1.0, "Condizioni climatiche standard")
        
        eventi = [
            ("Grandine", 0.7, "Grandine: perdita del 30% della produzione"),
            ("Siccità", 0.6, "Siccità: perdita del 40% della produzione"),
            ("Alluvione", 0.5, "Alluvione: perdita del 50% della produzione"),
            ("Piogge abbondanti", 0.85, "Piogge: lieve riduzione della resa"),
            ("Clima perfetto", 1.2, "Clima ottimale: aumento della resa del 20%"),
            ("Ventoso", 0.9, "Venti forti: rallentamento raccolta"),
            ("Normale", 1.0, "Condizioni climatiche standard")
        ]
        
        # Probabilità evento: 40% di avere un evento non normale
        if random.random() < 0.6:
            return eventi[6]  # Normale
        else:
            evento = random.choice(eventi[:-1])  # esclude l'ultimo (Normale)
            return evento
    
    def genera_quantita_casuali(self, variazione_percentuale: float = 20, 
                                 evento_meteo: Optional[Tuple] = None) -> Dict:
        """
        Genera casualmente le quantità effettive prodotte (tonnellate)
        Considerando anche eventi meteorologici.
        """
        if evento_meteo is None:
            evento_meteo = self.genera_evento_meteo()
        
        tipo_evento, fattore_evento, desc_evento = evento_meteo
        
        quantita = {}
        for prodotto, dati in self.prodotti.items():
            resa_base = dati["resa_base"]
            superficie = self.config["superficie_ettari"][prodotto]
            coeff_climatico = self.config["coefficiente_climatico"][prodotto]
            
            # Variazione casuale della resa
            variazione = random.uniform(1 - variazione_percentuale/100, 
                                        1 + variazione_percentuale/100)
            
            # Resa effettiva con evento meteo
            resa_effettiva = resa_base * coeff_climatico * variazione * fattore_evento
            
            quantita[prodotto] = round(resa_effettiva * superficie, 2)
        
        return quantita, evento_meteo
    
    def configura_parametri(self, prodotto: Optional[str] = None, 
                           ore_capacita: Optional[float] = None, 
                           coefficiente_clim: Optional[float] = None, 
                           superficie: Optional[float] = None,
                           costo_manodopera: Optional[float] = None,
                           eventi_meteo: Optional[bool] = None):
        """Permette di configurare i parametri di produzione."""
        if ore_capacita:
            self.config["capacita_giornaliera_ore"] = ore_capacita
            self.log(f"Capacità giornaliera impostata a {ore_capacita} ore")
        
        if costo_manodopera:
            self.config["costo_orario_manodopera"] = costo_manodopera
            self.log(f"Costo manodopera impostato a {costo_manodopera} €/ora")
        
        if eventi_meteo is not None:
            self.config["eventi_meteo_attivi"] = eventi_meteo
            self.log(f"Eventi meteorologici: {'Attivi' if eventi_meteo else 'Disattivi'}")
        
        if prodotto and coefficiente_clim:
            self.config["coefficiente_climatico"][prodotto] = coefficiente_clim
            self.log(f"Coefficiente climatico per {prodotto} impostato a {coefficiente_clim}")
        
        if prodotto and superficie:
            self.config["superficie_ettari"][prodotto] = superficie
            self.log(f"Superficie per {prodotto} impostata a {superficie} ettari")
    
    def calcola_tempi_produzione(self, quantita: Dict) -> Dict:
        """Calcola il tempo totale di raccolta per ogni prodotto."""
        tempi = {}
        for prodotto, qta in quantita.items():
            tempo_base = self.prodotti[prodotto]["tempo_raccolta_base"]
            ore_totali = qta * tempo_base
            giorni_totali = ore_totali / self.config["capacita_giornaliera_ore"]
            tempi[prodotto] = {
                "tonnellate": qta,
                "ore_lavorative": round(ore_totali, 2),
                "giorni_lavorativi": round(giorni_totali, 2)
            }
        return tempi
    
    def calcola_analisi_economica(self, quantita: Dict, tempi: Dict, 
                                  sequenza: str) -> Dict:
        """Calcola costi, ricavi e profitti."""
        # Ricavi totali
        ricavi_totali = 0
        for prodotto, qta in quantita.items():
            ricavi_totali += qta * self.prodotti[prodotto]["prezzo_vendita"]
        
        # Costi produzione (variabili)
        costi_produzione = 0
        for prodotto, qta in quantita.items():
            costi_produzione += qta * self.prodotti[prodotto]["costo_produzione"]
        
        # Costi manodopera
        ore_totali = sum(d["ore_lavorative"] for d in tempi.values())
        costi_manodopera = ore_totali * self.config["costo_orario_manodopera"]
        
        # Costi mezzi
        giorni_totali = max(d["giorni_lavorativi"] for d in tempi.values())
        costi_mezzi = giorni_totali * self.config["costo_manutenzione_mezzi"]
        
        # Costi totali e profitto
        costi_totali = costi_produzione + costi_manodopera + costi_mezzi
        profitto = ricavi_totali - costi_totali
        margine_profitto = (profitto / ricavi_totali) * 100 if ricavi_totali > 0 else 0
        
        return {
            "ricavi_totali": round(ricavi_totali, 2),
            "costi_produzione": round(costi_produzione, 2),
            "costi_manodopera": round(costi_manodopera, 2),
            "costi_mezzi": round(costi_mezzi, 2),
            "costi_totali": round(costi_totali, 2),
            "profitto": round(profitto, 2),
            "margine_profitto": round(margine_profitto, 2)
        }
    
    def simula_produzione(self, sequenza_produttiva: str = "parallela", 
                         variazione_percentuale: float = 20,
                         salva_csv: bool = True,
                         genera_grafico: bool = True) -> Dict:
        """
        Simula l'intero processo produttivo.
        sequenza_produttiva: "parallela" (contemporanea) o "sequenziale" (uno dopo l'altro)
        """
        print("\n" + "="*70)
        print(f"SIMULAZIONE PRODUZIONE AGRICOLA - {self.nome_azienda}")
        print(f"Data: {self.data_simulazione.strftime('%d/%m/%Y %H:%M:%S')}")
        print("="*70)
        
        # Fase 1: Evento meteorologico (se attivo)
        evento_meteo = None
        if self.config["eventi_meteo_attivi"]:
            evento_meteo = self.genera_evento_meteo()
            print(f"\n EVENTO METEOROLOGICO: {evento_meteo[0].upper()}")
            print(f"   {evento_meteo[2]}")
            print(f"   Fattore su rese: {evento_meteo[1]}")
        else:
            print("\n Eventi meteorologici: DISATTIVI")
        
        # Fase 2: generazione casuale delle quantità prodotte
        quantita, evento_meteo = self.genera_quantita_casuali(variazione_percentuale, evento_meteo)
        
        print("\n [1] QUANTITÀ PRODOTTE (tonnellate):")
        for p, q in quantita.items():
            print(f"   {p.capitalize()}: {q} t")
        
        # Fase 3: calcolo tempi individuali
        tempi = self.calcola_tempi_produzione(quantita)
        
        print("\n [2] TEMPI DI RACCOLTA INDIVIDUALI:")
        for prodotto, dati in tempi.items():
            print(f"   {prodotto.capitalize()}: {dati['ore_lavorative']} ore ({dati['giorni_lavorativi']} giorni)")
        
        # Fase 4: tempo complessivo in base alla sequenza produttiva
        print(f"\n [3] SEQUENZA PRODUTTIVA: {sequenza_produttiva.upper()}")
        
        if sequenza_produttiva == "sequenziale":
            ore_totali = sum(d["ore_lavorative"] for d in tempi.values())
            giorni_totali = ore_totali / self.config["capacita_giornaliera_ore"]
            print(f"   Tempo complessivo: {ore_totali} ore ({round(giorni_totali, 2)} giorni)")
            print("   (Raccolta in sequenza: grano → pomodoro → girasole)")
        
        elif sequenza_produttiva == "parallela":
            ore_max = max(d["ore_lavorative"] for d in tempi.values())
            giorni_totali = ore_max / self.config["capacita_giornaliera_ore"]
            print(f"   Tempo complessivo: {ore_max} ore ({round(giorni_totali, 2)} giorni)")
            print("   (Raccolta in parallelo su campi diversi)")
        
        else:
            raise ValueError("Sequenza produttiva non valida. Usare 'parallela' o 'sequenziale'")
        
        # Fase 5: Analisi economica
        print("\n [4] ANALISI ECONOMICA:")
        economia = self.calcola_analisi_economica(quantita, tempi, sequenza_produttiva)
        print(f"   Ricavi totali:     {economia['ricavi_totali']:,.2f} €")
        print(f"   Costi produzione:  {economia['costi_produzione']:,.2f} €")
        print(f"   Costi manodopera:  {economia['costi_manodopera']:,.2f} €")
        print(f"   Costi mezzi:       {economia['costi_mezzi']:,.2f} €")
        print(f"   Costi totali:      {economia['costi_totali']:,.2f} €")
        print(f"   Profitto:        {economia['profitto']:,.2f} €")
        print(f"   Margine:           {economia['margine_profitto']:.1f}%")
        
        # Salva risultato
        risultato = {
            "timestamp": self.data_simulazione.isoformat(),
            "sequenza": sequenza_produttiva,
            "evento_meteo": evento_meteo[0] if evento_meteo else "Nessuno",
            "fattore_evento": evento_meteo[1] if evento_meteo else 1.0,
            "quantita": quantita,
            "tempi": tempi,
            "ore_totali": ore_totali if sequenza_produttiva == "sequenziale" else ore_max,
            "giorni_totali": giorni_totali,
            "economia": economia
        }
        
        self.storico_simulazioni.append(risultato)
        
        # Salva su CSV
        if salva_csv:
            self.salva_su_csv(risultato)
        
        # Genera grafico
        if genera_grafico:
            self.genera_grafico_produzione(risultato)
        
        self.log(f"Simulazione completata: {sequenza_produttiva}, profitto: {economia['profitto']:.2f}€")
        
        return risultato
    
    def salva_su_csv(self, risultato: Dict):
        """Salva i risultati in un file CSV."""
        filename = f"report_{self.data_simulazione.strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Prepara dati per CSV
        data = []
        for prodotto, qta in risultato["quantita"].items():
            data.append({
                "Timestamp": risultato["timestamp"],
                "Azienda": self.nome_azienda,
                "Sequenza": risultato["sequenza"],
                "Evento_meteo": risultato["evento_meteo"],
                "Prodotto": prodotto,
                "Quantita_t": qta,
                "Ore_raccolta": risultato["tempi"][prodotto]["ore_lavorative"],
                "Giorni_raccolta": risultato["tempi"][prodotto]["giorni_lavorativi"],
                "Tempo_totale_giorni": risultato["giorni_totali"],
                "Ricavi_euro": risultato["economia"]["ricavi_totali"],
                "Costi_totali_euro": risultato["economia"]["costi_totali"],
                "Profitto_euro": risultato["economia"]["profitto"],
                "Margine_percentuale": risultato["economia"]["margine_profitto"]
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding="utf-8")
        print(f"\n Report salvato in: {filename}")
    
    def genera_grafico_produzione(self, risultato: Dict):
        """Genera un grafico a barre della produzione."""
        prodotti = list(risultato["quantita"].keys())
        quantita = list(risultato["quantita"].values())
        colori = [self.prodotti[p]["colore"] for p in prodotti]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Grafico 1: Quantità prodotte
        bars = ax1.bar(prodotti, quantita, color=colori, edgecolor="black")
        ax1.set_title(f"Produzione {self.nome_azienda}\nEvento: {risultato['evento_meteo']}")
        ax1.set_xlabel("Prodotto")
        ax1.set_ylabel("Quantità (tonnellate)")
        
        # Aggiungi valori sulle barre
        for bar, q in zip(bars, quantita):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{q:.1f} t', ha='center', va='bottom', fontweight='bold')
        
        # Grafico 2: Analisi economica
        economia = risultato["economia"]
        labels = ["Ricavi", "Costi\nTotali", "Profitto"]
        values = [economia["ricavi_totali"], economia["costi_totali"], economia["profitto"]]
        colors_bar = ["#2ECC71", "#E74C3C", "#3498DB"]
        
        bars2 = ax2.bar(labels, values, color=colors_bar, edgecolor="black")
        ax2.set_title(f"Analisi Economica\nMargine: {economia['margine_profitto']:.1f}%")
        ax2.set_ylabel("Euro (€)")
        
        # Aggiungi valori
        for bar, v in zip(bars2, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1000,
                    f'€{v:,.0f}', ha='center', va='bottom', fontweight='bold')
        
        plt.suptitle(f"Simulazione Produzione - {risultato['sequenza'].upper()}", fontsize=14, fontweight="bold")
        plt.tight_layout()
        
        filename = f"grafico_{self.data_simulazione.strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f" Grafico salvato in: {filename}")
        plt.show()
    
    def report_completo(self):
        """Genera un report completo di tutte le simulazioni."""
        if not self.storico_simulazioni:
            print("Nessuna simulazione disponibile.")
            return
        
        print("\n" + "="*70)
        print("REPORT COMPLETO STORICO SIMULAZIONI")
        print("="*70)
        
        for i, sim in enumerate(self.storico_simulazioni, 1):
            print(f"\n Simulazione {i}:")
            print(f"   Data: {sim['timestamp']}")
            print(f"   Sequenza: {sim['sequenza'].upper()}")
            print(f"   Evento meteo: {sim['evento_meteo']} (x{sim['fattore_evento']})")
            print(f"   Profitto: {sim['economia']['profitto']:,.2f} €")
            print(f"   Margine: {sim['economia']['margine_profitto']:.1f}%")
        
        # Statistiche riassuntive
        profitti = [sim["economia"]["profitto"] for sim in self.storico_simulazioni]
        print(f"\n STATISTICHE:")
        print(f"   Profitto medio: {np.mean(profitti):,.2f} €")
        print(f"   Profitto max: {max(profitti):,.2f} €")
        print(f"   Profitto min: {min(profitti):,.2f} €")
        print(f"   Deviazione std: {np.std(profitti):,.2f} €")

# ========== INTERFACCIA INTERATTIVA A MENU ==========
def menu_interattivo():
    print("="*60)
    print("SIMULATORE PRODUZIONE AGRICOLA")
    print("="*60)
    
    nome = input("\nInserisci nome azienda (default: AgroVerde Bio): ").strip()
    if not nome:
        nome = "AgroVerde Bio"
    
    azienda = ProduzioneAgricolaAvanzata(nome)
    
    while True:
        print("\n" + "-"*40)
        print("MENU PRINCIPALE")
        print("-"*40)
        print("1.  Simula produzione (configurazione attuale)")
        print("2.  Configura parametri produzione")
        print("3.  Visualizza storico simulazioni")
        print("4.  Esporta report completo")
        print("5.  Attiva/Disattiva eventi meteo")
        print("6.  Esegui simulazione multipla")
        print("7.  Esci")
        
        scelta = input("\nScegli un'opzione (1-7): ").strip()
        
        if scelta == "1":
            print("\n Scegli sequenza produttiva:")
            print("1. Parallela (raccolta contemporanea)")
            print("2. Sequenziale (un prodotto dopo l'altro)")
            seq_choice = input("Opzione (default 1): ").strip()
            sequenza = "parallela" if seq_choice != "2" else "sequenziale"
            
            azienda.simula_produzione(sequenza_produttiva=sequenza, 
                                     salva_csv=True, 
                                     genera_grafico=True)
            
            input("\nPremi INVIO per continuare...")
        
        elif scelta == "2":
            print("\n CONFIGURAZIONE PARAMETRI")
            print("1. Modifica capacità giornaliera (ore)")
            print("2. Modifica costo manodopera (€/ora)")
            print("3. Modifica superficie coltivata")
            print("4. Modifica coefficiente climatico")
            print("5. Torna indietro")
            
            sub_scelta = input("\nScelta: ").strip()
            
            if sub_scelta == "1":
                ore = float(input("Capacità giornaliera (ore, default 8): ") or 8)
                azienda.configura_parametri(ore_capacita=ore)
            
            elif sub_scelta == "2":
                costo = float(input("Costo manodopera (€/ora, default 25): ") or 25)
                azienda.configura_parametri(costo_manodopera=costo)
            
            elif sub_scelta == "3":
                print("\nProdotti disponibili: grano, pomodoro, girasole")
                prodotto = input("Prodotto: ").lower()
                if prodotto in azienda.prodotti:
                    ettari = float(input(f"Ettari per {prodotto} (attuale {azienda.config['superficie_ettari'][prodotto]}): "))
                    azienda.configura_parametri(prodotto=prodotto, superficie=ettari)
                else:
                    print("Prodotto non valido!")
            
            elif sub_scelta == "4":
                print("\nProdotti disponibili: grano, pomodoro, girasole")
                prodotto = input("Prodotto: ").lower()
                if prodotto in azienda.prodotti:
                    coeff = float(input(f"Coefficiente climatico per {prodotto} (attuale {azienda.config['coefficiente_climatico'][prodotto]}): "))
                    azienda.configura_parametri(prodotto=prodotto, coefficiente_clim=coeff)
                else:
                    print("Prodotto non valido!")
        
        elif scelta == "3":
            azienda.report_completo()
            input("\nPremi INVIO per continuare...")
        
        elif scelta == "4":
            if azienda.storico_simulazioni:
                # Salva tutto lo storico in un unico CSV
                df_list = []
                for sim in azienda.storico_simulazioni:
                    for prodotto, qta in sim["quantita"].items():
                        df_list.append({
                            "Timestamp": sim["timestamp"],
                            "Sequenza": sim["sequenza"],
                            "Evento_meteo": sim["evento_meteo"],
                            "Prodotto": prodotto,
                            "Quantita_t": qta,
                            "Profitto_euro": sim["economia"]["profitto"]
                        })
                df = pd.DataFrame(df_list)
                filename = f"storico_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(filename, index=False, encoding="utf-8")
                print(f"\nStorico salvato in: {filename}")
            else:
                print("Nessuna simulazione da esportare.")
            input("\nPremi INVIO per continuare...")
        
        elif scelta == "5":
            stato = not azienda.config["eventi_meteo_attivi"]
            azienda.configura_parametri(eventi_meteo=stato)
            print(f"Eventi meteo: {'ATTIVI' if stato else 'DISATTIVI'}")
            input("\nPremi INVIO per continuare...")
        
        elif scelta == "6":
            print("\nSIMULAZIONE MULTIPLA")
            n_sim = int(input("Numero di simulazioni da eseguire (1-100): ") or 5)
            n_sim = min(max(n_sim, 1), 100)
            
            print("\nScegli sequenza produttiva per tutte le simulazioni:")
            print("1. Parallela")
            print("2. Sequenziale")
            seq_choice = input("Opzione (default 1): ").strip()
            sequenza = "parallela" if seq_choice != "2" else "sequenziale"
            
            profitti = []
            for i in range(n_sim):
                print(f"\n--- Simulazione {i+1}/{n_sim} ---")
                risultato = azienda.simula_produzione(sequenza_produttiva=sequenza, 
                                                     salva_csv=False, 
                                                     genera_grafico=False)
                profitti.append(risultato["economia"]["profitto"])
            
            print("\n" + "="*50)
            print(f"RISULTATI SIMULAZIONE MULTIPLA ({n_sim} simulazioni)")
            print("="*50)
            print(f"Profitto medio:     {np.mean(profitti):,.2f} €")
            print(f"Profitto mediano:   {np.median(profitti):,.2f} €")
            print(f"Profitto massimo:   {max(profitti):,.2f} €")
            print(f"Profitto minimo:    {min(profitti):,.2f} €")
            print(f"Deviazione std:     {np.std(profitti):,.2f} €")
            
            # Istogramma dei profitti
            plt.figure(figsize=(10, 6))
            plt.hist(profitti, bins=15, color="green", edgecolor="black", alpha=0.7)
            plt.xlabel("Profitto (€)")
            plt.ylabel("Frequenza")
            plt.title(f"Distribuzione Profitti - {n_sim} Simulazioni")
            plt.axvline(np.mean(profitti), color="red", linestyle="--", label=f"Media: {np.mean(profitti):,.0f}€")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f"istogramma_profitti_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png", dpi=300)
            plt.show()
            
            input("\nPremi INVIO per continuare...")
        
        elif scelta == "7":
            print("\nGrazie per aver usato il simulatore. Arrivederci!")
            break
        
        else:
            print("Opzione non valida! Riprova.")

# ========== ESECUZIONE ==========
if __name__ == "__main__":
    menu_interattivo()