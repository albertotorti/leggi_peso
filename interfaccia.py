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

        self.ultimo_raw = 0.0
        self.scala_default = 0.025412960609911054
        self.scala = self.scala_default

        # Carichiamo la calibrazione prima di creare la UI
        self.carica_calibrazione()

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

        self.label_peso = ctk.CTkLabel(self.frame_peso, text="--- Kg", font=("Roboto", 80, "bold"), text_color="#3b8ed0")
        self.label_peso.pack(pady=30)

        self.frame_bottoni = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_bottoni.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.frame_bottoni, text="AVVIA SISTEMA", command=self.start_measurement)
        self.btn_start.pack(side="left", padx=30, ipadx=20, ipady=20)
        self.btn_start.configure(font=font_bottoni)

        self.btn_tara = ctk.CTkButton(self.frame_bottoni, text="TARA", command=self.esegui_tara, fg_color="orange")
        self.btn_tara.pack(side="left", padx=30, ipadx=20, ipady=20)
        self.btn_tara.configure(font=font_bottoni)

        self.btn_exit = ctk.CTkButton(self.frame_bottoni, text="ESCI", command=self.chiudi_applicazione, fg_color="#C0392B")
        self.btn_exit.pack(side="left", padx=30, ipadx=20, ipady=20)
        self.btn_exit.configure(font=font_bottoni)

        self.frame_calib = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_calib.pack(pady=20)

        self.entry_campione = ctk.CTkEntry(self.frame_calib, placeholder_text="Peso Kg", font=("Roboto", 24))
        self.entry_campione.pack(side="left", padx=5, ipadx=20, ipady=30)
        self.entry_campione.bind("<Button-1>", lambda e: NumericKeypad(self, self.entry_campione))

        self.btn_calib_span = ctk.CTkButton(self.frame_calib, text="CALIBRA", command=self.esegui_calibrazione_campione, fg_color="green")
        self.btn_calib_span.pack(side="left", padx=5, ipadx=20, ipady=20)
        self.btn_calib_span.configure(font=font_bottoni)

        self.process = None

    def start_measurement(self):
        self.btn_start.configure(state="disabled")
        thread = threading.Thread(target=self.run_c_program, daemon=True)
        thread.start()

    def run_c_program(self):
        cmd = ["stdbuf", "-oL", "/home/tecno/leggi_peso/leggi_peso"]
        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True, bufsize=1)
            self.process.stdin.write("\n")
            self.process.stdin.flush()

            for line in self.process.stdout:
                line = line.strip()
                if "CALIB:" in line:
                    step = int(line.split(":")[1])
                    self.after(0, self.update_calibration, step, step/40)
                elif "RAW:" in line or "PESO:" in line:
                    self.after(0, self.update_peso, line)
        except Exception as e:
            self.after(0, lambda: self.label_stato.configure(text=f"Errore: {e}"))

    def update_calibration(self, step, percent):
        self.label_stato.configure(text=f"Calibrazione in corso: {step}/40")
        self.progress_bar.set(percent)
        if step >= 40:
            self.label_stato.configure(text="Sistema Pronto", text_color="green")

    def update_peso(self, line):
        try:
            valore_str = line.split(":")[1].strip()
            valore_raw = float(valore_str)
            self.ultimo_raw = valore_raw
            
            peso_calibrati = valore_raw * self.scala
            taglio = 0.05
            kg_fissati = round(peso_calibrati / taglio) * taglio

            testo_display = f"{max(0, kg_fissati):.2f} Kg"
            self.label_peso.configure(text=testo_display)
        except:
            pass

    def esegui_tara(self):
        if self.process and self.process.poll() is None:
            self.process.stdin.write('t')
            self.process.stdin.flush()
            self.label_stato.configure(text="Ricalibrazione tara...", text_color="orange")
            self.progress_bar.set(0)

    def esegui_calibrazione_campione(self):
        try:
            peso_campione = float(self.entry_campione.get())
            if self.ultimo_raw != 0:
                self.scala = peso_campione / self.ultimo_raw
                self.salva_calibrazione()
                self.label_stato.configure(text="Calibrazione salvata!", text_color="green")
                self.entry_campione.delete(0, 'end')
        except:
            self.label_stato.configure(text="Errore valore!", text_color="red")

    def salva_calibrazione(self):
        try:
            with open("config_bilancia.txt", "w") as f:
                f.write(str(self.scala))
        except Exception as e:
            print(f"Errore salvataggio: {e}")

    def carica_calibrazione(self):
        if os.path.exists("config_bilancia.txt"):
            try:
                with open("config_bilancia.txt", "r") as f:
                    self.scala = float(f.read().strip())
                    print(f"Caricata: {self.scala}")
            except:
                self.scala = self.scala_default
        else:
            self.scala = self.scala_default

    def chiudi_applicazione(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
        os.system("stty echo")
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
