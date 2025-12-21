import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps, ImageFilter
import colorsys

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
        self.channel_mode = "RGB" # RGB, R, G, B, H, S, V, L, Y, Cb, Cr
        self.analysis_mode = "Normal" # Normal, Equalize, Edge

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
        
    def set_analysis_mode(self, mode):
        if self.analysis_mode == mode:
            self.analysis_mode = "Normal"
        else:
            self.analysis_mode = mode
        self.redraw()
        return self.analysis_mode

    def toggle_invert(self):
        self.is_inverted = not self.is_inverted
        self.redraw()

    def get_current_processed_image(self):
        """Restituisce l'immagine processata a piena risoluzione."""
        if not self.original_image:
            return None
        return self._apply_filters(self.original_image)

    def _apply_filters(self, img):
        if img.mode != "RGB" and img.mode != "RGBA":
            img_to_process = img.convert("RGB")
        else:
            img_to_process = img.copy()

        mode = self.channel_mode
        try:
            if mode == "RGB": pass
            elif mode in ["R", "G", "B"]:
                if img_to_process.mode != "RGB": img_to_process = img_to_process.convert("RGB")
                r, g, b = img_to_process.split()
                zero = Image.new("L", r.size, 0)
                if mode == "R": img_to_process = Image.merge("RGB", (r, zero, zero))
                elif mode == "G": img_to_process = Image.merge("RGB", (zero, g, zero))
                elif mode == "B": img_to_process = Image.merge("RGB", (zero, zero, b))
            elif mode in ["HSV", "H", "S", "V"]:
                hsv = img_to_process.convert("HSV")
                if mode == "HSV": img_to_process = hsv.convert("RGB")
                else:
                    h, s, v = hsv.split()
                    if mode == "H": img_to_process = h.convert("RGB")
                    elif mode == "S": img_to_process = s.convert("RGB")
                    elif mode == "V": img_to_process = v.convert("RGB")
            elif mode in ["YCbCr", "Y", "Cb", "Cr"]:
                ycbcr = img_to_process.convert("YCbCr")
                if mode == "YCbCr": img_to_process = ycbcr.convert("RGB")
                else:
                    y, cb, cr = ycbcr.split()
                    if mode == "Y": img_to_process = y.convert("RGB")
                    elif mode == "Cb": img_to_process = cb.convert("RGB")
                    elif mode == "Cr": img_to_process = cr.convert("RGB")
            elif mode == "L":
                img_to_process = img_to_process.convert("L").convert("RGB")
        except Exception as e:
            print(f"Errore colore {mode}: {e}")

        if self.is_inverted:
            try:
                if img_to_process.mode == "RGBA":
                    r, g, b, a = img_to_process.split()
                    inv = ImageOps.invert(Image.merge("RGB", (r, g, b)))
                    r, g, b = inv.split()
                    img_to_process = Image.merge("RGBA", (r, g, b, a))
                else:
                    if img_to_process.mode != "RGB": img_to_process = img_to_process.convert("RGB")
                    img_to_process = ImageOps.invert(img_to_process)
            except Exception as e:
                print(f"Errore invert: {e}")

        if self.analysis_mode != "Normal":
            try:
                if img_to_process.mode == "RGBA": img_to_process = img_to_process.convert("RGB")
                if self.analysis_mode == "Equalize": img_to_process = ImageOps.equalize(img_to_process)
                elif self.analysis_mode == "Edge": img_to_process = img_to_process.filter(ImageFilter.FIND_EDGES)
            except Exception as e:
                print(f"Errore analisi: {e}")
        return img_to_process

    def redraw(self):
        self.canvas.delete("all")
        if not self.original_image: return
        img_to_process = self._apply_filters(self.original_image)
        width, height = img_to_process.size
        new_size = (int(width * self.scale), int(height * self.scale))
        if new_size[0] < 1 or new_size[1] < 1: return
        resample_method = Image.Resampling.NEAREST if self.scale > 2.0 else Image.Resampling.BILINEAR
        self.displayed_image = img_to_process.resize(new_size, resample_method)
        self.tk_image = ImageTk.PhotoImage(self.displayed_image)
        self.canvas.create_image(self.pan_x, self.pan_y, anchor="nw", image=self.tk_image)
        if self.show_grid: self._draw_grid(new_size[0], new_size[1])

    def _draw_grid(self, w, h):
        step = 50 * self.scale
        if step < 10: step = 10
        for i in range(0, int(w), int(step)):
            x = self.pan_x + i
            self.canvas.create_line(x, self.pan_y, x, self.pan_y + h, fill="#00ff00", stipple="gray50")
        for i in range(0, int(h), int(step)):
            y = self.pan_y + i
            self.canvas.create_line(self.pan_x, y, self.pan_x + w, y, fill="#00ff00", stipple="gray50")
        self.canvas.create_rectangle(self.pan_x, self.pan_y, self.pan_x + w, self.pan_y + h, outline="#ff0000")

    def get_pixel_data(self, canvas_x, canvas_y):
        if not self.original_image: return "Nessuna immagine"
        img_x = int((canvas_x - self.pan_x) / self.scale)
        img_y = int((canvas_y - self.pan_y) / self.scale)
        w, h = self.original_image.size
        if 0 <= img_x < w and 0 <= img_y < h:
            try:
                pixel = self.original_image.getpixel((img_x, img_y))
                if isinstance(pixel, int): r = g = b = pixel
                elif len(pixel) == 4: r, g, b = pixel[:3]
                else: r, g, b = pixel
                mode = self.channel_mode
                if mode == "RGB": return f"XY: {img_x},{img_y} | RGB: ({r}, {g}, {b})"
                elif mode == "HSV" or mode in ["H", "S", "V"]:
                    hh, ss, vv = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
                    return f"XY: {img_x},{img_y} | HSV: ({int(hh*360)}°, {int(ss*100)}%, {int(vv*100)}%)"
                elif mode == "YCbCr" or mode in ["Y", "Cb", "Cr"]:
                    y = int(0.299*r + 0.587*g + 0.114*b)
                    cb = int(128 - 0.168736*r - 0.331264*g + 0.5*b)
                    cr = int(128 + 0.5*r - 0.418688*g - 0.081312*b)
                    return f"XY: {img_x},{img_y} | YCbCr: ({y}, {cb}, {cr})"
                elif mode == "L": return f"XY: {img_x},{img_y} | L: {int(0.299*r + 0.587*g + 0.114*b)}"
                elif mode == "R": return f"XY: {img_x},{img_y} | R: {r}"
                elif mode == "G": return f"XY: {img_x},{img_y} | G: {g}"
                elif mode == "B": return f"XY: {img_x},{img_y} | B: {b}"
                return f"XY: {img_x},{img_y} | RGB: {r},{g},{b}"
            except Exception: return "Errore lettura"
        return "Fuori area"

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
        if not self.original_image: return
        zoom_factor = 1.1
        if event.num == 5 or event.delta < 0: self.scale /= zoom_factor
        else: self.scale *= zoom_factor
        self.redraw()