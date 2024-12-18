from server import *
from old_ui import UIWindow


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=SERVER().ID,
                        flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = UIWindow(application=self)
        win.present()


def main():
    app = Application()
    return app.run(sys.argv)
    

if __name__ == "__main__":
    main()


# TODO
'''
1 - If backup if being made, user should be unable to:
    * Change backup device.
    * Disable realtime protection.
    * Disable Exclude options.
'''