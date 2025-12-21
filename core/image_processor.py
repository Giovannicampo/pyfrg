from PIL import Image, ImageTk, ExifTags
import os
import exifread

class ImageProcessor:
    def __init__(self):
        self.original_image = None
        self.filename = None
        self.format = None
        self.size = None
        self.exif_data = {}

    def load_image(self, path):
        """Carica un'immagine e ne salva i metadati di base."""
        try:
            self.original_image = Image.open(path)
            self.filename = os.path.basename(path)
            self.format = self.original_image.format
            self.size = self.original_image.size
            self.exif_data = {}
            
            # 1. Tentativo con exifread (più dettagliato per RAW/TIFF)
            try:
                with open(path, 'rb') as f:
                    tags = exifread.process_file(f, details=False)
                    if tags:
                        self.exif_data = tags
            except Exception: pass

            # 2. Fallback su PIL (se exifread fallisce o è vuoto)
            if not self.exif_data and hasattr(self.original_image, '_getexif'):
                try:
                    exif = self.original_image._getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                            self.exif_data[str(tag_name)] = value
                except Exception: pass
            
            # 3. Dati base immagine (sempre presenti)
            self.exif_data["Format"] = self.format
            self.exif_data["Size"] = f"{self.size[0]}x{self.size[1]}"
            self.exif_data["Mode"] = self.original_image.mode

            return self.original_image
        except Exception as e:
            print(f"Errore caricamento immagine: {e}")
            return None

    def get_formatted_exif(self):
        """Restituisce una lista di tuple (Tag, Valore) per la UI."""
        if not self.exif_data:
            return [("Info", "Nessun metadato EXIF trovato/supportato")]
        
        result = []
        for tag, val in self.exif_data.items():
            # Filtriamo dati binari o inutili per la visualizzazione rapida
            if "Thumbnail" in tag or "MakerNote" in tag:
                continue
            
            # Convertiamo il valore in stringa
            val_str = str(val)
            if len(val_str) > 50: # Tagliamo stringhe troppo lunghe (es. dati binari dumpati)
                val_str = val_str[:50] + "..."
            
            # Pulizia etichetta (Rimuovi prefissi comuni)
            label = tag
            if label.startswith("EXIF "): label = label[5:]
            if label.startswith("Image "): label = label[6:]
            
            result.append((label, val_str))
        
        # Ordiniamo alfabeticamente
        result.sort(key=lambda x: x[0])
        
        if not result:
            return [("Info", "Nessun tag leggibile trovato")]
        return result

    def get_display_image(self, max_width, max_height):
        """Restituisce una copia ridimensionata per l'anteprima (se necessario)."""
        if not self.original_image:
            return None
        
        # Copia per non modificare l'originale
        img = self.original_image.copy()
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        return img
