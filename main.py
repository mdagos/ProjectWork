import random
#import numpy as np

class ProduzioneAgricola:
    def __init__(self):
        # Prodotti: nome, resa_base (tonnellate/ettaro), tempo_raccolta_base (ore/tonnellata)
        self.prodotti = {
            "grano": {"resa_base": 6.5, "tempo_raccolta_base": 0.8},
            "pomodoro": {"resa_base": 45.0, "tempo_raccolta_base": 0.3},
            "girasole": {"resa_base": 2.8, "tempo_raccolta_base": 1.2}
        }
        
        # Configurazioni personalizzabili
        self.config = {
            "superficie_ettari": {"grano": 20, "pomodoro": 15, "girasole": 15},
            "coefficiente_climatico": {"grano": 1.0, "pomodoro": 1.0, "girasole": 1.0},
            "capacita_giornaliera_ore": 8  # ore di raccolta al giorno
        }
    
    def genera_quantita_casuali(self, variazione_percentuale=20):
        """
        Genera casualmente le quantità effettive prodotte (tonnellate)
        sulla base della resa base e della superficie coltivata.
        """
        quantita = {}
        for prodotto, dati in self.prodotti.items():
            resa_base = dati["resa_base"]
            superficie = self.config["superficie_ettari"][prodotto]
            coeff_climatico = self.config["coefficiente_climatico"][prodotto]
            
            # Resa effettiva con variazione casuale
            variazione = random.uniform(1 - variazione_percentuale/100, 
                                        1 + variazione_percentuale/100)
            resa_effettiva = resa_base * coeff_climatico * variazione
            
            quantita[prodotto] = round(resa_effettiva * superficie, 2)
        
        return quantita
    
    def configura_parametri(self, prodotto=None, ore_capacita=None, 
                            coefficiente_clim=None, superficie=None):
        """Permette di configurare i parametri di produzione."""
        if ore_capacita:
            self.config["capacita_giornaliera_ore"] = ore_capacita
        if prodotto and coefficiente_clim:
            self.config["coefficiente_climatico"][prodotto] = coefficiente_clim
        if prodotto and superficie:
            self.config["superficie_ettari"][prodotto] = superficie
    
    def calcola_tempi_produzione(self, quantita):
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
    
    def simula_produzione(self, sequenza_produttiva="parallela", variazione_percentuale=20):
        """
        Simula l'intero processo produttivo.
        sequenza_produttiva: "parallela" (contemporanea) o "sequenziale" (uno dopo l'altro)
        """
        print("\n" + "="*60)
        print("SIMULAZIONE PRODUZIONE AGRICOLA - AgroVerde Bio")
        print("="*60)
        
        # Fase 1: generazione casuale delle quantità prodotte
        quantita = self.genera_quantita_casuali(variazione_percentuale)
        
        print("\n[1] QUANTITÀ PRODOTTE (tonnellate):")
        for p, q in quantita.items():
            print(f"   {p.capitalize()}: {q} t")
        
        # Fase 2: calcolo tempi individuali
        tempi = self.calcola_tempi_produzione(quantita)
        
        print("\n[2] TEMPI DI RACCOLTA INDIVIDUALI:")
        for prodotto, dati in tempi.items():
            print(f"   {prodotto.capitalize()}: {dati['ore_lavorative']} ore ({dati['giorni_lavorativi']} giorni)")
        
        # Fase 3: tempo complessivo in base alla sequenza produttiva
        print(f"\n[3] SEQUENZA PRODUTTIVA: {sequenza_produttiva.upper()}")
        
        if sequenza_produttiva == "sequenziale":
            # Somma dei tempi (un prodotto dopo l'altro)
            ore_totali = sum(d["ore_lavorative"] for d in tempi.values())
            giorni_totali = ore_totali / self.config["capacita_giornaliera_ore"]
            print(f"   Tempo complessivo: {ore_totali} ore ({round(giorni_totali, 2)} giorni)")
            print("   (Raccolta eseguita in sequenza: grano → pomodoro → girasole)")
        
        elif sequenza_produttiva == "parallela":
            # Tempo massimo (raccolta in parallelo con risorse divise)
            ore_max = max(d["ore_lavorative"] for d in tempi.values())
            giorni_totali = ore_max / self.config["capacita_giornaliera_ore"]
            print(f"   Tempo complessivo: {ore_max} ore ({round(giorni_totali, 2)} giorni)")
            print("   (Raccolta in parallelo su campi diversi)")
        
        else:
            raise ValueError("Sequenza produttiva non valida. Usare 'parallela' o 'sequenziale'")
        
        return quantita, tempi

# ========== ESEMPIO DI UTILIZZO ==========
if __name__ == "__main__":
    # Inizializzazione azienda
    azienda = ProduzioneAgricola()
    
    # Configurazione personalizzata (es. cambio capacità operativa)
    print("Configurazione iniziale:")
    print(f"Capacità giornaliera: {azienda.config['capacita_giornaliera_ore']} ore")
    
    # Modifica parametri (es. clima sfavorevole per pomodori)
    azienda.configura_parametri(prodotto="pomodoro", coefficiente_clim=0.85)
    azienda.configura_parametri(ore_capacita=10)  # aumento ore disponibili
    
    print("\nNuova configurazione applicata:")
    print(f"Capacità giornaliera: {azienda.config['capacita_giornaliera_ore']} ore")
    print(f"Coefficiente climatico pomodoro: {azienda.config['coefficiente_climatico']['pomodoro']}")
    
    # Simulazione con sequenza parallela
    azienda.simula_produzione(sequenza_produttiva="parallela", variazione_percentuale=15)
    
    # Simulazione con sequenza sequenziale
    azienda.simula_produzione(sequenza_produttiva="sequenziale", variazione_percentuale=15)