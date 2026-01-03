import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps, ImageFilter
import colorsys
from core.image_processor import ImageProcessor
from core.history_manager import HistoryManager

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
        self.original_image = None  # PIL Image originale (Base modificabile)
        self.displayed_image = None # PIL Image scalata
        self.tk_image = None        # Immagine compatibile Tkinter
        
        self.history = HistoryManager(max_steps=20)
        
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        # Tools state
        self.tool_mode = "view" # view, select, move_floating
        self.selection_shape = "rect" # rect, oval
        
        # Selezione / Copy-Move
        self.selection_start = None # (x, y) canvas coords
        self.selection_rect_id = None # ID rettangolo selezione
        self.selection_coords_img = None # (x1, y1, x2, y2) image coords
        
        self.floating_pil_image = None # L'immagine ritagliata (in memoria corrente)
        self.floating_tk_image = None  # L'immagine ritagliata (per display)
        self.floating_image_id = None  # ID oggetto canvas image
        self.floating_pos = (0, 0)     # Posizione attuale top-left (canvas coords)

        self.show_grid = False
        self.is_inverted = False
        self.channel_mode = "RGB" # RGB, R, G, B, H, S, V, L, Y, Cb, Cr
        self.analysis_mode = "Normal" # Normal, Equalize, Edge, ELA

        # Eventi Mouse
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        self.canvas.bind("<MouseWheel>", self.zoom_image) # Windows/MacOS
        self.canvas.bind("<Button-4>", self.zoom_image)   # Linux Scroll Up
        self.canvas.bind("<Button-5>", self.zoom_image)   # Linux Scroll Down

    def set_image(self, pil_image):
        """Imposta una nuova immagine e resetta la vista."""
        self.original_image = pil_image
        self.history = HistoryManager(max_steps=20) # Reset history per nuova immagine
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.fit_to_screen()
        self.redraw()
        
    def save_current_state(self):
        """Salva lo stato corrente PRIMA di una modifica."""
        if self.original_image:
            self.history.push(self.original_image)

    def perform_undo(self, event=None):
        prev_img = self.history.undo(self.original_image)
        if prev_img:
            self.original_image = prev_img
            self.redraw()
            print("Undo effettuato")

    def perform_redo(self, event=None):
        next_img = self.history.redo(self.original_image)
        if next_img:
            self.original_image = next_img
            self.redraw()
            print("Redo effettuato")

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
                if self.analysis_mode == "Equalize": 
                    img_to_process = ImageOps.equalize(img_to_process)
                elif self.analysis_mode == "Edge": 
                    img_to_process = img_to_process.filter(ImageFilter.FIND_EDGES)
                elif self.analysis_mode == "ELA":
                    img_to_process = ImageProcessor.compute_ela(img_to_process)
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

    def set_tool_mode(self, mode):
        self.tool_mode = mode
        if mode == "view":
            self.canvas.config(cursor="")
            self.clear_selection()
        elif mode == "select":
            self.canvas.config(cursor="crosshair")

    def set_selection_shape(self, shape):
        self.selection_shape = shape
        self.clear_selection()
        if self.tool_mode != "view":
            self.set_tool_mode("select")

    def clear_selection(self):
        """Pulisce selezioni e immagini fluttuanti senza applicarle."""
        if self.selection_rect_id: self.canvas.delete(self.selection_rect_id)
        if self.floating_image_id: self.canvas.delete(self.floating_image_id)
        self.selection_rect_id = None
        self.floating_image_id = None
        self.floating_pil_image = None
        self.selection_coords_img = None
        self.tool_mode = "view" if self.tool_mode == "move_floating" else self.tool_mode

    # --- Conversione Coordinate ---
    def canvas_to_image(self, cx, cy):
        if not self.original_image: return 0, 0
        ix = int((cx - self.pan_x) / self.scale)
        iy = int((cy - self.pan_y) / self.scale)
        return ix, iy

    def image_to_canvas(self, ix, iy):
        cx = int(ix * self.scale) + self.pan_x
        cy = int(iy * self.scale) + self.pan_y
        return cx, cy

    # --- Gestione Eventi Mouse ---
    def on_mouse_down(self, event):
        if self.tool_mode == "view":
            self.start_pan(event)
        elif self.tool_mode == "select":
            # Inizia selezione
            self.selection_start = (event.x, event.y)
            if self.selection_rect_id: self.canvas.delete(self.selection_rect_id)
            
            if self.selection_shape == "rect":
                self.selection_rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="yellow", width=2, dash=(4, 2))
            elif self.selection_shape == "oval":
                self.selection_rect_id = self.canvas.create_oval(event.x, event.y, event.x, event.y, outline="cyan", width=2, dash=(4, 2))
                
        elif self.tool_mode == "move_floating":
            # Inizia spostamento immagine incollata
            self._drag_start_x = event.x
            self._drag_start_y = event.y

    def on_mouse_drag(self, event):
        if self.tool_mode == "view":
            self.pan_image(event)
        elif self.tool_mode == "select":
            # Aggiorna forma selezione
            if self.selection_start and self.selection_rect_id:
                x1, y1 = self.selection_start
                self.canvas.coords(self.selection_rect_id, x1, y1, event.x, event.y)
        elif self.tool_mode == "move_floating":
            # Sposta l'immagine fluttuante
            dx = event.x - self._drag_start_x
            dy = event.y - self._drag_start_y
            self.canvas.move(self.floating_image_id, dx, dy)
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            
            # Aggiorna posizione salvata
            coords = self.canvas.coords(self.floating_image_id)
            self.floating_pos = (coords[0], coords[1])

    def on_mouse_up(self, event):
        if self.tool_mode == "select":
            # Finalizza selezione
            if not self.selection_start: return
            x1, y1 = self.selection_start
            x2, y2 = event.x, event.y
            
            # Normalizza coords
            cx1, cx2 = min(x1, x2), max(x1, x2)
            cy1, cy2 = min(y1, y2), max(y1, y2)
            
            # Se troppo piccolo, ignora
            if cx2 - cx1 < 5 or cy2 - cy1 < 5:
                self.clear_selection()
                return

            # Converti in coordinate immagine reale
            ix1, iy1 = self.canvas_to_image(cx1, cy1)
            ix2, iy2 = self.canvas_to_image(cx2, cy2)
            
            # Clamp ai bordi immagine
            w, h = self.original_image.size
            ix1, iy1 = max(0, ix1), max(0, iy1)
            ix2, iy2 = min(w, ix2), min(h, iy2)
            
            self.selection_coords_img = (ix1, iy1, ix2, iy2)
            self.create_floating_from_selection()

    def create_floating_from_selection(self):
        if not self.selection_coords_img or not self.original_image: return
        
        # Ritaglia il bounding box rettangolare
        cropped_img = self.original_image.crop(self.selection_coords_img)
        
        # Se è Ovale, applichiamo una maschera alpha
        if self.selection_shape == "oval":
            w, h = cropped_img.size
            mask = Image.new("L", (w, h), 0) # Nero = Trasparente
            from PIL import ImageDraw
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, w, h), fill=255) # Bianco = Opaco
            
            if cropped_img.mode != "RGBA":
                cropped_img = cropped_img.convert("RGBA")
            cropped_img.putalpha(mask)
            
        self.floating_pil_image = cropped_img
        
        # Rimuovi la selezione grafica
        if self.selection_rect_id: self.canvas.delete(self.selection_rect_id)
        
        # Mostra oggetto fluttuante sul canvas
        self.refresh_floating_image()
        
        # Passa a modalità spostamento
        self.tool_mode = "move_floating"
        self.canvas.config(cursor="fleur")

    def refresh_floating_image(self):
        """Ridisegna l'immagine fluttuante alla scala corretta."""
        if not self.floating_pil_image: return
        
        if self.floating_image_id: self.canvas.delete(self.floating_image_id)
        
        # Scala per visualizzazione
        w, h = self.floating_pil_image.size
        new_w, new_h = int(w * self.scale), int(h * self.scale)
        
        if new_w > 0 and new_h > 0:
            resample = Image.Resampling.NEAREST if self.scale > 2.0 else Image.Resampling.BILINEAR
            img_display = self.floating_pil_image.resize((new_w, new_h), resample)
            self.floating_tk_image = ImageTk.PhotoImage(img_display)
            
            if self.tool_mode == "select": 
                ox, oy = self.image_to_canvas(self.selection_coords_img[0], self.selection_coords_img[1])
                self.floating_pos = (ox, oy)
            
            self.floating_image_id = self.canvas.create_image(self.floating_pos[0], self.floating_pos[1], anchor="nw", image=self.floating_tk_image)

    def apply_paste(self):
        """Incolla definitivamente l'immagine fluttuante sull'originale."""
        if not self.original_image or not self.floating_pil_image or not self.floating_image_id:
            return

        self.save_current_state()
        
        # Calcola posizione finale in coordinate immagine
        cx, cy = self.canvas.coords(self.floating_image_id)
        ix, iy = self.canvas_to_image(cx, cy)
        
        # Incolla con maschera se presente (es. Ovale)
        if self.floating_pil_image.mode == "RGBA":
            self.original_image.paste(self.floating_pil_image, (ix, iy), self.floating_pil_image)
        else:
            self.original_image.paste(self.floating_pil_image, (ix, iy))
        
        # Pulisci UI
        self.clear_selection()
        self.redraw()
        print("Pasted!")
        
        # Torna a select
        self.set_tool_mode("select") 

    def update_floating_image(self, new_image):
        """Aggiorna l'immagine fluttuante con una processata esternamente."""
        if new_image:
            self.floating_pil_image = new_image
            self.refresh_floating_image()

    def trigger_feathering(self):
        if self.floating_pil_image:
            self.floating_pil_image = ImageProcessor.apply_feathering(self.floating_pil_image, radius=2)
            self.refresh_floating_image()

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
