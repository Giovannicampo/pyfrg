import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps

class ImageCanvas(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Configurazione Grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Canvas nativo di Tkinter per performance e gestione pixel
        self.canvas = tk.Canvas(self, bg="#2b2b2b", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Variabili stato
        self.original_image = None  # PIL Image originale
        self.displayed_image = None # PIL Image scalata
        self.tk_image = None        # Immagine compatibile Tkinter
        
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        self.show_grid = False
        self.is_inverted = False
        self.channel_mode = "RGB" # RGB, R, G, B

        # Eventi Mouse
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan_image)
        self.canvas.bind("<MouseWheel>", self.zoom_image) # Windows/MacOS
        self.canvas.bind("<Button-4>", self.zoom_image)   # Linux Scroll Up
        self.canvas.bind("<Button-5>", self.zoom_image)   # Linux Scroll Down

    def set_image(self, pil_image):
        """Imposta una nuova immagine e resetta la vista."""
        self.original_image = pil_image
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.fit_to_screen()
        self.redraw()

    def fit_to_screen(self):
        """Adatta l'immagine alle dimensioni attuali del canvas."""
        if not self.original_image:
            return
        
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        iw, ih = self.original_image.size

        # Calcola scala per adattare
        scale_w = cw / iw
        scale_h = ch / ih
        self.scale = min(scale_w, scale_h) * 0.9 # 90% per margine
        
        # Centra
        new_w = int(iw * self.scale)
        new_h = int(ih * self.scale)
        self.pan_x = (cw - new_w) // 2
        self.pan_y = (ch - new_h) // 2

        self.redraw()
    
    def set_zoom_1_to_1(self):
        """Imposta lo zoom al 100% (pixel reali)."""
        if not self.original_image:
            return
        self.scale = 1.0
        # Centriamo approssimativamente
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        iw, ih = self.original_image.size
        self.pan_x = (cw - iw) // 2
        self.pan_y = (ch - ih) // 2
        self.redraw()

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.redraw()

    def set_channel_mode(self, mode):
        self.channel_mode = mode
        self.redraw()

    def toggle_invert(self):
        self.is_inverted = not self.is_inverted
        self.redraw()

    def redraw(self):
        """Ridisegna l'immagine sul canvas applicando scala, pan e filtri canale."""
        self.canvas.delete("all")
        
        if not self.original_image:
            return

        # 0. Applica Filtro Canale (su copia temp, non toccare originale)
        img_to_process = self.original_image
        if self.channel_mode != "RGB":
            try:
                # Assicuriamoci che l'immagine sia RGB (gestisce RGBA o Grayscale)
                if img_to_process.mode != "RGB":
                    img_to_process = img_to_process.convert("RGB")
                
                r, g, b = img_to_process.split()
                zero = Image.new("L", r.size, 0)
                
                if self.channel_mode == "R":
                    img_to_process = Image.merge("RGB", (r, zero, zero))
                elif self.channel_mode == "G":
                    img_to_process = Image.merge("RGB", (zero, g, zero))
                elif self.channel_mode == "B":
                    img_to_process = Image.merge("RGB", (zero, zero, b))
            except Exception as e:
                print(f"Errore cambio canale: {e}")

        # 0.5 Inversione (Negativo)
        if self.is_inverted:
            try:
                if img_to_process.mode == "RGBA":
                    # Invertiamo solo RGB, lasciamo Alpha intatto
                    r, g, b, a = img_to_process.split()
                    rgb = Image.merge("RGB", (r, g, b))
                    inv = ImageOps.invert(rgb)
                    r, g, b = inv.split()
                    img_to_process = Image.merge("RGBA", (r, g, b, a))
                else:
                    if img_to_process.mode != "RGB":
                         img_to_process = img_to_process.convert("RGB")
                    img_to_process = ImageOps.invert(img_to_process)
            except Exception as e:
                print(f"Errore inversione: {e}")

        # 1. Calcola nuove dimensioni
        width, height = img_to_process.size
        new_size = (int(width * self.scale), int(height * self.scale))
        
        # Evitiamo crash se troppo piccolo
        if new_size[0] < 1 or new_size[1] < 1:
            return

        # 2. Resampling
        # Usa Nearest se zoom > 2.0 per vedere i pixel, altrimenti Bilinear
        resample_method = Image.Resampling.NEAREST if self.scale > 2.0 else Image.Resampling.BILINEAR
        self.displayed_image = img_to_process.resize(new_size, resample_method)
        
        # 3. Conversione per Tkinter
        self.tk_image = ImageTk.PhotoImage(self.displayed_image)

        # 4. Disegno Immagine
        self.canvas.create_image(self.pan_x, self.pan_y, anchor="nw", image=self.tk_image)
        
        # 5. Disegno Griglia (Overlay)
        if self.show_grid:
            self._draw_grid(new_size[0], new_size[1])

    def _draw_grid(self, w, h):
        """Disegna una griglia sopra l'immagine."""
        step = 50 * self.scale # Griglia ogni 50 pixel dell'immagine originale
        if step < 10: step = 10 # Limite minimo visivo
        
        # Linee Verticali
        for i in range(0, int(w), int(step)):
            x = self.pan_x + i
            self.canvas.create_line(x, self.pan_y, x, self.pan_y + h, fill="#00ff00", stipple="gray50")
            
        # Linee Orizzontali
        for i in range(0, int(h), int(step)):
            y = self.pan_y + i
            self.canvas.create_line(self.pan_x, y, self.pan_x + w, y, fill="#00ff00", stipple="gray50")
        
        # Bordo immagine
        self.canvas.create_rectangle(self.pan_x, self.pan_y, self.pan_x + w, self.pan_y + h, outline="#ff0000")

    def get_pixel_data(self, canvas_x, canvas_y):
        """Restituisce informazioni sul pixel alle coordinate canvas date."""
        if not self.original_image:
            return "Nessuna immagine"
            
        # Converti coord canvas -> coord immagine
        img_x = int((canvas_x - self.pan_x) / self.scale)
        img_y = int((canvas_y - self.pan_y) / self.scale)
        
        w, h = self.original_image.size
        
        if 0 <= img_x < w and 0 <= img_y < h:
            try:
                # Ottieni colore pixel originale (lento se fatto spesso, ma ok per hover)
                # Nota: getpixel è veloce su singoli pixel
                pixel = self.original_image.getpixel((img_x, img_y))
                return f"X: {img_x} Y: {img_y} | RGB: {pixel}"
            except Exception:
                return "Errore lettura"
        else:
            return f"Fuori area (X: {img_x}, Y: {img_y})"

    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def pan_image(self, event):
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        
        self.pan_x += dx
        self.pan_y += dy
        
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        
        self.redraw()

    def zoom_image(self, event):
        if not self.original_image:
            return

        # Fattore di zoom
        zoom_factor = 1.1
        if event.num == 5 or event.delta < 0:
            self.scale /= zoom_factor
        else:
            self.scale *= zoom_factor

        self.redraw()
