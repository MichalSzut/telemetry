import json
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from collections import deque


# Ilość próbek widoczna jednocześnie na wykresie (szerokość okna przesuwnego)
WINDOW_SIZE = 200 

WINDOW_SIZE = 150      # Mniejszy bufor = szybsze rysowanie
SKIP_STEP = 15         
REFRESH_RATE = 100      # Interwał odświeżania w ms

class LiveTelemetryDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Hidrive Live Telemetry Dashboard")
        self.root.geometry("1400x800")
        self.root.configure(bg="#2b2b2b")
        
        # Inicjalizacja buforów kołowych (zapobiega wyciekom pamięci)
        self.timestamps = deque(maxlen=WINDOW_SIZE)
        self.data = {
            "v1": deque(maxlen=WINDOW_SIZE), "v2": deque(maxlen=WINDOW_SIZE),
            "v3": deque(maxlen=WINDOW_SIZE), "v4": deque(maxlen=WINDOW_SIZE),
            "c1": deque(maxlen=WINDOW_SIZE), "c2": deque(maxlen=WINDOW_SIZE),
            "c3": deque(maxlen=WINDOW_SIZE), "c4": deque(maxlen=WINDOW_SIZE),
            "s": deque(maxlen=WINDOW_SIZE)
        }
        
        self.file_iterator = None
        self.is_playing = False
        
        self.setup_ui()
        self.setup_plots()
        
        # Konfiguracja animacji 
        self.ani = FuncAnimation(self.fig, self.update_dashboard, interval=50, blit=False, cache_frame_data=False)

    def setup_ui(self):
        # Panel sterowania na samej górze, wgrywanie danych i tytuł, stop/start
        ctrl_frame = tk.Frame(self.root, bg="#1e1e1e", pady=10)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(ctrl_frame, text="HIDRIVE TELEMETRY LIVE", fg="lime", bg="#1e1e1e", 
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=20)
        
        btn_load = tk.Button(ctrl_frame, text="Wczytaj strumień danych (TXT)", command=self.load_stream, 
                             bg="#007acc", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, padx=10)
        btn_load.pack(side=tk.LEFT, padx=10)

        self.btn_toggle = tk.Button(ctrl_frame, text="Wstrzymaj/Wznów", command=self.toggle_play,
                                    bg="#d9534f", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, padx=10)
        self.btn_toggle.pack(side=tk.LEFT, padx=10)

    def setup_plots(self):
        # Używamy profesjonalnego, ciemnego stylu
        plt.style.use("dark_background")
        self.fig = plt.Figure(figsize=(14, 8), dpi=100)
        # Marginesy i odstępy
        self.fig.subplots_adjust(left=0.05, right=0.98, top=0.95, bottom=0.05, wspace=0.3, hspace=0.5)
        
        # GridSpec - siatka 4 wiersze x 3 kolumny
        gs = self.fig.add_gridspec(4, 3)
        
        self.axes = {}
        self.lines = {}
        
        #KOLUMNA 1: NAPIĘCIA (v1-v4)
        for i in range(4):
            ax = self.fig.add_subplot(gs[i, 0])
            ax.set_title(f"Napięcie V{i+1} [V]", color="cyan", fontsize=10, loc="left", pad=3)
            ax.grid(True, alpha=0.3, linestyle="--")
            line, = ax.plot([], [], color="cyan", lw=1.5)
            self.axes[f"v{i+1}"] = ax
            self.lines[f"v{i+1}"] = line

        #KOLUMNA 2: PRĄDY (c1-c4)
        for i in range(4):
            ax = self.fig.add_subplot(gs[i, 1])
            ax.set_title(f"Prąd C{i+1} [A]", color="#ff9900", fontsize=10, loc="left", pad=3)
            ax.grid(True, alpha=0.3, linestyle="--")
            line, = ax.plot([], [], color="#ff9900", lw=1.5)
            self.axes[f"c{i+1}"] = ax
            self.lines[f"c{i+1}"] = line

        #KOLUMNA 3: PRĘDKOŚĆ (s)
        ax_s = self.fig.add_subplot(gs[:, 2])
        ax_s.set_title("Prędkość [km/h]", color="lime", fontsize=14, fontweight="bold")
        ax_s.grid(True, alpha=0.3, linestyle="--")
        line_s, = ax_s.plot([], [], color="lime", lw=2.5)
        # Cieniowanie pod wykresem
        self.fill_s = None
        self.axes["s"] = ax_s
        self.lines["s"] = line_s

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    def load_stream(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Lines / TXT", "*.TXT *.jsonl")])
        if filepath:
            self.file_iterator = open(filepath, 'r', encoding='utf-8')
            self.is_playing = True
            
            #Tu zaczyna się przejazd -> 423 000ms
            TARGET_TIMESTAMP = 423000
            
            # Pętla czyta plik w tle
            while True:
                pos = self.file_iterator.tell() # Zapamiętujemy pozycję linijki
                line = self.file_iterator.readline()
                
                if not line:
                    break # Doszliśmy do końca pliku
                    
                try:
                    record = json.loads(line)
                    # Jeśli znaleźliśmy nasz moment (lub pierwszy większy)...
                    if float(record.get("timestamp", 0)) >= TARGET_TIMESTAMP:
                        self.file_iterator.seek(pos) # ...cofamy "kursor" pliku o tę jedną linijkę
                        
                        # Ustawiamy czas startowy, dzięki temu oś X zacznie się ładnie od zera
                        self.start_time = float(record.get("timestamp", 0))
                        break # Wychodzimy z pętli, jesteśmy gotowi do rysowania!
                except Exception:
                    continue # Ignorujemy uszkodzone linijki
            
            # Czyszczenie buforów z danymi wykresów
            self.timestamps.clear()
            for key in self.data:
                self.data[key].clear()

    def toggle_play(self):
        self.is_playing = not self.is_playing

    def update_dashboard(self, frame):
        if not self.is_playing or not self.file_iterator:
            return

        has_new_data = False
        
        # Czytamy SKIP_STEP linii, ale zapisujemy tylko OSTATNIĄ z nich
        # Dzięki temu symulacja zachowuje realny upływ czasu, ale nie zapycha pamięci
        last_valid_record = None
        
        for _ in range(SKIP_STEP):
            line = self.file_iterator.readline()
            if not line:
                self.is_playing = False
                break
            
            line = line.strip()
            if line:
                try:
                    last_valid_record = json.loads(line)
                except json.JSONDecodeError:
                    continue

        # Jeśli udało się pobrać próbkę po przeskoczeniu SKIP_STEP linii
        if last_valid_record:
            record = last_valid_record
            if "timestamp" in record:
                #normalizacja czasu do sekund (zmieniamy milisekundy na sekundy)
                if self.start_time is None:
                    self.start_time = record["timestamp"]
                
                current_time = (record["timestamp"] - self.start_time) / 1000.0
                self.timestamps.append(current_time)
                
                for key in self.data.keys():
                    if key in record:
                        self.data[key].append(float(record[key]))
                has_new_data = True

        if has_new_data:
            t_data = list(self.timestamps)
            # Optymalizacja: przeliczamy skale tylko co 5 klatek, żeby oszczędzić CPU
            should_rescale = (frame % 5 == 0) 

            for key, line in self.lines.items():
                y_data = list(self.data[key])
                line.set_data(t_data, y_data)
                
                ax = self.axes[key]
                
                # Ustawiamy zakres osi X (pływające okno)
                if len(t_data) > 1:
                    ax.set_xlim(t_data[0], t_data[-1])
                
                if should_rescale:
                    ax.relim()
                    ax.autoscale_view(scalex=False, scaley=True)

            # Cieniowanie prędkości
            if self.fill_s is not None:
                self.fill_s.remove()
            self.fill_s = self.axes["s"].fill_between(t_data, list(self.data["s"]), color="lime", alpha=0.1)

            self.canvas.draw_idle() 

if __name__ == "__main__":
    root = tk.Tk()
    app = LiveTelemetryDashboard(root)
    root.mainloop()