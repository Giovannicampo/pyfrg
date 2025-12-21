import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

# Impostazioni iniziali (identiche alle tue)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ForgeryApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("pyfrg - Image Forgery Tool")
        self.geometry("1100x700")

        # Configurazione Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Barra laterale (Sidebar) ---
        # Nota: puoi rimuovere width=200 se vuoi che si adatti al contenuto,
        # ma tenerlo fisso spesso è meglio per l'aspetto.
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # --- Caricamento Logo e Titolo ---
        try:
            # MODIFICA 1: Dimensione ridotta a (40, 40) invece di (100, 100)
            logo_img = ctk.CTkImage(light_image=Image.open("assets/logo.png"),
                                  dark_image=Image.open("assets/logo.png"),
                                  size=(50, 50))
            
            # MODIFICA 2: compound="left" mette l'immagine a sinistra del testo.
            # Ho aggiunto un po' di padx nel label per distanziare il testo dal bordo
            self.logo_label = ctk.CTkLabel(self.sidebar, 
                                           text=" pyfrg", # Aggiunto uno spazio prima del testo per separarlo dall'icona
                                           image=logo_img, 
                                           compound="left", 
                                           font=ctk.CTkFont(size=20, weight="bold"))
        except Exception as e:
            print(f"Errore caricamento logo: {e}. Assicurati che 'assets/logo.png' esista.")
            self.logo_label = ctk.CTkLabel(self.sidebar, text="pyfrg", font=ctk.CTkFont(size=20, weight="bold"))
            
        # Ho ridotto leggermente il pady per renderlo più compatto
        self.logo_label.pack(padx=20, pady=(30, 20)) 

        # Bottone Carica
        self.load_button = ctk.CTkButton(self.sidebar, text="Carica Immagine", command=self.load_image)
        self.load_button.pack(padx=20, pady=10)

        # --- Area Canvas (per l'immagine) ---
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.image_label = ctk.CTkLabel(self.canvas_frame, text="Nessuna immagine caricata")
        self.image_label.pack(expand=True)

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if file_path:
            img = Image.open(file_path) # Codice futuro
            self.image_label.configure(text=f"Immagine caricata:\n{file_path}") # \n per andare a capo se il path è lungo
            print(f"Immagine selezionata: {file_path}")

if __name__ == "__main__":
    app = ForgeryApp()
    app.mainloop()