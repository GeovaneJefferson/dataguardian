from server import *
from ui import UIWindow 


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.dataguardian",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = UIWindow(application=self)
        win.present()

def main():
    app = Application()
    return app.run(sys.argv)


if __name__ == "__main__":
    main()