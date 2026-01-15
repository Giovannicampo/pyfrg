from PIL import Image

class HistoryManager:
    def __init__(self, max_steps=20):
        self.undo_stack = []
        self.redo_stack = []
        self.max_steps = max_steps

    def push(self, image):
        """Salva lo stato corrente nello stack di Undo prima di una modifica."""
        if image is None:
            return
        
        self.undo_stack.append(image.copy())
        
        if len(self.undo_stack) > self.max_steps:
            self.undo_stack.pop(0)
            
        self.redo_stack.clear()

    def undo(self, current_image):
        """Torna indietro di uno step. Restituisce la vecchia immagine."""
        if not self.undo_stack:
            return None
        
        if current_image:
            self.redo_stack.append(current_image.copy())
            
        return self.undo_stack.pop()

    def redo(self, current_image):
        """Rifa un'azione annullata."""
        if not self.redo_stack:
            return None
            
        if current_image:
            self.undo_stack.append(current_image.copy())
            
        return self.redo_stack.pop()
