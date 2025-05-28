from server import *

try:
    gi.require_version("Poppler", "0.18")
    from gi.repository import Poppler
    POPPLER_AVAILABLE = True
except Exception:
    POPPLER_AVAILABLE = False
    print("Warning: Poppler not available — PDF preview disabled.")

mount_point = "/media/geovane/BACKUP"

class DeviceManagerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_default_size(1280, 800)
        self.set_title(server.APP_NAME)

        ##########################################################################
		# VARIABLES
		##########################################################################
        self.selected_file_path = None
        self.ignored_folders = []
        self.documents_path = os.path.expanduser(server.main_backup_folder())
        self.files = self.scan_files_folder_threaded()
        
        self.page_size = 50  # Number of results per page
        self.current_page = 0  # Start from the first page

        self.search_results = []  # Store results based on filtering/searching
        self.date_combo = None  # To reference date combo in filtering
        self.search_timer = None  # Initialize in the class constructor

        # Get stored driver_location and driver_name
        self.driver_location = server.get_database_value(
            section='DRIVER',
            option='driver_location')

        self.driver_name = server.get_database_value(
            section='DRIVER',
            option='driver_name')
        
        # Create a vertical box to hold the HeaderBar at the top and the main content below it.
        # This replaces the functionality of Adw.ToolbarView for older libadwaita versions.
        main_layout_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(main_layout_box) # Set this box as the main content of the window

        # Adwaita 1.4+
        # toolbar_view = Adw.ToolbarView()
        # self.set_content(toolbar_view)

        # header = Adw.HeaderBar()
        # toolbar_view.add_top_bar(header)

        # main_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        # toolbar_view.set_content(main_content)


        # Adwaita 1.4-
        # Create the HeaderBar.
        header = Adw.HeaderBar()
        main_layout_box.append(header) # Add the HeaderBar to the top of the main_layout_box.

        # Create your main horizontal content box (this will contain your sidebar, center, and info panels).
        main_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        # It's good practice to make this main_content box expand to fill available space.
        main_content.set_hexpand(True)
        main_content.set_vexpand(True)
        main_layout_box.append(main_content) # Add main_content below the HeaderBar.

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sidebar.set_size_request(210, -1)
        sidebar.set_margin_top(0)
        sidebar.set_margin_bottom(12)
        sidebar.set_margin_start(12)
        sidebar.set_margin_end(12)

        overview_button = Gtk.Button(label="Overview")
        self.devices_button = Gtk.Button(label="Devices")
        settings_button = Gtk.Button(label="Settings")

        spacer = Gtk.Box()
        spacer.set_hexpand(False)
        spacer.set_vexpand(True)

        sidebar.append(overview_button)
        sidebar.append(self.devices_button)
        sidebar.append(spacer)
        sidebar.append(settings_button)
        main_content.append(sidebar)

        self.devices_popover = Gtk.Popover()
        self.devices_popover.set_parent(self.devices_button)
        self.devices_popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.devices_popover.set_child(self.devices_popover_box)

        # Center panel
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        center_box.set_hexpand(True)
        center_box.set_vexpand(True)
        center_box.set_css_classes(["center-panel"])
        center_box.set_name("center-box")

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search files to restore...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        center_box.append(self.search_entry)

        self.breadcrumbs = Gtk.Label(label=mount_point, halign=Gtk.Align.START)
        center_box.append(self.breadcrumbs)

        column_titles = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=48)
        for title in ["", "Name", "Size", "Backup", "Last backup"]:
            label = Gtk.Label(label=title, xalign=0)
            column_titles.append(label)
        center_box.append(column_titles)

        self.listbox = Gtk.ListBox()
        center_box.append(self.listbox)

        main_content.append(center_box)

        # Right panel
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        info_box.set_size_request(210, -1)
        info_box.set_margin_top(12)
        info_box.set_margin_bottom(12)
        info_box.set_margin_start(12)
        info_box.set_margin_end(12)

        self.device_icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
        self.device_icon.set_pixel_size(48)
        info_box.append(self.device_icon)

        # Get the device name from the server
        self.device_name: str = server.get_database_value(
            section='DRIVER',
            option='driver_name'
        )
        self.device_name_label = Gtk.Label(label=self.device_name if self.device_name else "")
        self.device_name_label.set_name("title-label")
        self.device_name_label.set_halign(Gtk.Align.START)
        info_box.append(self.device_name_label)

        # Get users filesystem type
        device = server.get_device_for_mountpoint(mount_point)
        fs_type = server.get_filesystem_type(device) if device else "Unknown"

        self.fs_type_label = Gtk.Label(label=f"Type: {fs_type}", xalign=0)
        info_box.append(self.fs_type_label)

        # Get users device total and used size
        total_size =  server.get_user_device_size(mount_point, True) if os.path.exists(mount_point) else "None"
        used_size = server.get_user_device_size(mount_point, False) if os.path.exists(mount_point) else "None"

        self.used_free_label = Gtk.Label(label=f"Total: {total_size}, Used: {used_size} ", xalign=0)
        info_box.append(self.used_free_label)

        self.open_location_button = Gtk.Button(label="Open Location")
        self.open_location_button.connect("clicked", self.on_open_location_clicked)
        info_box.append(self.open_location_button)

        bubble_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        bubble_box.set_css_classes(["bubble"])
        modified_label = Gtk.Label(label="Modified: 6 March 2025 10:25:33", xalign=0)
        created_label = Gtk.Label(label="Created: 24 March 2024 15:15:44", xalign=0)
        bubble_box.append(modified_label)
        bubble_box.append(created_label)
        #info_box.append(bubble_box)

        self.preview_scrolled = Gtk.ScrolledWindow()
        self.preview_scrolled.set_size_request(-1, 250)
        info_box.append(self.preview_scrolled)

        self.preview_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.preview_scrolled.set_child(self.preview_container)

        self.current_preview_widget = None

        spacer = Gtk.Box()
        spacer.set_hexpand(False)
        spacer.set_vexpand(True)
        info_box.append(spacer)

        self.restore_button = Gtk.Button(label="Restore")
        self.restore_button.set_sensitive(False)
        self.restore_button.set_hexpand(False)
        self.restore_button.set_valign(Gtk.Align.START)
        self.restore_button.set_css_classes(["restore-button"])
        info_box.append(self.restore_button)

        main_content.append(info_box)

        # css_provider = Gtk.CssProvider()
        # css_provider.load_from_data(b'''
        #     window {
        #         background-color: #2a2a2a;
        #     }
        #     #center-box {
        #         background-color: #1e1e1e;
        #         padding: 12px;
        #         border-radius: 12px;
        #     }
        #     #title-label {
        #         font-size: 20px;
        #         font-weight: bold;
        #         color: #ffffff;
        #     }
        #     .center-panel Gtk.Label {
        #         color: #ffffff;
        #     }
        #     Gtk.Label {
        #         color: #cccccc;
        #     }
        #     .bubble {
        #         background-color: #333333;
        #         border-radius: 10px;
        #         padding: 12px;
        #         margin-top: 20px;
        #     }
        #     #status-ok {
        #         color: #28a745;
        #     }
        #     #status-in-progress {
        #         color: #f0ad4e;
        #     }
        #     #status-fail {
        #         color: #dc3545;
        #     }
        #     .restore-button {
        #         background-image: none;
        #         background-color: #3b82f6;
        #         color: white;
        #         border-radius: 6px;
        #         padding: 8px 16px;
        #         font-weight: bold;
        #     }
        #     .restore-button:hover {
        #         background-color: #2563eb;
        #     }
        #     .restore-button:disabled {
        #         background-color: #6b7280;
        #         color: #d1d5db;
        #     }
        # ''')
        # Gtk.StyleContext.add_provider_for_display(
        #     Gdk.Display.get_default(),
        #     css_provider,
        #     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        # )

        self.populate_devices()
        self.devices_button.connect("clicked", self.on_devices_clicked)
        self.listbox.connect("row-selected", self.on_listbox_selection_changed)

    ##########################################################################
    # BACKUP DEVICE
    ##########################################################################
    def populate_devices(self):
        #self.listbox.remove_all()

        for i in range(15):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=48)
            row.set_margin_top(3)
            row.set_margin_bottom(3)

            # Alternate file types for demo
            if i == 0:
                filename = "CV.pdf"
                icon_name = "application-pdf-symbolic"
                filepath = "/home/geovane/MEGA/CV/CV.pdf"
            elif i % 3 == 0:
                filename = f"Document-{i:02d}.pdf"
                icon_name = "application-pdf-symbolic"
                filepath = f"/path/to/documents/Document-{i:02d}.pdf"
            elif i % 3 == 1:
                filename = f"Notes-{i:02d}.txt"
                icon_name = "text-x-generic-symbolic"
                filepath = f"/path/to/notes/Notes-{i:02d}.txt"
            else:
                filename = f"Image-{i:02d}.jpg"
                icon_name = "image-x-generic-symbolic"
                filepath = f"/path/to/images/Image-{i:02d}.jpg"

            row.append(Gtk.Image.new_from_icon_name(icon_name))
            row.append(Gtk.Label(label=filename, xalign=0))

            # Get file size
            if os.path.exists(filepath):
                size_label = server.get_item_size(filepath, True)
            else:
                size_label = ""

            row.append(Gtk.Label(label=size_label, xalign=0))
            row.append(Gtk.Label(label="Oct 25 10:30", xalign=0))

            listbox_row = Gtk.ListBoxRow()
            listbox_row.set_child(row)
            listbox_row.device_path = filepath
            self.listbox.append(listbox_row)

    def populate_device_locations(self):
        # Clear old children
        child = self.devices_popover_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.devices_popover_box.remove(child)
            child = next_child

        self.location_buttons = []

        def on_toggled(button):
            if button.get_active():
                for other in self.location_buttons:
                    if other != button:
                        other.set_active(False)
                print("Selected device path:", button.get_label())

        if self.driver_location and self.driver_name:
            label = f"{self.driver_location} ({self.driver_name})"
            check = Gtk.CheckButton(label=label)
            check.connect("toggled", on_toggled)
            self.devices_popover_box.append(check)
            self.location_buttons.append(check)
        else:
            label = Gtk.Label(label="No configured device", xalign=0)
            self.devices_popover_box.append(label)

    def auto_select_backup_device_from_checkbuttons(self):
        # Iterate through location_buttons to find a match and set it active
        for button in self.location_buttons:
            label = button.get_label()
            if label == f"{self.driver_location} ({self.driver_name})":
                button.set_active(True)
                print("Auto-selected backup device:", label)
                break

    def on_devices_clicked(self, button):
        if self.devices_popover.get_visible():
            self.devices_popover.popdown()
        else:
            self.populate_device_locations()
            self.auto_select_backup_device_from_checkbuttons()  # Auto-select saved device
            self.devices_popover.popup()

    # def on_listbox_selection_changed(self, listbox, row):
    #     self.restore_button.set_sensitive(row is not None)
    #     if row:
    #         path = getattr(row, "device_path", None)
    #         print("Selected item path:", path)
    #         self.device_name_label.set_text(os.path.basename(path) if path else "")
    #         self.show_preview(path)
    #     else:
    #         self.device_name_label.set_text("")
    #         self.clear_preview()

    def on_listbox_selection_changed(self, listbox, row):
        self.restore_button.set_sensitive(row is not None)
        if row:
            path = getattr(row, "device_path", None)
            self.selected_file_path = path  # ← Store the full path
            self.selected_item_size = server.get_item_size(path, True)
            self.show_preview(path)
            print("Selected item path:", path)
        else:
            self.device_name_label.set_text("")
            self.clear_preview()
            self.selected_file_path = None

    def clear_preview(self):
        if self.current_preview_widget:
            self.preview_container.remove(self.current_preview_widget)
            self.current_preview_widget = None

    def show_preview(self, filepath):
        self.clear_preview()
        if not filepath:
            self.show_no_preview()
            return

        ext = os.path.splitext(filepath)[1].lower()
        mime, _ = mimetypes.guess_type(filepath)
        if mime is None:
            mime = ""

        # If file doesn't exist, simulate preview
        file_exists = os.path.exists(filepath)

        if (ext == ".pdf" or mime == "application/pdf") and POPPLER_AVAILABLE and file_exists:
            self.show_pdf_preview(filepath)
        elif (ext == ".txt" or mime.startswith("text")) and file_exists:
            self.show_text_preview(filepath)
        else:
            self.show_no_preview()

    def show_pdf_preview(self, filepath):
        try:
            document = Poppler.Document.new_from_file(f"file://{filepath}", None)
            page = document.get_page(0)
            width, height = page.get_size()

            scale = 0.3
            surf_width = int(width * scale)
            surf_height = int(height * scale)

            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, surf_width, surf_height)
            cr = cairo.Context(surface)
            cr.scale(scale, scale)
            page.render(cr)
            surface.flush()

            pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, surf_width, surf_height)

            image = Gtk.Image.new_from_pixbuf(pixbuf)
            self.preview_container.append(image)
            self.current_preview_widget = image
        except Exception as e:
            print("Failed to load PDF preview:", e)
            self.show_no_preview()

    def show_text_preview(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read(4096)
            textview = Gtk.TextView()
            textview.set_editable(False)
            textview.set_wrap_mode(Gtk.WrapMode.WORD)
            textview.get_buffer().set_text(text)
            textview.set_size_request(-1, 250)
            self.preview_container.append(textview)
            self.current_preview_widget = textview
        except Exception as e:
            print("Failed to load text preview:", e)
            self.show_no_preview()

    def show_no_preview(self):
        label = Gtk.Label(label="No preview available")
        self.preview_container.append(label)
        self.current_preview_widget = label

    
    ##########################################################################
    # SEARCH ENTRY
    ##########################################################################
    def scan_files_folder_threaded(self):
        """Scan files in a background thread."""
        def scan():
            self.files = self.scan_files_folder()
            print("Files scanned:", len(self.files))
        threading.Thread(target=scan, daemon=True).start()
        
    def scan_files_folder(self):
        """Scan files and return a list of file dictionaries."""
        file_list = []
        if os.path.exists(self.documents_path):
            for root, dirs, files in os.walk(self.documents_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_date = os.path.getmtime(file_path)
                    file_list.append({
                        "name": file_name,
                        "path": file_path,
                        "date": file_date
                    })
        return file_list
	
    def on_search_changed(self, entry):
        """Debounce the search input."""
        if self.search_timer:
            self.search_timer.cancel()

        query = entry.get_text().strip().lower()

        if query:
            self.search_timer = Timer(
                0.5, 
                lambda: threading.Thread(target=self.perform_search, args=(query,), 
                                        daemon=True).start())
            self.search_timer.start()
        else:
            self.populate_results([])
    
    def perform_search(self, query):
        """Perform the search and update the results."""
        try:
            results = self.search_backup_sources(query)
            print("Search results:", results)
        except Exception as e:
            print(f"Error during search: {e}")
            results = []
        GLib.idle_add(self.populate_results, results)
    
    def search_backup_sources(self, query):
        print("Searching for:", query)
        query = query.lower()  # Ensure case-insensitive search

        # Files where name starts with the query
        starts_with = [f for f in self.files if f["name"].lower().startswith(query)]
        # Files where name contains the query but doesn't start with it
        contains = [f for f in self.files if query in f["name"].lower() and not f["name"].lower().startswith(query)]
        print("Starts with:", starts_with)
        print("Contains:", contains)
        return starts_with + contains  # Combine both lists: prioritize files that start with the query
   
    def populate_results(self, results):
        """Populate the results grid with search results, limiting the number of results."""
        print("Populating results:", results)
        # Clear existing results from the grid
        # child = self.results_grid.get_first_child()
        # while child:
        #     next_child = child.get_next_sibling()  # Save reference to the next sibling
        #     self.results_grid.remove(child)       # Remove the current child
        #     child = next_child                    # Move to the next child

        # Sort the results by date (latest first)
        # sorted_results = sorted(results, key=lambda x: x["date"], reverse=True)

        # Limit the number of results
        limited_results = results[:self.page_size]

    # Open location button
    def on_open_location_clicked(self, button):
        if self.selected_file_path:
            folder = os.path.dirname(self.selected_file_path)
            try:
                sub.Popen(["xdg-open", folder])
            except Exception as e:
                print("Failed to open folder:", e)


class DeviceManagerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=server.ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = DeviceManagerWindow(application=self)
        win.present()


def main():
    app = DeviceManagerApp()
    return app.run(None)


if __name__ == "__main__":
    server = SERVER()
    main()
