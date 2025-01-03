from server import *
from ui import BackupSettingsWindow


class BackupApp(Adw.Application):   
    def __init__(self):
        super().__init__(application_id=SERVER().ID,
                        flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = BackupSettingsWindow(application=self)
        win.present()


def main():
    app = BackupApp()
    return app.run(sys.argv)
    

if __name__ == "__main__":
    main()

