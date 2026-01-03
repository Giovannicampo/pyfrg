from gui.app import ForgeryApp
import faulthandler
faulthandler.enable()

if __name__ == "__main__":
    app = ForgeryApp()
    app.mainloop()
