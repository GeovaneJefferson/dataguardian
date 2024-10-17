from server import *
from ui import UIWindow 


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

# DOTO
'''
1 - user may only activate realtime protection after choose a backup device.
2 - After enable/disable realtime protection, user will be unable
    to enable/disable for x seconds. (To prevent crashes in the daemon).
3 - Fix options to user select folder to exclude from backing up.  
'''