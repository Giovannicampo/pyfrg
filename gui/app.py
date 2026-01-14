import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image
from core.image_processor import ImageProcessor
from gui.canvas_widget import ImageCanvas
from gui.tooltip import CTkToolTip
import os
import threading

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ChannelSelector(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Select Channel")
        self.geometry("300x600")
        self.callback = callback
        self.attributes("-topmost", True)
        
        ctk.CTkLabel(self, text="Color Spaces", font=("Arial", 16, "bold")).pack(pady=10)
        
        modes = [
            ("RGB (Original)", "RGB"),
            ("Red (R)", "R"), ("Green (G)", "G"), ("Blue (B)", "B"),
            ("---", None),
            ("HSV (Analysis)", "HSV"), ("Hue", "H"), ("Saturation", "S"), ("Value", "V"),
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

        # Layout Core
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Logo
        self.logo_label = ctk.CTkLabel(self.sidebar, text="  pyfrg", font=("Arial", 24, "bold"), text_color="#7A0202")
        try:
            if os.path.exists("assets/logo.png"):
                logo_img = ctk.CTkImage(light_image=Image.open("assets/logo.png"), 
                                      dark_image=Image.open("assets/logo.png"), 
                                      size=(40, 40))
                self.logo_label.configure(image=logo_img, compound="left")
        except Exception as e:
            print(f"Could not load logo: {e}")
            
        self.logo_label.pack(padx=20, pady=20)

        # UI Components
        self.setup_sidebar_buttons()

        # --- MAIN AREA ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        self.image_canvas = ImageCanvas(self.main_container)
        self.image_canvas.grid(row=1, column=0, sticky="nsew")

        self.toolbar = ctk.CTkFrame(self.main_container, height=50)
        self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.setup_toolbar()

        self.metadata_view = ctk.CTkScrollableFrame(self.main_container, fg_color="#1a1a1a")

        self.status_bar = ctk.CTkFrame(self.main_container, height=25)
        self.status_bar.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        
        self.lbl_file = ctk.CTkLabel(self.status_bar, text="No file loaded", font=("Arial", 11))
        self.lbl_file.pack(side="left", padx=10)

        self.pixel_info = ctk.CTkLabel(self.status_bar, text="X: - Y: - | RGB: -", font=("Consolas", 11))
        self.pixel_info.pack(side="right", padx=20)

        # Bindings
        self.image_canvas.canvas.bind("<Motion>", self.on_mouse_move)
        self.bind("<Control-z>", lambda e: self.image_canvas.perform_undo())
        self.bind("<Control-y>", lambda e: self.image_canvas.perform_redo())
        self.bind("<Control-plus>", lambda e: self.zoom(1.2))
        self.bind("<Control-minus>", lambda e: self.zoom(0.8))
        self.bind("<Control-equal>", lambda e: self.zoom(1.2))
        
        self.show_page("view")

    def setup_sidebar_buttons(self):
        btn_style = {"height": 35, "fg_color": "transparent", "hover_color": "#8B0000", "anchor": "w", "corner_radius": 0}
        
        self.btn_load = ctk.CTkButton(self.sidebar, text="  Load Image", command=self.load_image, **btn_style)
        self.btn_load.pack(fill="x", pady=2)
        
        self.btn_view = ctk.CTkButton(self.sidebar, text="  View", command=lambda: self.show_page("view"), **btn_style)
        self.btn_view.pack(fill="x", pady=2)
        
        self.btn_meta = ctk.CTkButton(self.sidebar, text="  Metadata", command=lambda: self.show_page("meta"), **btn_style)
        self.btn_meta.pack(fill="x", pady=2)

        self.btn_forge = ctk.CTkButton(self.sidebar, text="  Forgery Tools", command=lambda: self.show_page("forge"), **btn_style)
        self.btn_forge.pack(fill="x", pady=2)

    def show_page(self, page):
        self.btn_view.configure(fg_color="#8B0000" if page=="view" else "transparent")
        self.btn_meta.configure(fg_color="#8B0000" if page=="meta" else "transparent")
        self.btn_forge.configure(fg_color="#8B0000" if page=="forge" else "transparent")
        
        self.metadata_view.grid_forget()
        self.toolbar.grid_forget()
        self.image_canvas.grid_forget()
        if hasattr(self, 'forge_frame'): self.forge_frame.grid_forget()

        if page == "view":
            self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
            self.image_canvas.grid(row=1, column=0, sticky="nsew")
            self.image_canvas.set_tool_mode("view")
        elif page == "meta":
            self.metadata_view.grid(row=0, column=0, rowspan=2, sticky="nsew")
            self.update_metadata_ui()
        elif page == "forge":
            self.image_canvas.grid(row=1, column=0, sticky="nsew") 
            self.setup_forgery_page()
            self.forge_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
            self.start_selection_mode()

    def setup_forgery_page(self):
        if not hasattr(self, 'forge_frame'):
            self.forge_frame = ctk.CTkFrame(self.main_container, height=50, fg_color="#222")
            
            # --- SOURCE TOOLS ---
            btn_load_obj = ctk.CTkButton(self.forge_frame, text="Load Obj", command=self.load_external_asset, width=60, fg_color="#444")
            btn_load_obj.pack(side="left", padx=(10, 2))
            
            ctk.CTkFrame(self.forge_frame, width=1, height=20, fg_color="#444").pack(side="left", padx=5)

            # Copy-Move Selectors
            self.btn_rect = ctk.CTkButton(self.forge_frame, text="Rect", width=40, fg_color="#555", command=lambda: self.set_selection_shape("rect"))
            self.btn_rect.pack(side="left", padx=2)
            
            self.btn_oval = ctk.CTkButton(self.forge_frame, text="Oval", width=40, fg_color="#333", command=lambda: self.set_selection_shape("oval"))
            self.btn_oval.pack(side="left", padx=2)
            
            self.btn_free = ctk.CTkButton(self.forge_frame, text="Free", width=40, fg_color="#333", command=lambda: self.set_selection_shape("free"))
            self.btn_free.pack(side="left", padx=2)

            ctk.CTkFrame(self.forge_frame, width=1, height=20, fg_color="#444").pack(side="left", padx=5)

            # --- MANIPULATION TOOLS ---
            btn_fit = ctk.CTkButton(self.forge_frame, text="Fit", width=30, fg_color="#444", command=self.image_canvas.fit_to_screen)
            btn_fit.pack(side="left", padx=2)

            ctk.CTkFrame(self.forge_frame, width=1, height=20, fg_color="#444").pack(side="left", padx=5)

            # --- PROCESSING TOOLS ---
            self.loading_bar = ctk.CTkProgressBar(self.forge_frame, width=50, mode="indeterminate", height=8)
            
            self.btn_mask = ctk.CTkButton(self.forge_frame, text="Mask", command=self.run_auto_mask_thread, width=40, fg_color="#444")
            self.btn_mask.pack(side="left", padx=2)

            btn_feather = ctk.CTkButton(self.forge_frame, text="Blur", command=self.image_canvas.trigger_feathering, width=40, fg_color="#444")
            btn_feather.pack(side="left", padx=2)

            ctk.CTkFrame(self.forge_frame, width=1, height=20, fg_color="#444").pack(side="left", padx=5)

            # --- ACTION TOOLS ---
            btn_apply = ctk.CTkButton(self.forge_frame, text="Paste", command=self.apply_tool, width=50, fg_color="green")
            btn_apply.pack(side="left", padx=2)

            btn_clear = ctk.CTkButton(self.forge_frame, text="Cancel", command=self.clear_tool_selection, width=50, fg_color="#8B0000")
            btn_clear.pack(side="left", padx=2)

    def load_external_asset(self):
        if not self.image_canvas.original_image:
            return
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if path:
            img = Image.open(path)
            self.image_canvas.set_floating_image_from_external(img)
            self.btn_rect.configure(fg_color="#333")
            self.btn_oval.configure(fg_color="#333")
            self.btn_free.configure(fg_color="#333")

    def update_floating_scale(self, val):
        self.image_canvas.apply_transformations(scale_percent=val)

    def update_floating_rotate(self, val):
        self.image_canvas.apply_transformations(angle=val)

    def run_auto_mask_thread(self):
        if not self.image_canvas.floating_pil_image: return
        self.loading_bar.pack(side="left", padx=10)
        self.loading_bar.start()
        self.btn_mask.configure(state="disabled")
        threading.Thread(target=self._bg_remove_task, daemon=True).start()

    def _bg_remove_task(self):
        try:
            img_in = self.image_canvas.floating_pil_image.copy()
            img_out = ImageProcessor.smart_background_remove(img_in)
            self.after(0, lambda: self._on_bg_remove_done(img_out))
        except:
            self.after(0, lambda: self._on_bg_remove_done(None))

    def _on_bg_remove_done(self, result):
        self.loading_bar.stop()
        self.loading_bar.pack_forget()
        self.btn_mask.configure(state="normal")
        if result: self.image_canvas.update_floating_image(result)

    def set_selection_shape(self, shape):
        self.image_canvas.set_selection_shape(shape)
        self.btn_rect.configure(fg_color="#555" if shape == "rect" else "#333")
        self.btn_oval.configure(fg_color="#555" if shape == "oval" else "#333")
        self.btn_free.configure(fg_color="#555" if shape == "free" else "#333")

    def start_selection_mode(self):
        self.image_canvas.set_tool_mode("select")
        # Reset transformation sliders to defaults
        if hasattr(self, 'slider_scale'): self.slider_scale.set(100)
        if hasattr(self, 'slider_rotate'): self.slider_rotate.set(0)

    def apply_tool(self):
        self.image_canvas.apply_paste()
        
    def clear_tool_selection(self):
        self.image_canvas.clear_selection()
        self.image_canvas.set_tool_mode("select")

    def update_metadata_ui(self):
        for widget in self.metadata_view.winfo_children():
            widget.destroy()
        data = self.image_processor.get_formatted_exif()
        for label, value in data:
            row = ctk.CTkFrame(self.metadata_view, fg_color="transparent")
            row.pack(fill="x", padx=40, pady=5)
            ctk.CTkLabel(row, text=f"{label}:", width=200, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
            ctk.CTkLabel(row, text=value, anchor="w", font=("Arial", 12)).pack(side="left", padx=10)

    def setup_toolbar(self):
        t_btn = {"width": 35, "height": 30, "fg_color": "#333", "hover_color": "#8B0000"}
        
        # ZOOM
        ctk.CTkLabel(self.toolbar, text="Zoom:").pack(side="left", padx=5)
        ctk.CTkButton(self.toolbar, text="-", command=lambda: self.zoom(0.8), **t_btn).pack(side="left", padx=2)
        ctk.CTkButton(self.toolbar, text="1:1", command=lambda: self.image_canvas.set_zoom_1_to_1(), **t_btn).pack(side="left", padx=2)
        ctk.CTkButton(self.toolbar, text="+", command=lambda: self.zoom(1.2), **t_btn).pack(side="left", padx=2)
        
        btn_fit = ctk.CTkButton(self.toolbar, text="FIT", command=self.image_canvas.fit_to_screen, **t_btn)
        btn_fit.pack(side="left", padx=(5, 2))
        CTkToolTip(btn_fit, "Fit to screen")
        
        # CHANNELS
        ctk.CTkLabel(self.toolbar, text="| Channels:").pack(side="left", padx=5)
        self.btn_channels = ctk.CTkButton(self.toolbar, text="RGB", command=self.open_channel_selector, width=60, height=30, fg_color="#333")
        self.btn_channels.pack(side="left", padx=2)

        # ANALYSIS TOOLS
        ctk.CTkLabel(self.toolbar, text="| Tools:").pack(side="left", padx=5)
        
        self.btn_grid = ctk.CTkButton(self.toolbar, text="Grid", command=self.toggle_grid, **t_btn)
        self.btn_grid.pack(side="left", padx=2)

        self.btn_invert = ctk.CTkButton(self.toolbar, text="Neg", command=self.toggle_invert, **t_btn)
        self.btn_invert.pack(side="left", padx=2)
        CTkToolTip(self.btn_invert, "Invert Colors (Negative)")

        self.btn_he = ctk.CTkButton(self.toolbar, text="HE", command=lambda: self.toggle_filter("Equalize"), **t_btn)
        self.btn_he.pack(side="left", padx=2)
        CTkToolTip(self.btn_he, "Histogram Equalization")

        self.btn_edge = ctk.CTkButton(self.toolbar, text="Edge", command=lambda: self.toggle_filter("Edge"), **t_btn)
        self.btn_edge.pack(side="left", padx=2)
        CTkToolTip(self.btn_edge, "Edge Detection")

        self.btn_ela = ctk.CTkButton(self.toolbar, text="ELA", command=lambda: self.toggle_filter("ELA"), **t_btn)
        self.btn_ela.pack(side="left", padx=2)
        CTkToolTip(self.btn_ela, "Error Level Analysis")
        
        ctk.CTkLabel(self.toolbar, text="|").pack(side="left", padx=5)

        self.btn_hist = ctk.CTkButton(self.toolbar, text="HIST", command=self.show_histogram, **t_btn)
        self.btn_hist.pack(side="left", padx=2)
        CTkToolTip(self.btn_hist, "RGB Histogram")

        ctk.CTkButton(self.toolbar, text="SAVE", command=self.save_view, width=50, height=30, fg_color="#333").pack(side="left", padx=10)

    def show_histogram(self):
        try:
            from gui.histogram_window import HistogramWindow
            if self.image_canvas.original_image:
                HistogramWindow(self, self.image_canvas.original_image, self.image_canvas.get_current_processed_image())
        except Exception as e:
            print(f"Error opening histogram: {e}")

    def toggle_grid(self):
        self.image_canvas.toggle_grid()
        self.btn_grid.configure(fg_color="#8B0000" if self.image_canvas.show_grid else "#333")

    def toggle_invert(self):
        self.image_canvas.toggle_invert()
        self.btn_invert.configure(fg_color="#8B0000" if self.image_canvas.is_inverted else "#333")

    def toggle_filter(self, mode):
        curr = self.image_canvas.set_analysis_mode(mode)
        # Update button colors for feedback
        self.btn_he.configure(fg_color="#8B0000" if curr == "Equalize" else "#333")
        self.btn_edge.configure(fg_color="#8B0000" if curr == "Edge" else "#333")
        self.btn_ela.configure(fg_color="#8B0000" if curr == "ELA" else "#333")

    def open_channel_selector(self):
        ChannelSelector(self, self.set_channel_from_popup)

    def set_channel_from_popup(self, mode):
        self.image_canvas.set_channel_mode(mode)
        self.btn_channels.configure(text=mode)

    def save_view(self):
        img = self.image_canvas.get_current_processed_image()
        if img:
            path = filedialog.asksaveasfilename(defaultextension=".png", 
                                               filetypes=[("PNG", "*.png"), ("JPG", "*.jpg")])
            if path: img.save(path)

    def on_mouse_move(self, event):
        self.pixel_info.configure(text=self.image_canvas.get_pixel_data(event.x, event.y))
        self.image_canvas.on_mouse_move(event)

    def zoom(self, f):
        if self.image_canvas.original_image:
            self.image_canvas.scale *= f
            self.image_canvas.redraw()

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Supported Images", "*.jpg *.jpeg *.png *.bmp *.webp"),
            ("All Files", "*.*")
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