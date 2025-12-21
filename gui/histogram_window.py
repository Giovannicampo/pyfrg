import customtkinter as ctk
import tkinter as tk
import matplotlib
matplotlib.use("TkAgg") # Fondamentale per evitare conflitti su Linux
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

class HistogramWindow(ctk.CTkToplevel):
    def __init__(self, parent, original_image, current_image):
        super().__init__(parent)
        self.title("Analisi Spettrale RGB")
        self.geometry("800x600")
        
        # Rendiamo la finestra modale (opzionale, per ora lasciamola libera)
        # self.transient(parent) 
        
        self.original_image = original_image
        self.current_image = current_image

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Matplotlib Figure
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.figure.patch.set_facecolor('#2b2b2b') # Background scuro
        
        # Creiamo 2 subplot: Originale vs Corrente
        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212)
        
        self.plot_histogram(self.ax1, self.original_image, "Istogramma Originale")
        if self.current_image:
            self.plot_histogram(self.ax2, self.current_image, "Istogramma Attuale (Filtrato)")
        
        self.figure.tight_layout()

        # Canvas Tkinter per Matplotlib
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Bottone Chiudi
        self.btn_close = ctk.CTkButton(self, text="Chiudi", command=self.destroy, fg_color="#8B0000")
        self.btn_close.grid(row=1, column=0, pady=10)

    def plot_histogram(self, ax, image, title):
        ax.set_facecolor('#333333')
        ax.set_title(title, color='white', fontsize=10)
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        
        if image is None:
            return

        # Converti in RGB array
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        img_array = np.array(image)
        
        colors = ('r', 'g', 'b')
        for i, color in enumerate(colors):
            hist, bins = np.histogram(img_array[:, :, i], 256, [0, 256])
            ax.plot(hist, color=color, alpha=0.8, linewidth=1)
            ax.fill_between(range(256), hist, color=color, alpha=0.1)
        
        ax.set_xlim([0, 256])
        ax.grid(True, linestyle='--', alpha=0.2)
