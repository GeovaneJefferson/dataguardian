from server import *
#from ui_old import BackupSettingsWindow
from ui import BackupWindow


class BackupApp(Adw.Application):   
    def __init__(self):
        super().__init__(application_id=SERVER().ID,
                        flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = BackupWindow(application=self)
        win.present()


def main():
    app = BackupApp()
    return app.run(sys.argv)
    

if __name__ == "__main__":
    main()

