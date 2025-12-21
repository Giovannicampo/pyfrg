from PIL import Image, ImageTk
import os

class ImageProcessor:
    def __init__(self):
        self.original_image = None
        self.filename = None
        self.format = None
        self.size = None

    def load_image(self, path):
        """Carica un'immagine e ne salva i metadati di base."""
        try:
            self.original_image = Image.open(path)
            self.filename = os.path.basename(path)
            self.format = self.original_image.format
            self.size = self.original_image.size
            return self.original_image
        except Exception as e:
            print(f"Errore caricamento immagine: {e}")
            return None

    def get_display_image(self, max_width, max_height):
        """Restituisce una copia ridimensionata per l'anteprima (se necessario)."""
        if not self.original_image:
            return None
        
        # Copia per non modificare l'originale
        img = self.original_image.copy()
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        return img
