from PIL import Image, ImageTk, ExifTags, ImageChops, ImageEnhance, ImageFilter, ImageOps
import os
import exifread
import io
import numpy as np

class ImageProcessor:
    def __init__(self):
        self.original_image = None
        self.filename = None
        self.format = None
        self.size = None
        self.exif_data = {}

    @staticmethod
    def smart_background_remove(image, tolerance=30):
        """
        Rimuove lo sfondo usando AI (rembg/U2-Net) se disponibile.
        Altrimenti usa un fallback basato sugli angoli.
        """
        # Lazy import per evitare conflitti all'avvio
        try:
            from rembg import remove as rembg_remove
            HAS_REMBG = True
        except ImportError:
            HAS_REMBG = False
            print("rembg non installato. Installa con 'pip install rembg[cpu]' per il ritaglio intelligente.")

        if HAS_REMBG:
            try:
                # rembg lavora al meglio su immagini intere
                output = rembg_remove(image)
                return output
            except Exception as e:
                print(f"Errore rembg: {e}")
        
        # Fallback (Algoritmo Naive NumPy) se rembg manca o fallisce
        try:
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            
            data = np.array(image)
            r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
            
            corners = [data[0, 0, :3], data[0, -1, :3], data[-1, 0, :3], data[-1, -1, :3]]
            bg_mean = np.mean(corners, axis=0)
            
            diff = np.sqrt((r - bg_mean[0])**2 + (g - bg_mean[1])**2 + (b - bg_mean[2])**2)
            
            mask = np.where(diff < tolerance, 0, 255).astype(np.uint8)
            new_a = np.minimum(a, mask)
            data[:,:,3] = new_a
            
            return Image.fromarray(data)
        except Exception as e:
            print(f"Errore Fallback Mask: {e}")
            return image

    @staticmethod
    def apply_feathering(image, radius=3):
        """
        Sfuma i bordi del canale Alpha per un incollaggio più morbido.
        Include un passaggio di 'Erosione' per rimuovere gli aloni del vecchio sfondo.
        """
        try:
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            
            # Separa alpha
            r, g, b, a = image.split()
            
            # 1. Erosione: Restringi la maschera per eliminare i bordi sporchi (halo)
            a_eroded = a.filter(ImageFilter.MinFilter(3))
            
            # 2. Sfumatura: Ammorbidisci il nuovo bordo
            a_blurred = a_eroded.filter(ImageFilter.GaussianBlur(radius))
            
            return Image.merge("RGBA", (r, g, b, a_blurred))
        except Exception:
            return image

    @staticmethod
    def compute_ela(image, quality=90):
        """
        Esegue l'Error Level Analysis (ELA).
        """
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")

            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=quality)
            buffer.seek(0)
            
            resaved_image = Image.open(buffer)
            
            ela_image = ImageChops.difference(image, resaved_image)
            
            extrema = ela_image.getextrema()
            max_diff = max([ex[1] for ex in extrema])
            if max_diff == 0:
                max_diff = 1
            
            scale = 255.0 / max_diff
            ela_image = ImageEnhance.Brightness(ela_image).enhance(scale)
            
            return ela_image
        except Exception as e:
            print(f"Errore ELA: {e}")
            return image

    def load_image(self, path):
        """Carica un'immagine e ne salva i metadati di base."""
        try:
            self.original_image = Image.open(path)
            self.filename = os.path.basename(path)
            self.format = self.original_image.format
            self.size = self.original_image.size
            self.exif_data = {}
            
            try:
                with open(path, 'rb') as f:
                    tags = exifread.process_file(f, details=False)
                    if tags:
                        self.exif_data = tags
            except Exception: pass

            if not self.exif_data and hasattr(self.original_image, '_getexif'):
                try:
                    exif = self.original_image._getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                            self.exif_data[str(tag_name)] = value
                except Exception: pass
            
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
            if "Thumbnail" in tag or "MakerNote" in tag:
                continue
            
            val_str = str(val)
            if len(val_str) > 50:
                val_str = val_str[:50] + "..."
            
            label = tag
            if label.startswith("EXIF "): label = label[5:]
            if label.startswith("Image "): label = label[6:]
            
            result.append((label, val_str))
        
        result.sort(key=lambda x: x[0])
        return result