import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image
from core.image_processor import ImageProcessor
from gui.canvas_widget import ImageCanvas
from gui.tooltip import CTkToolTip
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ChannelSelector(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Seleziona Canale")
        self.geometry("300x650")
        self.callback = callback
        self.attributes("-topmost", True)
        
        ctk.CTkLabel(self, text="Spazi Colore", font=("Arial", 16, "bold")).pack(pady=10)
        
        modes = [
            ("RGB (Originale)", "RGB"),
            ("Rosso (R)", "R"), ("Verde (G)", "G"), ("Blu (B)", "B"),
            ("---", None),
            ("HSV (Analisi)", "HSV"), ("Hue (Tonalità)", "H"), ("Saturation", "S"), ("Value (Luminosità)", "V"),
            ("---", None),
            ("YCbCr (JPEG)", "YCbCr"), ("Luminance (Y)", "Y"), ("Chroma Blue (Cb)", "Cb"), ("Chroma Red (Cr)", "Cr"),
            ("---", None),
            ("Luminance (L)", "L")
        ]
        
        for label, mode in modes:
            if mode is None:
                ctk.CTkFrame(self, height=2, fg_color="#444").pack(fill="x", padx=20, pady=5)
            else:
                ctk.CTkButton(self, text=label, command=lambda m=mode: self.select(m), 
                            fg_color="transparent", border_width=1, border_color="#555").pack(fill="x", padx=20, pady=2)

    def select(self, mode):
        self.callback(mode)
        self.destroy()

class ForgeryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("pyfrg")
        self.geometry("1100x700")

        self.image_processor = ImageProcessor()

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Logo
        self.logo_label = ctk.CTkLabel(self.sidebar, text="pyfrg", font=("Arial", 24, "bold"), text_color="#7A0202")
        try:
            if os.path.exists("assets/logo.png"):
                logo_img = ctk.CTkImage(Image.open("assets/logo.png"), size=(50, 50))
                self.logo_label.configure(image=logo_img, compound="left", text=" pyfrg")
        except: pass
        self.logo_label.pack(padx=20, pady=(20, 15))

        # Pulsanti Sidebar
        btn_style = {"height": 35, "fg_color": "transparent", "hover_color": "#8B0000", "anchor": "w", "corner_radius": 0}
        
        self.btn_load = ctk.CTkButton(self.sidebar, text="  📂 Carica Immagine", command=self.load_image, **btn_style)
        self.btn_load.pack(fill="x", pady=2)
        self.add_sep()
        
        self.btn_view = ctk.CTkButton(self.sidebar, text="  👁  Visualizza", command=lambda: self.show_page("view"), **btn_style)
        self.btn_view.pack(fill="x", pady=2)
        self.add_sep()
        
        self.btn_meta = ctk.CTkButton(self.sidebar, text="  ℹ  Metadati", command=lambda: self.show_page("meta"), **btn_style)
        self.btn_meta.pack(fill="x", pady=2)
        self.add_sep()

        self.btn_tools = ctk.CTkButton(self.sidebar, text="  🛠  Strumenti", command=lambda: self.show_page("tools"), **btn_style)
        self.btn_tools.pack(fill="x", pady=2)

        # --- AREA CONTENUTI ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # 1. Canvas
        self.image_canvas = ImageCanvas(self.main_container)
        self.image_canvas.grid(row=1, column=0, sticky="nsew")

        # 2. Toolbar
        self.toolbar = ctk.CTkFrame(self.main_container, height=50)
        self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.setup_toolbar()

        # 3. Vista Metadati
        self.metadata_view = ctk.CTkScrollableFrame(self.main_container, fg_color="#1a1a1a")

        # 4. Status Bar
        self.status_bar = ctk.CTkFrame(self.main_container, height=25)
        self.status_bar.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        
        self.lbl_file = ctk.CTkLabel(self.status_bar, text="Nessun file caricato", font=("Arial", 11))
        self.lbl_file.pack(side="left", padx=10)

        self.pixel_info = ctk.CTkLabel(self.status_bar, text="X: - Y: - | RGB: -", font=("Consolas", 11))
        self.pixel_info.pack(side="right", padx=20)

        # Binding
        self.image_canvas.canvas.bind("<Motion>", self.on_mouse_move)
        self.bind("<Control-plus>", lambda e: self.zoom(1.2))
        self.bind("<Control-minus>", lambda e: self.zoom(0.8))
        self.bind("<Control-equal>", lambda e: self.zoom(1.2))

        self.show_page("view")

    def add_sep(self):
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#444").pack(fill="x")

    def show_page(self, page):
        self.btn_view.configure(fg_color="#8B0000" if page=="view" else "transparent")
        self.btn_meta.configure(fg_color="#8B0000" if page=="meta" else "transparent")
        self.btn_tools.configure(fg_color="#8B0000" if page=="tools" else "transparent")
        
        if page == "view":
            self.metadata_view.grid_forget()
            self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
            self.image_canvas.grid(row=1, column=0, sticky="nsew")
        elif page == "meta":
            self.toolbar.grid_forget()
            self.image_canvas.grid_forget()
            self.metadata_view.grid(row=0, column=0, rowspan=2, sticky="nsew")
            self.update_metadata_ui()
        else:
            print(f"Pagina {page} non implementata")

    def update_metadata_ui(self):
        for widget in self.metadata_view.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(self.metadata_view, text="Analisi Metadati EXIF", font=("Arial", 18, "bold"), text_color="#7A0202").pack(pady=20)
        data = self.image_processor.get_formatted_exif()
        for label, value in data:
            row = ctk.CTkFrame(self.metadata_view, fg_color="transparent")
            row.pack(fill="x", padx=40, pady=5)
            ctk.CTkLabel(row, text=f"{label}:", width=200, anchor="w", font=("Arial", 12, "bold"), text_color="gray70").pack(side="left")
            ctk.CTkLabel(row, text=value, anchor="w", font=("Arial", 12)).pack(side="left", padx=10)

    def setup_toolbar(self):
        t_btn = {"width": 35, "height": 30, "fg_color": "#333", "hover_color": "#8B0000"}
        
        # ZOOM
        ctk.CTkLabel(self.toolbar, text="Zoom:").pack(side="left", padx=5)
        b_out = ctk.CTkButton(self.toolbar, text="-", command=lambda: self.zoom(0.8), **t_btn)
        b_out.pack(side="left", padx=2)
        CTkToolTip(b_out, "Zoom Out")

        b_11 = ctk.CTkButton(self.toolbar, text="1:1", command=lambda: self.image_canvas.set_zoom_1_to_1(), **t_btn)
        b_11.pack(side="left", padx=2)
        CTkToolTip(b_11, "Zoom 1:1")

        b_in = ctk.CTkButton(self.toolbar, text="+", command=lambda: self.zoom(1.2), **t_btn)
        b_in.pack(side="left", padx=2)
        CTkToolTip(b_in, "Zoom In")
        
        t_btn_fit = t_btn.copy()
        t_btn_fit["width"] = 40
        b_fit = ctk.CTkButton(self.toolbar, text="FIT", command=lambda: self.image_canvas.fit_to_screen(), **t_btn_fit)
        b_fit.pack(side="left", padx=5)
        CTkToolTip(b_fit, "Adatta allo schermo")
        
        # CANALI (Popup button invece di Dropdown instabile)
        ctk.CTkLabel(self.toolbar, text="| Canali:").pack(side="left", padx=5)
        self.btn_channels = ctk.CTkButton(self.toolbar, text="RGB ▾", command=self.open_channel_selector, width=60, height=30, fg_color="#333", hover_color="#8B0000")
        self.btn_channels.pack(side="left", padx=2)
        CTkToolTip(self.btn_channels, "Seleziona Canale / Spazio Colore")

        # STRUMENTI ANALISI
        ctk.CTkLabel(self.toolbar, text="| Strumenti:").pack(side="left", padx=5)
        
        t_btn_wide = t_btn.copy()
        t_btn_wide["width"] = 45

        self.btn_grid = ctk.CTkButton(self.toolbar, text="▦", command=self.toggle_grid, **t_btn_wide)
        self.btn_grid.pack(side="left", padx=2)
        CTkToolTip(self.btn_grid, "Griglia")

        self.btn_invert = ctk.CTkButton(self.toolbar, text="🌓", command=self.toggle_invert, **t_btn_wide)
        self.btn_invert.pack(side="left", padx=2)
        CTkToolTip(self.btn_invert, "Inverti (Negativo)")

        self.btn_he = ctk.CTkButton(self.toolbar, text="◩", command=lambda: self.toggle_filter("Equalize"), **t_btn_wide)
        self.btn_he.pack(side="left", padx=2)
        CTkToolTip(self.btn_he, "Equalizzazione Contrasto")

        self.btn_edge = ctk.CTkButton(self.toolbar, text="EDGE", command=lambda: self.toggle_filter("Edge"), **t_btn_wide)
        self.btn_edge.pack(side="left", padx=2)
        CTkToolTip(self.btn_edge, "Rilevamento Bordi")
        
        ctk.CTkLabel(self.toolbar, text="|").pack(side="left", padx=5)

        b_save = ctk.CTkButton(self.toolbar, text="SAVE", command=self.save_view, **t_btn_wide)
        b_save.pack(side="left", padx=2)
        CTkToolTip(b_save, "Salva Vista")

        b_hist = ctk.CTkButton(self.toolbar, text="HIST", command=self.show_histogram, **t_btn_wide)
        b_hist.pack(side="left", padx=2)
        CTkToolTip(b_hist, "Istogramma RGB")

    def open_channel_selector(self):
        ChannelSelector(self, self.set_channel_from_popup)

    def set_channel_from_popup(self, mode):
        self.image_canvas.set_channel_mode(mode)
        # Aggiorna il testo del bottone per mostrare cosa è selezionato
        self.btn_channels.configure(text=f"{mode} ▾")

    def toggle_grid(self):
        if hasattr(self, 'image_canvas'):
            self.image_canvas.toggle_grid()
            self.btn_grid.configure(fg_color="#8B0000" if self.image_canvas.show_grid else "#333")

    def toggle_invert(self):
        if hasattr(self, 'image_canvas'):
            self.image_canvas.toggle_invert()
            self.btn_invert.configure(fg_color="#8B0000" if self.image_canvas.is_inverted else "#333")

    def toggle_filter(self, mode):
        if hasattr(self, 'image_canvas'):
            curr = self.image_canvas.set_analysis_mode(mode)
            self.btn_he.configure(fg_color="#8B0000" if curr == "Equalize" else "#333")
            self.btn_edge.configure(fg_color="#8B0000" if curr == "Edge" else "#333")

    def show_histogram(self):
        try:
            from gui.histogram_window import HistogramWindow
            if self.image_canvas.original_image:
                HistogramWindow(self, self.image_canvas.original_image, self.image_canvas.get_current_processed_image())
        except Exception as e:
            print(f"Errore: {e}")

    def save_view(self):
        img = self.image_canvas.get_current_processed_image()
        if img:
            path = filedialog.asksaveasfilename(defaultextension=".png")
            if path: img.save(path)

    def on_mouse_move(self, event):
        self.pixel_info.configure(text=self.image_canvas.get_pixel_data(event.x, event.y))

    def zoom(self, f):
        if self.image_canvas.original_image:
            self.image_canvas.scale *= f
            self.image_canvas.redraw()

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Immagini supportate", "*.jpg *.jpeg *.png *.bmp *.webp"),
            ("Tutti i file", "*.*")
        ])
        if path:
            img = self.image_processor.load_image(path)
            if img:
                self.image_canvas.set_image(img)
                self.lbl_file.configure(text=f"File: {os.path.basename(path)}")
                if hasattr(self, 'metadata_view') and self.metadata_view.winfo_ismapped():
                    self.update_metadata_ui()

if __name__ == "__main__":
    ForgeryApp().mainloop()
