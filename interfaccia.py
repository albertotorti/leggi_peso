import customtkinter as ctk
import subprocess
import threading
import os

class BilanciaApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema di Pesatura Professionale")
        self.geometry("600x400")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # UI Elements
        self.label_titolo = ctk.CTkLabel(self, text="BILANCIA DIGITALE", font=("Roboto", 24, "bold"))
        self.label_titolo.pack(pady=20)

        self.progress_bar = ctk.CTkProgressBar(self, width=300)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.label_stato = ctk.CTkLabel(self, text="In attesa di avvio...", font=("Roboto", 14))
        self.label_stato.pack(pady=5)

        self.frame_peso = ctk.CTkFrame(self, corner_radius=15)
        self.frame_peso.pack(pady=20, padx=40, fill="both")

        self.label_peso = ctk.CTkLabel(self.frame_peso, text="--- g", font=("Roboto", 60, "bold"), text_color="#3b8ed0")
        self.label_peso.pack(pady=30)

        self.btn_start = ctk.CTkButton(self, text="AVVIA SISTEMA", command=self.start_measurement)
        self.btn_start.pack(pady=20)

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
                if "Calibrazione" in line:
                    try:
                        step = int(line.split()[1].split('/')[0])
                        percent = step / 40
                        self.after(0, self.update_calibration, step, percent)
                    except: pass
                
                # Gestione Lettura Peso
                elif "Peso:" in line:
                    try:
                        # Estrae il valore numerico dopo "Peso:"
                        valore = line.split("Peso:")[1].split("gr")[0].strip()
                        self.after(0, self.update_peso, valore)
                    except: pass

        except Exception as e:
            self.after(0, lambda: self.label_stato.configure(text=f"Errore: {e}"))

    def update_calibration(self, step, percent):
        self.label_stato.configure(text=f"Calibrazione in corso: {step}/40")
        self.progress_bar.set(percent)
        if step >= 40:
            self.label_stato.configure(text="Sistema Pronto", text_color="green")

    def update_peso(self, valore):
        self.label_peso.configure(text=f"{valore} g")

if __name__ == "__main__":
    app = BilanciaApp()
    app.mainloop()
