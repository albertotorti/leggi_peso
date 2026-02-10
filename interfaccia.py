import customtkinter as ctk
import subprocess
import threading
import os

class BilanciaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema di Pesatura Professionale")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # UI Elements
        self.label_titolo = ctk.CTkLabel(self, text="BILANCIA DIGITALE", font=("Roboto", 34, "bold"))
        self.label_titolo.pack(pady=20)

        self.progress_bar = ctk.CTkProgressBar(self, width=300)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.label_stato = ctk.CTkLabel(self, text="In attesa di avvio...", font=("Roboto", 24))
        self.label_stato.pack(pady=5)

        self.frame_peso = ctk.CTkFrame(self, corner_radius=15)
        self.frame_peso.pack(pady=20, padx=40, fill="both")

        self.label_peso = ctk.CTkLabel(self.frame_peso, text="--- g", font=("Roboto", 80, "bold"), text_color="#3b8ed0")
        self.label_peso.pack(pady=30)

        self.btn_start = ctk.CTkButton(self, text="AVVIA SISTEMA", command=self.start_measurement)
        self.btn_start.pack(pady=30)

        self.btn_tara = ctk.CTkButton(self, text="TARA", command=self.esegui_tara, fg_color="orange")
        self.btn_tara.pack(pady=30)

        self.process = None

    def start_measurement(self):
        self.btn_start.configure(state="disabled")
        self.label_stato.configure(text="Inizializzazione SPI...")
        # Avvia il thread per non bloccare la grafica
        thread = threading.Thread(target=self.run_c_program, daemon=True)
        thread.start()

    def run_c_program(self):
        # Lanciamo l'eseguibile C
        # Usiamo stdbuf per forzare l'output immediato senza ritardi di buffer
        cmd = ["stdbuf", "-oL", "./leggi_peso"]
        
        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, 
                                          stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            # Simula la pressione del tasto per avviare il C
            self.process.stdin.write("\n")
            self.process.stdin.flush()

            for line in self.process.stdout:
                line = line.strip()
                
                # Gestione Calibrazione
                if "CALIB:" in line:
                    step = int(line.split(":")[1])
                    self.after(0, self.update_calibration, step, step/40)                
                # Gestione Lettura Peso
                elif "PESO:" in line:
                    valore = line.split(":")[1]
                    self.after(0, self.update_peso, valore)

        except Exception as e:
            self.after(0, lambda: self.label_stato.configure(text=f"Errore: {e}"))

    def update_calibration(self, step, percent):
        self.label_stato.configure(text=f"Calibrazione in corso: {step}/40")
        self.progress_bar.set(percent)
        if step >= 40:
            self.label_stato.configure(text="Sistema Pronto", text_color="green")

    def update_peso(self, valore_str):
        try:
            # 1. Convertiamo la stringa ricevuta dal C in numero (grammi)
            grammi = float(valore_str)
        
            # 2. Convertiamo in Kg
            kg_raw = grammi / 1000.0
        
            # 3. Applichiamo il taglio di 50g (0.05 kg)
            # La logica: dividiamo per 0.05, arrotondiamo all'intero e rimoltiplichiamo per 0.05
            taglio = 0.05
            kg_fissati = round(kg_raw / taglio) * taglio
        
            # 4. Gestione dello zero e valori negativi
            # Se il peso è molto piccolo (es. 20g), il taglio lo porterà a 0.00
            if abs(kg_fissati) < 0.01: 
                kg_fissati = 0.00

            # 5. Formattazione per la GUI (sempre 2 decimali)
            testo_display = f"{kg_fissati:.2f} Kg"
        
            # Aggiornamento etichetta
            self.label_peso.configure(text=testo_display)
        
            # Opzionale: Colore rosso se il peso è negativo (sotto la tara)
            if kg_fissati < -0.04: # tolleranza prima di segnare rosso
                self.label_peso.configure(text_color="#E74C3C") # Rosso
            else:
                self.label_peso.configure(text_color="#3b8ed0") # Blu CustomTkinter
            
        except ValueError:
            # Se il C invia qualcosa di non numerico, ignoriamo l'errore
            pass

    def esegui_tara(self):
        if self.process and self.process.poll() is None:
            try:
                # Invia 't' al programma C
                self.process.stdin.write('t')
                self.process.stdin.flush()
                self.label_stato.configure(text="Ricalibrazione tara...", text_color="orange")
                self.progress_bar.set(0)
            except Exception as e:
                print(f"Errore tara: {e}")

if __name__ == "__main__":
    app = BilanciaApp()
    app.mainloop()
