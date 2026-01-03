import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageOps, ImageFilter
import colorsys
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
                pixel = self.original_image.getpixel((ix, iy))
                return f"XY: {ix},{iy} | RGB: {pixel[:3]}"
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
        if self.tool_mode == "view":
            self.canvas.scan_mark(event.x, event.y)
            self._drag_start_x, self._drag_start_y = event.x, event.y
        elif self.tool_mode == "select":
            self.selection_start = (event.x, event.y)
            self.selection_points = [(event.x, event.y)]
            if self.selection_rect_id: self.canvas.delete(self.selection_rect_id)
            
            color = "#00ffff" # Cyan acceso
            if self.selection_shape == "rect":
                self.selection_rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline=color, width=2, dash=(4, 4))
            elif self.selection_shape == "oval":
                self.selection_rect_id = self.canvas.create_oval(event.x, event.y, event.x, event.y, outline=color, width=2, dash=(4, 4))
            elif self.selection_shape == "free":
                self.selection_rect_id = self.canvas.create_line(event.x, event.y, event.x, event.y, fill=color, width=2, dash=(4, 4), tags="free_line")
                
        elif self.tool_mode == "move_floating":
            self._drag_start_x, self._drag_start_y = event.x, event.y

    def on_mouse_drag(self, event):
        if self.tool_mode == "view":
            dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
            self.pan_x += dx
            self.pan_y += dy
            self._drag_start_x, self._drag_start_y = event.x, event.y
            self.redraw()
        elif self.tool_mode == "select":
            if self.selection_start:
                if self.selection_shape == "free":
                    self.selection_points.append((event.x, event.y))
                    # Aggiorna la linea a mano libera
                    flat_points = [p for sub in self.selection_points for p in sub]
                    self.canvas.coords(self.selection_rect_id, *flat_points)
                else:
                    x1, y1 = self.selection_start
                    self.canvas.coords(self.selection_rect_id, x1, y1, event.x, event.y)
        elif self.tool_mode == "move_floating":
            dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
            self.canvas.move(self.floating_image_id, dx, dy)
            self._drag_start_x, self._drag_start_y = event.x, event.y
            coords = self.canvas.coords(self.floating_image_id)
            self.floating_pos = (coords[0], coords[1])

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

    def refresh_floating_image(self):
        if not self.floating_pil_image: return
        if self.floating_image_id: self.canvas.delete(self.floating_image_id)
        w, h = self.floating_pil_image.size
        dw, dh = int(w * self.scale), int(h * self.scale)
        if dw > 0 and dh > 0:
            img_display = self.floating_pil_image.resize((dw, dh), Image.Resampling.BILINEAR)
            self.floating_tk_image = ImageTk.PhotoImage(img_display)
            if self.tool_mode == "select":
                self.floating_pos = self.image_to_canvas(self.selection_coords_img[0], self.selection_coords_img[1])
            self.floating_image_id = self.canvas.create_image(self.floating_pos[0], self.floating_pos[1], anchor="nw", image=self.floating_tk_image)

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
