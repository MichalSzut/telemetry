import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class TelemetryAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Hydrive Telemetry Analyzer - Shell Eco-marathon")
        self.root.geometry("900x600")
        
        # Słowniki na zdekodowane dane
        self.data = {
            "v1": [], "v2": [], "v3": [], "v4": [],
            "c1": [], "c2": [], "c3": [], "c4": [],
            "s": []
        }
        self.timestamps = []
        
        self.setup_ui()
        
    def setup_ui(self):
        # --- Górny panel sterowania ---
        control_frame = tk.Frame(self.root, padx=10, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Przycisk wczytywania
        self.btn_load = tk.Button(control_frame, text="Wczytaj dane (TXT/JSONL)", command=self.load_file)
        self.btn_load.pack(side=tk.LEFT, padx=5)
        
        # Wybór parametru do wyświetlenia
        tk.Label(control_frame, text="Parametr:").pack(side=tk.LEFT, padx=5)
        self.param_var = tk.StringVar()
        self.param_cb = ttk.Combobox(control_frame, textvariable=self.param_var, state="readonly", width=5)
        self.param_cb.pack(side=tk.LEFT, padx=5)
        self.param_cb.bind("<<ComboboxSelected>>", self.update_plot)
        
        # Wybór skoku próbkowania (Downsampling)
        tk.Label(control_frame, text="Próbkowanie (co N-ta próbka):").pack(side=tk.LEFT, padx=5)
        self.sampling_var = tk.IntVar(value=10)
        self.sampling_spin = tk.Spinbox(control_frame, from_=1, to=5000, textvariable=self.sampling_var, width=5, command=self.update_plot)
        self.sampling_spin.pack(side=tk.LEFT, padx=5)
        
        # --- Obszar wykresu (Matplotlib wbudowany w Tkinter) ---
        self.fig, self.ax = plt.subplots(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        
    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text Files", "*.TXT"), ("All Files", "*.*")])
        if not filepath:
            return
            
        # Resetowanie danych przed nowym odczytem
        for key in self.data:
            self.data[key].clear()
        self.timestamps.clear()
        
        try:
            # Odczyt linia po linii
            with open(filepath, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if "timestamp" in record:
                            self.timestamps.append(record["timestamp"])
                            # Reszta wartości z danego rekordu
                            for key in self.data.keys():
                                if key in record:
                                    self.data[key].append(float(record[key]))
                    except json.JSONDecodeError:
                        continue # pomijanie uszkodzonych linii z czujników
                        
            # Aktualizacja UI po udanym wczytaniu
            self.param_cb['values'] = list(self.data.keys())
            if self.param_cb['values']:
                self.param_cb.current(0)
                self.update_plot()
                
            messagebox.showinfo("Sukces", f"Pomyślnie załadowano {len(self.timestamps)} próbek!")
                
        except Exception as e:
            messagebox.showerror("Błąd", f"Wystąpił błąd podczas czytania pliku:\n{e}")
            
    def update_plot(self, event=None):
        if not self.timestamps:
            return
            
        param = self.param_var.get()
        try:
            step = int(self.sampling_var.get())
        except ValueError:
            step = 1
            
        if step < 1: step = 1
            
        # PRÓBKOWANIE
        sampled_time = self.timestamps[::step]
        sampled_values = self.data[param][::step]
        
        # Czyszczenie i rysowanie nowego wykresu
        self.ax.clear()
        self.ax.plot(sampled_time, sampled_values, label=f"Parametr: {param}", color="#ff5722", linewidth=1.5)
        
        # Estetyka wykresu
        self.ax.set_title(f"Telemetria Hydrive - {param.upper()}", fontsize=14, fontweight='bold')
        self.ax.set_xlabel("Czas [ms]", fontsize=11)
        self.ax.set_ylabel("Wartość", fontsize=11)
        self.ax.grid(True, linestyle="--", alpha=0.6)
        self.ax.legend()
        
        # Formatowanie osi X, aby unikać notacji naukowej (np. 1e6) przy długich timestampach
        self.ax.ticklabel_format(style='plain', axis='x')
        
        self.canvas.draw()

if __name__ == "__main__":
    # Inicjalizacja aplikacji
    root = tk.Tk()
    app = TelemetryAnalyzer(root)
    root.mainloop()