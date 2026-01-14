import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps, ImageFilter
import colorsys
import math
from core.image_processor import ImageProcessor
from core.history_manager import HistoryManager

class ImageCanvas(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg="#2b2b2b", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.original_image = None
        self.displayed_image = None
        self.tk_image = None
        
        self.history = HistoryManager(max_steps=20)
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        self.tool_mode = "view"
        self.selection_shape = "rect" # rect, oval, free
        
        # Selezione / Copy-Move
        self.selection_start = None 
        self.selection_rect_id = None 
        self.selection_coords_img = None 
        self.selection_points = [] # Per freehand
        
        self.floating_pil_image = None
        self.floating_base_ref = None
        self.floating_tk_image = None
        self.floating_image_id = None
        self.floating_pos = (0, 0)
        self.floating_angle = 0
        self.floating_scale_val = 1.0

        self.show_grid = False
        self.is_inverted = False
        self.channel_mode = "RGB"
        self.analysis_mode = "Normal"

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<MouseWheel>", self.zoom_image)
        self.canvas.bind("<Button-4>", self.zoom_image)
        self.canvas.bind("<Button-5>", self.zoom_image)

    def set_image(self, pil_image):
        self.original_image = pil_image
        self.history = HistoryManager(max_steps=20)
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.fit_to_screen()
        self.redraw()
        
    def save_current_state(self):
        if self.original_image: self.history.push(self.original_image)

    def perform_undo(self, event=None):
        prev_img = self.history.undo(self.original_image)
        if prev_img:
            self.original_image = prev_img
            self.redraw()

    def perform_redo(self, event=None):
        next_img = self.history.redo(self.original_image)
        if next_img:
            self.original_image = next_img
            self.redraw()

    def fit_to_screen(self):
        if not self.original_image: return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10: cw, ch = 800, 600
        iw, ih = self.original_image.size
        self.scale = min(cw / iw, ch / ih) * 0.9
        self.pan_x = (cw - int(iw * self.scale)) // 2
        self.pan_y = (ch - int(ih * self.scale)) // 2
        self.redraw()
    
    def set_zoom_1_to_1(self):
        if not self.original_image: return
        self.scale = 1.0
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        iw, ih = self.original_image.size
        self.pan_x, self.pan_y = (cw - iw) // 2, (ch - ih) // 2
        self.redraw()

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.redraw()

    def set_channel_mode(self, mode):
        self.channel_mode = mode
        self.redraw()
        
    def set_analysis_mode(self, mode):
        self.analysis_mode = "Normal" if self.analysis_mode == mode else mode
        self.redraw()
        return self.analysis_mode

    def toggle_invert(self):
        self.is_inverted = not self.is_inverted
        self.redraw()

    def get_current_processed_image(self):
        if not self.original_image: return None
        return self._apply_filters(self.original_image)

    def _apply_filters(self, img):
        img_to_process = img.convert("RGB") if img.mode not in ["RGB", "RGBA"] else img.copy()
        mode = self.channel_mode
        try:
            if mode in ["R", "G", "B"]:
                r, g, b = img_to_process.convert("RGB").split()
                zero = Image.new("L", r.size, 0)
                if mode == "R": img_to_process = Image.merge("RGB", (r, zero, zero))
                elif mode == "G": img_to_process = Image.merge("RGB", (zero, g, zero))
                elif mode == "B": img_to_process = Image.merge("RGB", (zero, zero, b))
            elif mode in ["H", "S", "V"]:
                h, s, v = img_to_process.convert("HSV").split()
                if mode == "H": img_to_process = h.convert("RGB")
                elif mode == "S": img_to_process = s.convert("RGB")
                elif mode == "V": img_to_process = v.convert("RGB")
            elif mode in ["YCbCr", "Y", "Cb", "Cr"]:
                y, cb, cr = img_to_process.convert("YCbCr").split()
                if mode == "YCbCr": img_to_process = Image.merge("RGB", (y, cb, cr))
                elif mode == "Y": img_to_process = y.convert("RGB")
                elif mode == "Cb": img_to_process = cb.convert("RGB")
                elif mode == "Cr": img_to_process = cr.convert("RGB")
            elif mode == "L": img_to_process = img_to_process.convert("L").convert("RGB")
        except: pass

        if self.is_inverted:
            try: img_to_process = ImageOps.invert(img_to_process.convert("RGB"))
            except: pass

        if self.analysis_mode != "Normal":
            try:
                if self.analysis_mode == "Equalize": img_to_process = ImageOps.equalize(img_to_process.convert("RGB"))
                elif self.analysis_mode == "Edge": img_to_process = img_to_process.convert("RGB").filter(ImageFilter.FIND_EDGES)
                elif self.analysis_mode == "ELA": img_to_process = ImageProcessor.compute_ela(img_to_process)
            except: pass
        return img_to_process

    def redraw(self):
        self.canvas.delete("all")
        if not self.original_image: return
        img_to_process = self._apply_filters(self.original_image)
        width, height = img_to_process.size
        new_size = (int(width * self.scale), int(height * self.scale))
        if new_size[0] < 1 or new_size[1] < 1: return
        resample = Image.Resampling.NEAREST if self.scale > 2.0 else Image.Resampling.BILINEAR
        self.displayed_image = img_to_process.resize(new_size, resample)
        self.tk_image = ImageTk.PhotoImage(self.displayed_image)
        self.canvas.create_image(self.pan_x, self.pan_y, anchor="nw", image=self.tk_image)
        if self.show_grid: self._draw_grid(new_size[0], new_size[1])

    def _draw_grid(self, w, h):
        step = max(10, 50 * self.scale)
        for i in range(0, int(w), int(step)):
            x = self.pan_x + i
            self.canvas.create_line(x, self.pan_y, x, self.pan_y + h, fill="#00ff00", stipple="gray50")
        for i in range(0, int(h), int(step)):
            y = self.pan_y + i
            self.canvas.create_line(self.pan_x, y, self.pan_x + w, y, fill="#00ff00", stipple="gray50")

    def get_pixel_data(self, canvas_x, canvas_y):
        if not self.original_image: return "No image"
        ix, iy = self.canvas_to_image(canvas_x, canvas_y)
        w, h = self.original_image.size
        if 0 <= ix < w and 0 <= iy < h:
            try:
                mode = self.channel_mode
                label = mode
                vals = ""
                
                if mode == "RGB":
                    p = self.original_image.convert("RGB").getpixel((ix, iy))
                    vals = f"{p[0]},{p[1]},{p[2]}"
                elif mode in ["R", "G", "B"]:
                    p = self.original_image.convert("RGB").getpixel((ix, iy))
                    idx = ["R", "G", "B"].index(mode)
                    vals = f"{p[idx]}"
                elif mode == "HSV":
                    p = self.original_image.convert("HSV").getpixel((ix, iy))
                    vals = f"{p[0]},{p[1]},{p[2]}"
                elif mode in ["H", "S", "V"]:
                    p = self.original_image.convert("HSV").getpixel((ix, iy))
                    idx = ["H", "S", "V"].index(mode)
                    vals = f"{p[idx]}"
                elif mode == "YCbCr":
                    p = self.original_image.convert("YCbCr").getpixel((ix, iy))
                    vals = f"{p[0]},{p[1]},{p[2]}"
                elif mode in ["Y", "Cb", "Cr"] or mode == "L":
                    # Note: L is often handled as Y in YCbCr or separate Grayscale
                    if mode == "L": 
                         p = self.original_image.convert("L").getpixel((ix, iy))
                         vals = f"{p}"
                    else:
                        p = self.original_image.convert("YCbCr").getpixel((ix, iy))
                        idx = ["Y", "Cb", "Cr"].index(mode)
                        vals = f"{p[idx]}"
                else:
                    # Fallback
                    p = self.original_image.convert("RGB").getpixel((ix, iy))
                    vals = f"{p[0]},{p[1]},{p[2]}"

                return f"XY: {ix},{iy} | {label}: {vals}"
            except: return "Error"
        return "Outside"

    def set_tool_mode(self, mode):
        self.tool_mode = mode
        self.canvas.config(cursor="crosshair" if mode == "select" else "")
        if mode == "view": self.clear_selection()

    def set_selection_shape(self, shape):
        self.selection_shape = shape
        self.clear_selection()
        if self.tool_mode != "view": self.set_tool_mode("select")

    def clear_selection(self):
        if self.selection_rect_id: self.canvas.delete(self.selection_rect_id)
        if self.floating_image_id: self.canvas.delete(self.floating_image_id)
        self.selection_rect_id = self.floating_image_id = None
        self.floating_pil_image = self.floating_base_ref = None
        if self.tool_mode == "move_floating": self.tool_mode = "view"

    def canvas_to_image(self, cx, cy):
        if not self.original_image: return 0, 0
        return int((cx - self.pan_x) / self.scale), int((cy - self.pan_y) / self.scale)

    def image_to_canvas(self, ix, iy):
        return int(ix * self.scale) + self.pan_x, int(iy * self.scale) + self.pan_y

    def on_mouse_down(self, event):
        self._drag_start_x, self._drag_start_y = event.x, event.y
        
        if self.tool_mode == "view":
            self.canvas.scan_mark(event.x, event.y)
            
        elif self.tool_mode == "select":
            self.selection_start = (event.x, event.y)
            self.selection_points = [(event.x, event.y)]
            if self.selection_rect_id: self.canvas.delete(self.selection_rect_id)
            
            color = "#00ffff"
            if self.selection_shape == "rect":
                self.selection_rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline=color, width=2, dash=(4, 4))
            elif self.selection_shape == "oval":
                self.selection_rect_id = self.canvas.create_oval(event.x, event.y, event.x, event.y, outline=color, width=2, dash=(4, 4))
            elif self.selection_shape == "free":
                self.selection_rect_id = self.canvas.create_line(event.x, event.y, event.x, event.y, fill=color, width=2, dash=(4, 4), tags="free_line")
                
        elif self.tool_mode == "move_floating":
            # Check if clicked on a handle
            clicked = self.canvas.find_overlapping(event.x-2, event.y-2, event.x+2, event.y+2)
            tags = []
            for item in clicked:
                tags.extend(self.canvas.gettags(item))
            
            self._interaction_mode = "move" # default
            
            if "handle_rot" in tags:
                self._interaction_mode = "rotate"
                # Calcola angolo iniziale del click
                w, h = self.floating_pil_image.size
                dw, dh = int(w * self.scale), int(h * self.scale)
                cx = self.floating_pos[0] + dw / 2
                cy = self.floating_pos[1] + dh / 2
                self._start_angle_ref = math.degrees(math.atan2(event.y - cy, event.x - cx))
                self._base_angle = self.floating_angle
                
            elif "handle" in tags: # Any resize handle
                self._interaction_mode = "scale"
                # Salva distanza iniziale dal centro
                w, h = self.floating_pil_image.size
                dw, dh = int(w * self.scale), int(h * self.scale)
                cx = self.floating_pos[0] + dw / 2
                cy = self.floating_pos[1] + dh / 2
                self._start_dist = math.hypot(event.x - cx, event.y - cy)
                self._base_scale = self.floating_scale_val
                self._center_ref = (cx, cy)
            
            else:
                self._interaction_mode = "move"
                self._start_pos = self.floating_pos

    def on_mouse_drag(self, event):
        if self.tool_mode == "view":
            dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
            self.pan_x += dx
            self.pan_y += dy
            self._drag_start_x, self._drag_start_y = event.x, event.y
            self.redraw()
            
        elif self.tool_mode == "select" and self.selection_start:
            if self.selection_shape == "free":
                self.selection_points.append((event.x, event.y))
                flat_points = [p for sub in self.selection_points for p in sub]
                self.canvas.coords(self.selection_rect_id, *flat_points)
            else:
                x1, y1 = self.selection_start
                self.canvas.coords(self.selection_rect_id, x1, y1, event.x, event.y)
                
        elif self.tool_mode == "move_floating":
            
            if self._interaction_mode == "move":
                dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
                self.floating_pos = (self._start_pos[0] + (event.x - self._drag_start_x), 
                                     self._start_pos[1] + (event.y - self._drag_start_y))
                
                # Muovi tutto (immagine e overlay)
                self.refresh_floating_image()
                
            elif self._interaction_mode == "scale":
                cx, cy = self._center_ref
                cur_dist = math.hypot(event.x - cx, event.y - cy)
                if self._start_dist > 0:
                    ratio = cur_dist / self._start_dist
                    new_scale = self._base_scale * ratio
                    # Limiti di sicurezza
                    new_scale = max(0.1, min(new_scale, 5.0))
                    
                    # Centered scaling logic:
                    # 1. Update scale value
                    self.floating_scale_val = new_scale
                    
                    # 2. Recalculate image
                    self.apply_transformations(scale_percent=None) # Use internal values
                    
                    # 3. Re-center: apply_transformations changed the size, so top-left floating_pos must shift
                    # to keep the center at cx, cy
                    w, h = self.floating_pil_image.size
                    dw, dh = int(w * self.scale), int(h * self.scale)
                    self.floating_pos = (cx - dw/2, cy - dh/2)
                    
                    self.refresh_floating_image()
                    
            elif self._interaction_mode == "rotate":
                # Calcola centro dinamicamente
                w, h = self.floating_pil_image.size
                dw, dh = int(w * self.scale), int(h * self.scale)
                cx = self.floating_pos[0] + dw / 2
                cy = self.floating_pos[1] + dh / 2
                
                cur_angle = math.degrees(math.atan2(event.y - cy, event.x - cx))
                delta = cur_angle - self._start_angle_ref
                
                self.floating_angle = self._base_angle + delta
                
                # Come per scale, la rotazione cambia il bounding box (expand=True), quindi dobbiamo ricentrare
                self.apply_transformations(angle=None)
                
                w_new, h_new = self.floating_pil_image.size
                dw_new, dh_new = int(w_new * self.scale), int(h_new * self.scale)
                self.floating_pos = (cx - dw_new/2, cy - dh_new/2)
                
                self.refresh_floating_image()

    def on_mouse_move(self, event):
        # Gestione cursore
        if self.tool_mode == "move_floating":
            # Check overlap con tolleranza
            clicked = self.canvas.find_overlapping(event.x-2, event.y-2, event.x+2, event.y+2)
            tags = []
            for item in clicked:
                tags.extend(self.canvas.gettags(item))
                
            if "handle_rot" in tags:
                self.canvas.config(cursor="exchange") # O altro cursore rotazione
            elif "handle" in tags:
                self.canvas.config(cursor="sizing") # O doppio arrow
            else:
                self.canvas.config(cursor="fleur")
        elif self.tool_mode == "select":
             self.canvas.config(cursor="crosshair")
        else:
             self.canvas.config(cursor="")

    def on_mouse_up(self, event):
        if self.tool_mode == "select" and self.selection_start:
            if self.selection_shape == "free":
                if len(self.selection_points) < 3: return
                # Chiudi il poligono visivamente
                self.selection_points.append(self.selection_points[0])
                flat_points = [p for sub in self.selection_points for p in sub]
                self.canvas.coords(self.selection_rect_id, *flat_points)
                
                # Calcola bounding box per il crop
                xs = [p[0] for p in self.selection_points]
                ys = [p[1] for p in self.selection_points]
                cx1, cx2, cy1, cy2 = min(xs), max(xs), min(ys), max(ys)
            else:
                x1, y1 = self.selection_start
                x2, y2 = event.x, event.y
                cx1, cx2, cy1, cy2 = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
            
            if cx2 - cx1 < 5: return
            
            ix1, iy1 = self.canvas_to_image(cx1, cy1)
            ix2, iy2 = self.canvas_to_image(cx2, cy2)
            w, h = self.original_image.size
            self.selection_coords_img = (max(0, ix1), max(0, iy1), min(w, ix2), min(h, iy2))
            
            self.create_floating_from_selection()
            
        self._interaction_mode = None

    def create_floating_from_selection(self):
        if not self.selection_coords_img: return
        cropped = self.original_image.crop(self.selection_coords_img)
        
        # Gestione Maschere (Oval / Free)
        if self.selection_shape in ["oval", "free"]:
            mask = Image.new("L", cropped.size, 0)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(mask)
            
            if self.selection_shape == "oval":
                draw.ellipse((0, 0) + cropped.size, fill=255)
            elif self.selection_shape == "free":
                # Converti i punti canvas in punti relativi all'immagine ritagliata
                ix1, iy1, _, _ = self.selection_coords_img
                rel_points = []
                for px, py in self.selection_points:
                    img_px, img_py = self.canvas_to_image(px, py)
                    rel_points.append((img_px - ix1, img_py - iy1))
                draw.polygon(rel_points, fill=255)
            
            cropped = cropped.convert("RGBA")
            cropped.putalpha(mask)
            
        self.floating_base_ref = cropped
        self.floating_pil_image = cropped.copy()
        self.floating_angle = 0
        self.floating_scale_val = 1.0
        
        if self.selection_rect_id: self.canvas.delete(self.selection_rect_id)
        self.refresh_floating_image()
        self.tool_mode = "move_floating"
        self.canvas.config(cursor="fleur")


    def set_floating_image_from_external(self, pil_image):
        """
        Carica un'immagine esterna come layer fluttuante per lo Splicing.
        """
        if not pil_image or not self.original_image: return

        # Reset selezione interna
        self.selection_coords_img = None
        self.selection_rect_id = None
        
        # Imposta subito la modalità per evitare conflitti nel refresh
        self.tool_mode = "move_floating"
        self.canvas.config(cursor="fleur")

        # Converti e prepara
        self.floating_base_ref = pil_image.convert("RGBA")
        self.floating_pil_image = self.floating_base_ref.copy()
        self.floating_angle = 0
        self.floating_scale_val = 1.0
        
        # Calcola dimensioni e posizione iniziali (Centrato)
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        cx, cy = cw // 2, ch // 2
        w, h = pil_image.size
        
        # Scala iniziale se l'immagine è troppo grande
        if w > cw or h > ch:
             self.floating_scale_val = min(cw/w, ch/h) * 0.5

        # Calcola la posizione centrata BASATA sullo scale appena deciso
        # Nota: il refresh userà floating_pos
        dw = int(w * self.scale * self.floating_scale_val)
        dh = int(h * self.scale * self.floating_scale_val)
        self.floating_pos = (cx - dw//2, cy - dh//2)

        # Ora applica le trasformazioni (che chiamerà refresh_floating_image usando pos e scale corretti)
        self.apply_transformations()

    def apply_transformations(self, scale_percent=None, angle=None):
        if self.floating_base_ref is None: return
        if scale_percent is not None: self.floating_scale_val = float(scale_percent) / 100.0
        if angle is not None: self.floating_angle = float(angle)
        
        w, h = self.floating_base_ref.size
        new_w, new_h = max(1, int(w * self.floating_scale_val)), max(1, int(h * self.floating_scale_val))
        transformed = self.floating_base_ref.resize((new_w, new_h), Image.Resampling.LANCZOS)
        if self.floating_angle != 0:
            transformed = transformed.rotate(self.floating_angle, resample=Image.Resampling.BICUBIC, expand=True)
        self.floating_pil_image = transformed
        self.refresh_floating_image()

    def _get_corners(self, w, h, angle_deg, cx, cy):
        """Calcola i 4 angoli dell'immagine ruotata rispetto al centro cx,cy."""
        rad = math.radians(angle_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        # Coordinate relative al centro (metà larghezza, metà altezza)
        hw, hh = w / 2.0, h / 2.0
        
        # 4 vertici: TL, TR, BR, BL
        # Nota: in canvas Y cresce verso il basso
        corners = [
            (-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)
        ]
        
        rotated_corners = []
        for x, y in corners:
            # Rotazione 2D
            rx = x * cos_a - y * sin_a
            ry = x * sin_a + y * cos_a
            rotated_corners.append((cx + rx, cy + ry))
            
        return rotated_corners

    def refresh_floating_image(self):
        # Pulisce i vecchi elementi grafici dell'overlay
        self.canvas.delete("overlay_ui")
        
        if not self.floating_pil_image: return
        if self.floating_image_id: self.canvas.delete(self.floating_image_id)
        
        # 1. Disegna l'immagine
        w, h = self.floating_pil_image.size
        dw, dh = int(w * self.scale), int(h * self.scale)
        
        if dw > 0 and dh > 0:
            img_display = self.floating_pil_image.resize((dw, dh), Image.Resampling.BILINEAR)
            self.floating_tk_image = ImageTk.PhotoImage(img_display)
            
            # Se siamo in fase di spostamento/select, la posizione è definita.
            # Altrimenti, calcoliamo la posizione per centrare l'immagine se necessario, 
            # ma qui assumiamo che self.floating_pos sia l'angolo Top-Left del bounding box NON RUOTATO.
            # Tuttavia, con la rotazione, floating_pos diventa ambiguo. 
            # Convenzione: self.floating_pos è sempre l'angolo Top-Left del rettangolo che contiene l'immagine (visuale).
            
            # Aggiorna posizione solo se siamo in modalità selezione attiva con coordinate valide
            if self.tool_mode == "select" and self.selection_coords_img:
                self.floating_pos = self.image_to_canvas(self.selection_coords_img[0], self.selection_coords_img[1])

            self.floating_image_id = self.canvas.create_image(
                self.floating_pos[0], self.floating_pos[1], 
                anchor="nw", image=self.floating_tk_image
            )
            
            # 2. Se siamo in modalità di modifica (move_floating), disegna le maniglie
            if self.tool_mode == "move_floating":
                # Calcoliamo il centro attuale dell'immagine visualizzata
                # L'immagine visualizzata da PIL è già ruotata e include il padding trasparente?
                # Se floating_pil_image è il risultato di rotate(expand=True), allora floating_pos è il top-left del bounding box.
                # Il centro reale dell'immagine è semplicemente al centro di dw, dh
                cx = self.floating_pos[0] + dw / 2
                cy = self.floating_pos[1] + dh / 2
                
                # Per disegnare le maniglie correttamente orientate, dobbiamo sapere le dimensioni originali (pre-rotazione) scalate
                # Ma floating_pil_image è GIA' ruotata. Questo complica le cose.
                # APPROCCIO SEMPLIFICATO: Disegniamo un box attorno all'immagine corrente (che è il bounding box dell'immagine ruotata)
                # Questo è lo stile standard quando si usa rotate(expand=True).
                
                # Disegna Box Contenitore
                rect_coords = (
                    self.floating_pos[0], self.floating_pos[1],
                    self.floating_pos[0] + dw, self.floating_pos[1] + dh
                )
                self.canvas.create_rectangle(*rect_coords, outline="#00ffff", width=1, tags="overlay_ui")
                
                # Maniglie Angolari (Resize)
                handle_size = 8
                corners = [
                    (rect_coords[0], rect_coords[1]), # TL
                    (rect_coords[2], rect_coords[1]), # TR
                    (rect_coords[2], rect_coords[3]), # BR
                    (rect_coords[0], rect_coords[3])  # BL
                ]
                tags = ["handle_tl", "handle_tr", "handle_br", "handle_bl"]
                
                for i, (hx, hy) in enumerate(corners):
                    self.canvas.create_rectangle(
                        hx - handle_size/2, hy - handle_size/2,
                        hx + handle_size/2, hy + handle_size/2,
                        fill="white", outline="#00ffff", tags=("overlay_ui", "handle", tags[i])
                    )
                
                # Maniglia Rotazione (Top)
                # La posizioniamo sopra il lato superiore
                top_mid_x = (rect_coords[0] + rect_coords[2]) / 2
                top_mid_y = rect_coords[1]
                rot_handle_y = top_mid_y - 20
                
                self.canvas.create_line(top_mid_x, top_mid_y, top_mid_x, rot_handle_y, fill="#00ffff", tags="overlay_ui")
                self.canvas.create_oval(
                    top_mid_x - 5, rot_handle_y - 5,
                    top_mid_x + 5, rot_handle_y + 5,
                    fill="#00ffff", tags=("overlay_ui", "handle_rot")
                )

    def apply_paste(self):
        if not self.original_image or not self.floating_pil_image: return
        self.save_current_state()
        ix, iy = self.canvas_to_image(*self.floating_pos)
        if self.floating_pil_image.mode == "RGBA":
            self.original_image.paste(self.floating_pil_image, (ix, iy), self.floating_pil_image)
        else:
            self.original_image.paste(self.floating_pil_image, (ix, iy))
        self.clear_selection()
        self.redraw()
        self.set_tool_mode("select") 

    def update_floating_image(self, new_image):
        if new_image:
            self.floating_base_ref = new_image
            self.apply_transformations()

    def trigger_feathering(self):
        if self.floating_pil_image:
            self.floating_base_ref = ImageProcessor.apply_feathering(self.floating_base_ref, radius=2)
            self.apply_transformations()

    def zoom_image(self, event):
        if not self.original_image: return
        zoom_factor = 1.03
        if event.num == 5 or event.delta < 0: self.scale /= zoom_factor
        else: self.scale *= zoom_factor
        self.redraw()
