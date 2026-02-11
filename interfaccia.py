import customtkinter as ctk
import subprocess
import threading
import os

class BilanciaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema di Pesatura Professionale")
        self.geometry("1280x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Variabile per il fattore di correzione (inizialmente 1.0)
        self.calib_factor = 1.0
        self.ultimo_peso_grezzo = 0.0 # Per memorizzare l'ultima lettura non corretta

        # UI Elements
        font_bottoni = ("Roboto", 30, "bold")

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

        # 1. Crea il contenitore (Frame) per i bottoni
        self.frame_bottoni = ctk.CTkFrame(self, fg_color="transparent") # Trasparente per non vederlo
        self.frame_bottoni.pack(pady=10)

        # 2. Crea il bottone AVVIA e mettilo nel frame (side="left")
        self.btn_start = ctk.CTkButton(self.frame_bottoni, text="AVVIA SISTEMA", command=self.start_measurement)
        self.btn_start.pack(side="left", padx=30, ipadx=20, ipady=20) # padx aggiunge spazio tra i due bottoni
        self.btn_start.configure(font=font_bottoni)

        # 3. Crea il bottone TARA e mettilo nello stesso frame (side="left")
        self.btn_tara = ctk.CTkButton(self.frame_bottoni, text="TARA", command=self.esegui_tara, fg_color="orange")
        self.btn_tara.pack(side="left", padx=30, ipadx=20, ipady=20)
        self.btn_tara.configure(font=font_bottoni)

        self.frame_calib = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_calib.pack(pady=20)

        self.entry_campione = ctk.CTkEntry(self.frame_calib, placeholder_text="Peso Kg")
        self.entry_campione.pack(side="left", padx=5, ipadx=20, ipady=30)
        self.entry_campione.bind("<Button-1>", lambda e: NumericKeypad(self, self.entry_campione))

        self.btn_calib_span = ctk.CTkButton(self.frame_calib, text="CALIBRA", 
                                           command=self.esegui_calibrazione_campione, 
                                           fg_color="green", width=100)
        self.btn_calib_span.pack(side="left", padx=5, ipadx=20, ipady=20)
        self.btn_calib_span.configure(font=font_bottoni)

# 4. Crea il bottone ESCI e mettilo nello stesso frame (side="left")
        self.btn_exit = ctk.CTkButton(self.frame_bottoni, text="ESCI", 
                                     command=self.chiudi_applicazione, 
                                     fg_color="#C0392B", hover_color="#962D22") # Rosso scuro
        self.btn_exit.pack(side="left", padx=30, ipadx=20, ipady=20)
        self.btn_exit.configure(font=font_bottoni)

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
            grammi = float(valore_str)
            kg_raw = grammi / 1000.0

        # Salviamo SEMPRE il valore grezzo (senza correzioni) 
        # per permettere ricalibrazioni successive
            self.ultimo_peso_grezzo = kg_raw

        # 1. Applichiamo il fattore di correzione calcolato col tasto
            kg_calibrati = kg_raw * self.calib_factor

        # 2. Applichiamo il taglio di 50g (0.05)
            taglio = 0.05
            kg_fissati = round(kg_calibrati / taglio) * taglio

        # Visualizzazione (usiamo max(0, ...) per evitare -0.00 se la pedana è vuota)
            testo = f"{max(0, kg_fissati):.2f} Kg"
            self.label_peso.configure(text=testo)

        except Exception as e:
            print(f"Errore update_peso: {e}")

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

    def esegui_calibrazione_campione(self):
        try:
            # Leggi il valore inserito nella Entry
            peso_campione_kg = float(self.entry_campione.get())
        
            # Evitiamo la divisione per zero se non abbiamo ancora letto nulla
            if self.ultimo_peso_grezzo == 0:
                self.label_stato.configure(text="Errore: nessuna lettura", text_color="red")
                return

            # Calcolo del nuovo fattore
            # Se leggo 19.90 e voglio 20.00: 20 / 19.90 = 1.0050...
            self.calib_factor = peso_campione_kg / self.ultimo_peso_grezzo
        
            self.label_stato.configure(text=f"Calibrazione OK! Fattore: {self.calib_factor:.4f}", text_color="green")
            
            # Opzionale: pulisci la casella di testo dopo la calibrazione
            self.entry_campione.delete(0, 'end')

        except ValueError:
            self.label_stato.configure(text="Inserire un numero valido!", text_color="red")

    def chiudi_applicazione(self):
            # 1. Se il processo C è attivo, termina il programma
            if self.process and self.process.poll() is None:
                try:
                    # Invia un comando di uscita se previsto o termina forzatamente
                    self.process.terminate() 
                    self.process.wait(timeout=1)
                except:
                    self.process.kill()

            # 2. Ripristina il terminale (utile per la tastiera del Raspberry)
            os.system("stty echo") # Forza il ripristino dell'echo del terminale
        
            # 3. Chiudi la finestra
            self.quit()
            self.destroy()

class NumericKeypad(ctk.CTkToplevel):
    def __init__(self, master, target_entry):
        super().__init__(master)
        self.title("Tastierino")
        self.geometry("280x400")
        self.target_entry = target_entry
        self.attributes('-topmost', True) # Resta sopra la finestra principale
        self.resizable(False, False)

        # Configurazione griglia
        for i in range(3): self.grid_columnconfigure(i, weight=1)

        tasti = [
            '7', '8', '9',
            '4', '5', '6',
            '1', '2', '3',
            '0', '.', 'Canc'
        ]

        r, c = 0, 0
        for tasto in tasti:
            cmd = lambda t=tasto: self.click_tasto(t)
            color = "#E74C3C" if tasto == 'Canc' else "#34495E"
            
            btn = ctk.CTkButton(self, text=tasto, width=70, height=70, 
                               font=("Roboto", 20, "bold"), fg_color=color, command=cmd)
            btn.grid(row=r, column=c, padx=5, pady=5)
            c += 1
            if c > 2:
                c = 0
                r += 1

        # Tasto Chiudi
        btn_ok = ctk.CTkButton(self, text="OK", height=50, fg_color="#2ECC71", 
                              font=("Roboto", 24, "bold"), command=self.destroy)
        btn_ok.grid(row=4, column=0, columnspan=3, sticky="we", padx=5, pady=10)

    def click_tasto(self, valore):
        if valore == 'Canc':
            self.target_entry.delete(0, 'end')
        else:
            current = self.target_entry.get()
            self.target_entry.delete(0, 'end')
            self.target_entry.insert(0, current + valore)

if __name__ == "__main__":
    app = BilanciaApp()
    app.mainloop()
