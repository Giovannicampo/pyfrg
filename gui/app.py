import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
from core.image_processor import ImageProcessor
from gui.canvas_widget import ImageCanvas
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ForgeryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("pyfrg - Image Forgery Tool")
        self.geometry("1100x700")

        self.image_processor = ImageProcessor()

        # Layout principale
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Logo sicuro
        self.logo_label = ctk.CTkLabel(self.sidebar, text="pyfrg", font=("Arial", 24, "bold"), text_color="#8B0000")
        try:
            if os.path.exists("assets/logo.png"):
                logo_img = ctk.CTkImage(Image.open("assets/logo.png"), size=(50, 50))
                self.logo_label.configure(image=logo_img, compound="left", text=" pyfrg")
        except: pass
        self.logo_label.pack(padx=20, pady=(20, 15))

        # Pulsanti Sidebar - Più compatti
        btn_style = {"height": 35, "fg_color": "transparent", "hover_color": "#8B0000", "anchor": "w", "corner_radius": 0}
        
        self.btn_load = ctk.CTkButton(self.sidebar, text="  📂 Carica Immagine", command=self.load_image, **btn_style)
        self.btn_load.pack(fill="x", pady=2)
        
        self.add_sep()
        
        self.btn_view = ctk.CTkButton(self.sidebar, text="  👁  Visualizza", command=lambda: self.show_page("view"), **btn_style)
        self.btn_view.pack(fill="x", pady=2)
        
        self.add_sep()
        
        self.btn_meta = ctk.CTkButton(self.sidebar, text="  ℹ  Metadati", command=lambda: self.show_page("meta"), **btn_style)
        self.btn_meta.pack(fill="x", pady=2)

        # --- AREA CONTENUTI ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        # 1. Canvas (al centro) - Inizializzato PRIMA della toolbar
        self.image_canvas = ImageCanvas(self.main_container)
        self.image_canvas.grid(row=1, column=0, sticky="nsew")

        # 2. Toolbar (sempre in alto nel container)
        self.toolbar = ctk.CTkFrame(self.main_container, height=50)
        self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.setup_toolbar()

        # 3. Status Bar (in basso)
        self.status_bar = ctk.CTkFrame(self.main_container, height=25)
        self.status_bar.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        self.pixel_info = ctk.CTkLabel(self.status_bar, text="X: - Y: - | RGB: -", font=("Consolas", 11))
        self.pixel_info.pack(side="right", padx=10)

        # Binding
        self.image_canvas.canvas.bind("<Motion>", self.on_mouse_move)
        
        # Binding Tastiera Globali
        self.bind("<Control-plus>", lambda e: self.zoom(1.2))
        self.bind("<Control-minus>", lambda e: self.zoom(0.8))
        self.bind("<Control-equal>", lambda e: self.zoom(1.2))

        self.show_page("view")

    def add_sep(self):
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#444").pack(fill="x")

    def show_page(self, page):
        # Per ora facciamo solo un feedback visivo sui tasti
        self.btn_view.configure(fg_color="#8B0000" if page=="view" else "transparent")
        self.btn_meta.configure(fg_color="#8B0000" if page=="meta" else "transparent")
        if page == "meta":
            print("Pagina Metadati non ancora implementata")

    def setup_toolbar(self):
        t_btn = {"width": 35, "height": 30, "fg_color": "#333", "hover_color": "#8B0000"}
        
        ctk.CTkLabel(self.toolbar, text="Zoom:").pack(side="left", padx=5)
        ctk.CTkButton(self.toolbar, text="-", command=lambda: self.zoom(0.8), **t_btn).pack(side="left", padx=2)
        ctk.CTkButton(self.toolbar, text="1:1", command=lambda: self.image_canvas.set_zoom_1_to_1(), **t_btn).pack(side="left", padx=2)
        ctk.CTkButton(self.toolbar, text="+", command=lambda: self.zoom(1.2), **t_btn).pack(side="left", padx=2)
        
        t_btn_fit = t_btn.copy()
        t_btn_fit["width"] = 50
        ctk.CTkButton(self.toolbar, text="Fit", command=lambda: self.image_canvas.fit_to_screen(), **t_btn_fit).pack(side="left", padx=5)
        
        ctk.CTkLabel(self.toolbar, text="| Canali:").pack(side="left", padx=5)
        for c in ["RGB", "R", "G", "B"]:
            ctk.CTkButton(self.toolbar, text=c, command=lambda m=c: self.image_canvas.set_channel_mode(m), **t_btn).pack(side="left", padx=1)

        ctk.CTkLabel(self.toolbar, text="| Overlay:").pack(side="left", padx=5)
        self.btn_grid = ctk.CTkButton(self.toolbar, text="▦", command=self.toggle_grid, **t_btn)
        self.btn_grid.pack(side="left", padx=2)

        ctk.CTkLabel(self.toolbar, text="| Filtri:").pack(side="left", padx=5)
        self.btn_invert = ctk.CTkButton(self.toolbar, text="🌓", command=self.toggle_invert, **t_btn)
        self.btn_invert.pack(side="left", padx=2)

        self.lbl_file = ctk.CTkLabel(self.toolbar, text="Nessun file")
        self.lbl_file.pack(side="right", padx=10)

    def toggle_grid(self):
        if hasattr(self, 'image_canvas'):
            self.image_canvas.toggle_grid()
            color = "#8B0000" if self.image_canvas.show_grid else "#333"
            self.btn_grid.configure(fg_color=color)

    def toggle_invert(self):
        if hasattr(self, 'image_canvas'):
            self.image_canvas.toggle_invert()
            color = "#8B0000" if self.image_canvas.is_inverted else "#333"
            self.btn_invert.configure(fg_color=color)

    def on_mouse_move(self, event):
        self.pixel_info.configure(text=self.image_canvas.get_pixel_data(event.x, event.y))

    def zoom(self, f):
        if self.image_canvas.original_image:
            self.image_canvas.scale *= f
            self.image_canvas.redraw()

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Immagini", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Tutti i file", "*.*")])
        if path:
            img = self.image_processor.load_image(path)
            if img:
                self.image_canvas.set_image(img)
                self.lbl_file.configure(text=os.path.basename(path))

if __name__ == "__main__":
    ForgeryApp().mainloop()
