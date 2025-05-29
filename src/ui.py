from server import *
from device_location import device_location
from has_driver_connection import has_driver_connection
from check_package_manager import check_package_manager
try:
    gi.require_version("Poppler", "0.18")
    from gi.repository import Poppler
    POPPLER_AVAILABLE = True
except Exception:
    POPPLER_AVAILABLE = False
    print("Warning: Poppler not available — PDF preview disabled.")

server = SERVER()

class BackupWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("close-request", self.on_main_window_close)
        self.connect("map", self.on_window_map)

        self.set_default_size(1280, 800)
        self.set_title(server.APP_NAME)

        ##########################################################################
		# VARIABLES
		##########################################################################
        self.has_connection: bool = has_driver_connection()
        self.selected_file_path: bool = None
        self.documents_path = os.path.expanduser(server.main_backup_folder())
        self.location_buttons: list = []
        self.files: list = []
        self.last_query: str = ""
        self.files_loaded: bool = False
        self.pending_search_query: bool = None
        self.scan_files_folder_threaded()

        self.ignored_folders = []

        self.page_size = 28  # Number of results per page
        self.current_page = 0  # Start from the first page

        self.search_results = []  # Store results based on filtering/searching
        self.date_combo = None  # To reference date combo in filtering
        self.search_timer = None  # Initialize in the class constructor
        self.update_preview_window = None  # Add this in your __init__ if you want
        
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
        # It's good practice to make this main_content box expand to fill available space.
        main_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        main_content.set_hexpand(True)
        main_content.set_vexpand(True)
        main_layout_box.append(main_content) # Add main_content below the HeaderBar.

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sidebar.set_size_request(210, -1)
        sidebar.set_margin_top(12)
        sidebar.set_margin_bottom(12)
        sidebar.set_margin_start(12)
        sidebar.set_margin_end(12)

        # Overview button with icon
        overview_icon = Gtk.Image.new_from_icon_name("view-dashboard-symbolic")
        overview_button = Gtk.Button()
        overview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        overview_box.set_halign(Gtk.Align.CENTER)
        overview_box.set_valign(Gtk.Align.CENTER)
        overview_icon.set_halign(Gtk.Align.CENTER)
        overview_box.append(overview_icon)
        overview_box.append(Gtk.Label(label="Overview"))
        overview_button.set_child(overview_box)

        # Devices button with icon
        devices_icon = Gtk.Image.new_from_icon_name("drive-harddisk-symbolic")
        self.devices_button = Gtk.Button()
        devices_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        devices_box.set_halign(Gtk.Align.CENTER)
        devices_box.set_valign(Gtk.Align.CENTER)
        devices_icon.set_halign(Gtk.Align.CENTER)
        devices_box.append(devices_icon)
        devices_box.append(Gtk.Label(label="Devices"))
        self.devices_button.set_child(devices_box)
        
        # Full Restore button with icon
        restore_icon = Gtk.Image.new_from_icon_name("preferences-system-time-symbolic")
        self.restore_system_button = Gtk.Button()
        self.restore_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.restore_box.set_sensitive(self.has_connection)
        self.restore_box.set_halign(Gtk.Align.CENTER)
        self.restore_box.set_valign(Gtk.Align.CENTER)
        restore_icon.set_halign(Gtk.Align.CENTER)
        self.restore_box.append(restore_icon)
        self.restore_box.append(Gtk.Label(label="System Restore"))
        self.restore_system_button.set_tooltip_text("" \
        "This is usually used to restore applications, flatpaks, file and folders after a clean system re/install.")
        self.restore_system_button.set_child(self.restore_box)
        self.restore_system_button.connect("clicked", self.on_restore_system_button_clicked)

        # Settings button with icon
        settings_icon = Gtk.Image.new_from_icon_name("preferences-system-symbolic")
        settings_button = Gtk.Button()
        settings_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        settings_box.set_halign(Gtk.Align.CENTER)
        settings_box.set_valign(Gtk.Align.CENTER)
        settings_icon.set_halign(Gtk.Align.CENTER)
        settings_box.append(settings_icon)
        settings_box.append(Gtk.Label(label="Settings"))
        settings_button.set_child(settings_box)
        settings_button.connect("clicked", self.on_settings_clicked)

        spacer = Gtk.Box()
        spacer.set_hexpand(False)
        spacer.set_vexpand(True)

        #sidebar.append(overview_button)
        sidebar.append(self.devices_button)
        sidebar.append(self.restore_system_button)
        #sidebar.append(spacer)
        sidebar.append(settings_button)
        main_content.append(sidebar)

        self.devices_popover = Gtk.Popover()
        self.devices_popover.set_parent(self.devices_button)
        self.devices_popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.devices_popover.set_child(self.devices_popover_box)

        # Center left panel
        center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        center_box.set_hexpand(True)
        center_box.set_vexpand(True)
        center_box.set_css_classes(["center-panel"])
        center_box.set_name("center-box")

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search file to restore...")
        self.search_entry.set_margin_top(12)
        self.search_entry.set_hexpand(True)
        self.search_entry.set_sensitive(self.has_connection)
        self.search_entry.connect("search-changed", self.on_search_changed)
        center_box.append(self.search_entry)

        self.left_breadcrumbs = Gtk.Label(halign=Gtk.Align.START)
        center_box.append(self.left_breadcrumbs)

        # Header grid
        left_column_titles = Gtk.Grid()
        left_column_titles.set_margin_top(0)
        left_column_titles.set_column_spacing(42)
        left_column_titles.set_hexpand(True)

        # Icon header (empty)
        icon_header = Gtk.Label()
        icon_header.set_hexpand(False)
        icon_header.set_halign(Gtk.Align.START)
        #left_column_titles.attach(icon_header, 0, 0, 1, 1)

        # Name header
        name_header = Gtk.Label(label="Name")
        name_header.set_hexpand(True)
        name_header.set_halign(Gtk.Align.START)
        #left_column_titles.attach(name_header, 1, 0, 1, 1)

        # Size header
        size_header = Gtk.Label(label="Size" + " " * 4)  # Add padding for alignment
        size_header.set_hexpand(False)
        size_header.set_halign(Gtk.Align.START)
        #left_column_titles.attach(size_header, 2, 0, 1, 1)

        # Date header
        date_header = Gtk.Label(label="Date"  + " " * 18)  # Add padding for alignment
        date_header.set_hexpand(False)
        date_header.set_halign(Gtk.Align.START)
        left_column_titles.attach(date_header, 3, 0, 1, 1)
        #center_box.append(left_column_titles)

        # Add a loading label to the center left box
        self.loading_label = Gtk.Label(label=f"Searching for file...")
        self.loading_label.set_hexpand(True)
        self.loading_label.set_vexpand(True)
        self.loading_label.set_halign(Gtk.Align.CENTER)
        self.loading_label.set_valign(Gtk.Align.START)
        center_box.append(self.loading_label)
        self.loading_label.set_visible(False)  # Show at startup
        
        # # Listbox for search results
        # self.listbox = Gtk.ListBox()
        # self.listbox.connect("row-selected", self.on_listbox_selection_changed)

        # key_controller = Gtk.EventControllerKey()
        # key_controller.connect("key-pressed", self.on_listbox_key_press)
        # self.listbox.add_controller(key_controller)

        # # Add a scrolled window for the listbox
        # listbox_scrolled = Gtk.ScrolledWindow()
        # listbox_scrolled.set_policy(
        #     Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        # listbox_scrolled.set_hexpand(True)
        # listbox_scrolled.set_vexpand(True)
        # listbox_scrolled.set_child(self.listbox)

        # center_box.append(self.listbox)

        self.listbox = Gtk.ListBox()
        self.listbox.connect("row-selected", self.on_listbox_selection_changed)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_listbox_key_press)
        self.listbox.add_controller(key_controller)
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
        self.device_name_label = Gtk.Label(label=f"<b>{self.device_name}</b>" if self.device_name else "")
        self.device_name_label.set_use_markup(True)
        self.device_name_label.set_name("title-label")
        self.device_name_label.set_halign(Gtk.Align.START)
        info_box.append(self.device_name_label)

        # Get users filesystem type
        device = server.get_device_for_mountpoint(self.driver_location)
        fs_type = server.get_filesystem_type(device) if device else "Unknown"

        self.fs_type_label = Gtk.Label(label=f"<b>Type</b>: {fs_type}", xalign=0)
        self.fs_type_label.set_use_markup(True)
        info_box.append(self.fs_type_label)

        # Get users device total and used size
        total_size =  server.get_user_device_size(
            self.driver_location, True) if os.path.exists(self.driver_location) else "None"
        used_size = server.get_user_device_size(
            self.driver_location, False) if os.path.exists(self.driver_location) else "None"

        self.used_free_label = Gtk.Label(label=f"<b>Total:</b> {total_size}, <b>Used:</b> {used_size} ", xalign=0)
        self.used_free_label.set_use_markup(True)
        info_box.append(self.used_free_label)
        
        ##################################################################
        # Logs
        ##################################################################
        self.logs_label = Gtk.Label(xalign=0)
        info_box.append(self.logs_label)

        recent_backup_informations = server.get_database_value(
			section='RECENT',
			option='recent_backup_timeframe')
        
        if recent_backup_informations:
            self.logs_label.set_use_markup(True)
            self.logs_label.set_text("")
            self.logs_label.set_markup(f"<b>Most Recent Backup:</b>\n{recent_backup_informations}")
        else:
            self.logs_label.set_use_markup(True)
            self.logs_label.set_text("")
            self.logs_label.set_markup("<b>Most Recent Backup:</b>\nNever")

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(6)
        separator.set_margin_bottom(6)
        info_box.append(separator)
        
        self.logs_button = Gtk.Button(label="Logs")
        self.logs_button.set_sensitive(bool(self.has_connection))
        self.logs_button.set_hexpand(False)
        self.logs_button.set_valign(Gtk.Align.CENTER)
        #self.logs_button.set_css_classes(["pill"])
        self.logs_button.connect("clicked", self.show_backup_logs_dialog)  # Show logs, not the progress dialog
        info_box.append(self.logs_button)
        
        ##################################################################
        # Open location button
        ##################################################################
        self.open_location_button = Gtk.Button(label="Open File Location")
        self.open_location_button.set_sensitive(False)
        info_box.append(self.open_location_button)

        bubble_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        bubble_box.set_css_classes(["bubble"])
        modified_label = Gtk.Label(label="Modified: 6 March 2025 10:25:33", xalign=0)
        created_label = Gtk.Label(label="Created: 24 March 2024 15:15:44", xalign=0)
        bubble_box.append(modified_label)
        bubble_box.append(created_label)
        #info_box.append(bubble_box)

        # self.preview_scrolled = Gtk.ScrolledWindow()
        # self.preview_scrolled.set_size_request(-1, 250)
        # info_box.append(self.preview_scrolled)

        # self.preview_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # self.preview_scrolled.set_child(self.preview_container)
        # self.current_preview_widget = None

        # Find updates button
        # After user selects a file, this button will be enabled,
        # -this will be used to find updates for the selected file.
        self.find_updates = Gtk.Button(label="Find File Versions")
        self.find_updates.set_tooltip_text(
            "Search for all available versions of the selected file, including the current and previous backups. "
            "Use this to restore or review earlier versions of your file.")
        self.find_updates.set_sensitive(False)
        self.find_updates.set_hexpand(False)
        self.find_updates.set_valign(Gtk.Align.CENTER)
        #self.find_updates.set_css_classes(["suggested-action"])
        self.find_updates.connect("clicked", lambda b: self.find_update(self.selected_file_path))
        info_box.append(self.find_updates)
        
        # Spacer to push the restore button to the bottom
        spacer = Gtk.Box()
        spacer.set_hexpand(False)
        spacer.set_vexpand(True)
        info_box.append(spacer)
        
        # Restore button
        self.restore_button = Gtk.Button(label="Restore File")
        self.restore_button.set_sensitive(False)
        self.restore_button.set_hexpand(False)
        self.restore_button.set_valign(Gtk.Align.CENTER)
        self.restore_button.set_css_classes(["suggested-action"])
        self.restore_button.connect("clicked", self.on_restore_button_clicked)
        info_box.append(self.restore_button)
        
        self.restore_progressbar = Gtk.ProgressBar()
        #self.restore_progressbar.set_hexpand(True)
        self.restore_progressbar.set_visible(False)
        info_box.append(self.restore_progressbar)

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
        
        ##########################################################################
		# Connect signals
		##########################################################################
        self.open_location_button.connect("clicked", self.on_open_location_clicked)
        self.devices_button.connect("clicked", self.on_devices_clicked)
        
        ##########################################################################
		# Startup actions
		##########################################################################
        self.add_found_devices_to_devices_popover_box()  # Add found devices to the popover

    ##########################################################################
    # BACKUP
    ##########################################################################
    def add_found_devices_to_devices_popover_box(self):
        # Clear old children
        child = self.devices_popover_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.devices_popover_box.remove(child)
            child = next_child

        # Clear old buttons
        self.location_buttons.clear()

        # Get all devices locations from media or run e.g: /media/username/BACKUP or /run/username/BACKUP
        users_devices_location = os.path.join(device_location(), server.USERNAME)

        # Loop through all devices locations
        for device in os.listdir(users_devices_location):
            device_path = os.path.join(users_devices_location, device)
            check = Gtk.CheckButton(label=device_path)
            self.devices_popover_box.append(check)
            self.location_buttons.append(check)

            check.connect("toggled", lambda button: self.on_toggled(button, device_path))
            print("Found device location:", device_path)

        if not self.location_buttons:
            # If no devices found, show a label
            label = Gtk.Label(label="No backup devices found", xalign=0)
            self.devices_popover_box.append(label)

    def on_toggled(self, button, device_path):
        if button.get_active():
            self.enable_ui_stuff(True) # Enable UI stuff if a device is selected
            print("Selected device path:", device_path)
            for other in self.location_buttons:
                if other != button:
                    other.set_active(False)

            # Save to config/database here if needed
            server.set_database_value(
                section='DRIVER',
                option='driver_location',
                value=str(button.get_label())
            )
            server.set_database_value(
                section='DRIVER',
                option='driver_name',
                value=str(device_path.split("/")[-1])
            )
        else:
            print("Deselected device path:", device_path)
            self.enable_ui_stuff(False) # Disable UI stuff if a device is selected
            # User deselected all devices, clear the config
            server.set_database_value(
                section='DRIVER',
                option='driver_location',
                value=""
            )
            server.set_database_value(
                section='DRIVER',
                option='driver_name',
                value=""
            )

    def on_devices_clicked(self, button):
        if self.devices_popover.get_visible():
            self.devices_popover.popdown()
        else:
            self.automacatically_selected_saved_backup_device()  # Auto-select saved device
            self.devices_popover.popup()

    def automacatically_selected_saved_backup_device(self):
        # Iterate through location_buttons to find a match and set it active
        for button in self.location_buttons:
            label = button.get_label()
            if label == f"{self.driver_location}":
                button.set_active(True)
                print("Auto-selected backup device:", label)
                self.enable_ui_stuff(True) # Enable UI stuff if a device is selected
                break

    def enable_ui_stuff(self, state:bool):   
        """
        True: Enable stuff on the UI. 
        False: Disable stuff on the UI.
        """
        # Already a backup made and has connection
        if os.path.exists(server.backup_folder_name()) and self.has_connection:
            # Enable stuff if has connection to backup device
            self.restore_system_button.set_sensitive(state)
            self.search_entry.set_sensitive(state)

    def on_listbox_selection_changed(self, listbox, row):
        self.restore_button.set_sensitive(row is not None)
        self.find_updates.set_sensitive(row is not None)
        self.open_location_button.set_sensitive(row is not None)
        self.left_breadcrumbs.set_label("")  # Clear the label

        if row:
            path: str = getattr(row, "device_path", None)
            self.selected_file_path = path  # ← Store the full path
            self.left_breadcrumbs.set_label(path.replace(server.backup_folder_name(), "").lstrip(os.sep))
            self.selected_item_size = server.get_item_size(path, True)
            #self.show_preview(path)
            print("Selected item path:", path)
        else:
            self.device_name_label.set_text("")
            #self.clear_preview()
            self.selected_file_path = None

    # def clear_preview(self):
    #     if self.current_preview_widget:
    #         self.preview_container.remove(self.current_preview_widget)
    #         self.current_preview_widget = None

    # def show_preview(self, filepath):
    #     #self.clear_preview()
    #     if not filepath:
    #         self.show_no_preview()
    #         return

    #     ext = os.path.splitext(filepath)[1].lower()
    #     mime, _ = mimetypes.guess_type(filepath)
    #     if mime is None:
    #         mime = ""

    #     # If file doesn't exist, simulate preview
    #     file_exists = os.path.exists(filepath)

    #     if (ext == ".pdf" or mime == "application/pdf") and POPPLER_AVAILABLE and file_exists:
    #         self.show_pdf_preview(filepath)
    #     elif (ext == ".txt" or mime.startswith("text")) and file_exists:
    #         self.show_text_preview(filepath)
    #     else:
    #         self.show_no_preview()

    # def show_pdf_preview(self, filepath):
    #     try:
    #         document = Poppler.Document.new_from_file(f"file://{filepath}", None)
    #         page = document.get_page(0)
    #         width, height = page.get_size()

    #         scale = 0.3
    #         surf_width = int(width * scale)
    #         surf_height = int(height * scale)

    #         surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, surf_width, surf_height)
    #         cr = cairo.Context(surface)
    #         cr.scale(scale, scale)
    #         page.render(cr)
    #         surface.flush()

    #         pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, surf_width, surf_height)

    #         image = Gtk.Image.new_from_pixbuf(pixbuf)
    #         self.preview_container.append(image)
    #         self.current_preview_widget = image
    #     except Exception as e:
    #         print("Failed to load PDF preview:", e)
    #         self.show_no_preview()

    # def show_text_preview(self, filepath):
    #     try:
    #         with open(filepath, "r", encoding="utf-8") as f:
    #             text = f.read(4096)
    #         textview = Gtk.TextView()
    #         textview.set_editable(False)
    #         textview.set_wrap_mode(Gtk.WrapMode.WORD)
    #         textview.get_buffer().set_text(text)
    #         textview.set_size_request(-1, 250)
    #         self.preview_container.append(textview)
    #         self.current_preview_widget = textview
    #     except Exception as e:
    #         print("Failed to load text preview:", e)
    #         self.show_no_preview()

    # def show_no_preview(self):
    #     label = Gtk.Label(label="No preview available")
    #     self.preview_container.append(label)
    #     self.current_preview_widget = label

    
    ##########################################################################
    # SEARCH ENTRY
    ##########################################################################
    def scan_files_folder_threaded(self):
        def scan():
            self.files = self.scan_files_folder()
            self.file_names_lower = [f["name"].lower() for f in self.files]
            self.files_loaded = True
            if self.pending_search_query is not None:
                # Run the pending search
                GLib.idle_add(self.perform_search, self.pending_search_query)
                self.pending_search_query = None
            elif self.last_query:
                GLib.idle_add(self.perform_search, self.last_query)
            # else:
            #     GLib.idle_add(
            #         self.populate_results, 
            #         sorted(self.files, key=lambda x: x["date"], reverse=True)[:self.page_size]
            #     )
        threading.Thread(target=scan, daemon=True).start()
    
    # def scan_files_folder_threaded(self):
    #     """Scan files in a background thread."""
    #     def scan():
    #         self.files = self.scan_files_folder()
    #         # Show the latest files after scanning
    #         # GLib.idle_add(
    #         #     self.populate_results, 
    #         #     sorted(
    #         #         self.files, 
    #         #         key=lambda x: x["date"], 
    #         #         reverse=True)[:self.page_size])
    #     threading.Thread(target=scan, daemon=True).start()

    def scan_files_folder(self):
        """Scan files and return a list of file dictionaries."""
        if not os.path.exists(self.documents_path):
            return []

        file_list = []
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
        if self.search_timer:
            self.search_timer.cancel()

        query = entry.get_text().strip().lower()
        self.last_query = query  # Store the last query

        if not self.files_loaded:
            # Only show loading label if user is searching for something
            if hasattr(self, "loading_label"):
                self.loading_label.set_visible(bool(query))
            self.pending_search_query = query
            # print("Files not loaded yet, queuing search for:", query)
            return

        if query:
            if hasattr(self, "loading_label"):
                self.loading_label.set_visible(True)
            self.search_timer = Timer(0.5, 
                lambda: threading.Thread(target=self.perform_search, args=(query,), 
                                        daemon=True).start())
            self.search_timer.start()
        else:
            if hasattr(self, "loading_label"):
                self.loading_label.set_visible(False)
            # Show latest backup files from latest backup date
            self.populate_results([])
            
    def perform_search(self, query):
        """Perform the search and update the results."""
        try:
            results = self.search_backup_sources(query)
            #print(f"Search results for '{query}': {len(results)} files found.")
        except Exception as e:
            print(f"Error during search: {e}")
            results = []
        GLib.idle_add(self.populate_results, results)
    
    def search_backup_sources(self, query):
        query = query.strip().lower()
        if not query:
            return []
        
        # Before
        # starts_with = [f for f in self.files if f["name"].lower().startswith(query)]
        # contains = [f for f in self.files if query in f["name"].lower() and not f["name"].lower().startswith(query)]

        # # Combine and sort by date descending
        # results = starts_with + contains
        # return results
    
        # After
        # results = [f for f in self.files if query in f["name"].lower()]
        # results.sort(key=lambda x: x["date"], reverse=True)
        # return results[:self.page_size]

        # With index
        matches = []
        for idx, name in enumerate(self.file_names_lower):
            if query in name:
                matches.append(self.files[idx])
        #matches.sort(key=lambda x: x["date"], reverse=True)
        return matches[:self.page_size]
    
    def populate_results(self, results):
        """Populate the results listbox with up to 'self.page_size' search results, aligned in columns."""
        if hasattr(self, "loading_label"):
            self.loading_label.set_visible(False)
            
        # Clear existing results from the listbox
        child = self.listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.listbox.remove(child)
            child = next_child

        limited_results = results[:self.page_size]

        for file_info in limited_results:
            grid = Gtk.Grid()
            grid.set_column_spacing(24)
            grid.set_row_spacing(0)
            grid.set_hexpand(True)
            grid.set_vexpand(False)

            # Icon
            ext = os.path.splitext(file_info["name"])[1].lower()
            if ext == ".pdf":
                icon_name = "application-pdf-symbolic"
            elif ext == ".txt":
                icon_name = "text-x-generic-symbolic"
            elif ext in [".jpg", ".jpeg", ".png"]:
                icon_name = "image-x-generic-symbolic"
            else:
                icon_name = "text-x-generic-symbolic"
            icon = Gtk.Image.new_from_icon_name(icon_name)
            grid.attach(icon, 0, 0, 1, 1)

            # Name
            shorted_file_path = file_info["path"].replace(self.documents_path, "").lstrip(os.sep)
            name_label = Gtk.Label(label=shorted_file_path, xalign=0)
            name_label.set_hexpand(True)
            name_label.set_halign(Gtk.Align.START)
            name_label.set_max_width_chars(40)  # Limit to 40 chars (adjust as needed)
            #name_label.set_ellipsize(Pango.EllipsizeMode.END)  # Add this line
            grid.attach(name_label, 1, 0, 1, 1)

            # Size
            if os.path.exists(file_info["path"]):
                size_label_text = server.get_item_size(file_info["path"], True)
            else:
                size_label_text = ""
            size_label = Gtk.Label(label=size_label_text, xalign=0)
            size_label.set_hexpand(False)
            size_label.set_halign(Gtk.Align.START)
            grid.attach(size_label, 2, 0, 1, 1)

            # Date
            backup_date = datetime.fromtimestamp(file_info["date"]).strftime("%b %d %H:%M")
            date_label = Gtk.Label(label=backup_date, xalign=0)
            date_label.set_hexpand(False)
            date_label.set_halign(Gtk.Align.START)
            grid.attach(date_label, 3, 0, 1, 1)

            # Placeholder for last backup (optional)
            # last_backup_label = Gtk.Label(label="", xalign=0)
            # last_backup_label.set_hexpand(False)
            # last_backup_label.set_halign(Gtk.Align.START)
            # grid.attach(last_backup_label, 4, 0, 1, 1)

            listbox_row = Gtk.ListBoxRow()
            listbox_row.set_child(grid)
            listbox_row.device_path = file_info["path"]
            self.listbox.append(listbox_row)
    
    # Open location button
    def on_open_location_clicked(self, button):
        if self.selected_file_path:
            folder = os.path.dirname(self.selected_file_path)
            
            try:
                sub.Popen(["xdg-open", folder])
            except Exception as e:
                print("Failed to open folder:", e)

    def on_listbox_key_press(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_space:
            row = self.listbox.get_selected_row()
            if row:
                path = getattr(row, "device_path", None)
                if path:
                    self.open_preview_window(path)
            return True
        return False
    
    def open_preview_window(self, filepath):
        # If a preview window is already open, close it and return (toggle behavior)
        if getattr(self, "preview_window", None) is not None:
            self.preview_window.close()
            self.preview_window = None
            return

        ext = os.path.splitext(filepath)[1].lower()
        mime, _ = mimetypes.guess_type(filepath)
        if mime is None:
            mime = ""

        # Only allow preview for supported types
        previewable = False
        IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
        TEXT_EXTENSIONS = {".txt", ".py", ".md", ".csv", ".json", ".xml", ".ini", ".log", ".gd", ".js", ".html", ".css", ".sh", ".c", ".cpp", ".h", ".hpp", ".java", ".rs", ".go", ".toml", ".yml", ".yaml"}
        if (ext == ".pdf" or mime == "application/pdf") and POPPLER_AVAILABLE and os.path.exists(filepath):
            previewable = True
        elif (ext in TEXT_EXTENSIONS or mime.startswith("text")) and os.path.exists(filepath):
            previewable = True
        elif (ext in IMAGE_EXTENSIONS or mime.startswith("image")) and os.path.exists(filepath):
            previewable = True

        if not previewable:
            print("No preview available for this file.")
            return

        preview_win = Gtk.Window(title="File Preview")
        self.preview_window = preview_win  # Track the window

        preview_win.set_default_size(600, 400)
        preview_win.set_resizable(True)
        preview_win.set_deletable(True)
        preview_win.set_size_request(300, 200)

        # Set a maximum size (e.g., 90% of the screen)
        display = Gdk.Display.get_default()
        if not display:
            max_width = 800
            max_height = 600
        else:
            monitor_to_use = display.get_primary_monitor()
            if not monitor_to_use:
                monitors = display.get_monitors()
                if monitors.get_n_items() > 0:
                    monitor_to_use = monitors.get_item(0)
                else:
                    max_width = 800
                    max_height = 600
                    monitor_to_use = None
            if monitor_to_use:
                geometry = monitor_to_use.get_geometry()
                max_width = int(geometry.width * 0.9)
                max_height = int(geometry.height * 0.9)
            else:
                max_width = 800
                max_height = 600

        preview_win.set_default_size(min(600, max_width), min(400, max_height))
        preview_win.set_size_request(300, 200)

        # Add a scrolled window for the content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        preview_win.set_child(scrolled)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        scrolled.set_child(box)

        if (ext == ".pdf" or mime == "application/pdf") and POPPLER_AVAILABLE and os.path.exists(filepath):
            label = Gtk.Label(label="PDF preview not implemented in popup")
            box.append(label)
        elif (ext in TEXT_EXTENSIONS or mime.startswith("text")) and os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read(4096)
            textview = Gtk.TextView()
            textview.set_editable(False)
            textview.set_wrap_mode(Gtk.WrapMode.WORD)
            textview.get_buffer().set_text(text)
            textview.set_size_request(-1, 350)
            box.append(textview)
        elif (ext in IMAGE_EXTENSIONS or mime.startswith("image")) and os.path.exists(filepath):
            picture = Gtk.Picture.new_for_filename(filepath)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_vexpand(True)
            picture.set_hexpand(True)
            box.append(picture)

        # Add key controller to the preview window for Spacebar close
        key_controller = Gtk.EventControllerKey()
        def preview_key_press(controller, keyval, keycode, state):
            if keyval == Gdk.KEY_space:
                preview_win.close()
                return True
            return False
        key_controller.connect("key-pressed", preview_key_press)
        preview_win.add_controller(key_controller)

        # When the preview window is closed, clear the reference
        def on_close(win, *args):
            self.preview_window = None

        preview_win.connect("close-request", on_close)
        preview_win.present()
    def on_settings_clicked(self, button):
        # Only create one settings window at a time
        if getattr(self, "settings_window", None) is not None:
            self.settings_window.present()
            return
        self.settings_window = SettingsWindow(application=self.get_application())
        self.settings_window.set_modal(True)  # Make modal
        self.settings_window.set_transient_for(self)  # Set parent
        def on_close(win, *args):
            self.settings_window = None
        self.settings_window.connect("close-request", on_close)
        self.settings_window.present()
        
    ########################################################################################
    # Find updates for a file
    ########################################################################################
    def find_update(self, file_path):
        self.find_updates.set_sensitive(False)  # Disable button while searching

        # Extract the file name to search for all its backup versions
        def do_search():
            file_name = os.path.basename(file_path)
            results = []
            for root, dirs, files in os.walk(server.backup_folder_name()):
                for fname in files:
                    if fname == file_name:
                        fpath = os.path.join(root, fname)
                        fdate = os.path.getmtime(fpath)
                        results.append({
                            "name": fname,
                            "path": fpath,
                            "date": fdate
                        })
            results.sort(key=lambda x: x["date"], reverse=True)
            GLib.idle_add(self.show_update_window, file_name, results)

        threading.Thread(target=do_search, daemon=True).start()
    
    def show_update_window(self, file_name, results):
        """
        Show a window with all previous backups for the selected file.
            Reminder:
                - This will only show backups that are not in the main backup folder, e.g.: 01.01.2025/12-05/...
        """
        # Create a small window (no minimize/maximize)
        win = Gtk.Window(
            title=f'All previous backups for "{file_name}"',
            modal=True,
            transient_for=self,
            default_width=800,
            default_height=600
        )
        #win.set_resizable(True)
        #win.set_deletable(True)  # Allow close, but not minimize/maximize
        self.update_window = win  # Keep a reference

        def on_close(win, *args):
            self.update_window = None
            self.find_updates.set_sensitive(True)  # Re-enable button

        win.connect("close-request", on_close)

        # Header bar with Close and Restore buttons
        header = Gtk.HeaderBar()
        # header.set_show_close_button(True)
        win.set_titlebar(header)

        restore_button = Gtk.Button(label="Restore")
        restore_button.set_css_classes(["suggested-action"])
        restore_button.set_sensitive(False)
        header.pack_start(restore_button)

        # Main content: List of updates
        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6
        )
        win.set_child(vbox)

        # ListBox for updates inside a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        vbox.append(scrolled)

        listbox = Gtk.ListBox()
        scrolled.set_child(listbox)

        # For status messages
        status_label = Gtk.Label()
        vbox.append(status_label)

        progressbar = Gtk.ProgressBar()
        progressbar.set_hexpand(True)
        progressbar.set_visible(False)
        vbox.append(progressbar)

        # Populate the listbox with backup versions
        for result in results:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box()
            row.set_child(hbox)

            # Skip backups that are from the main backup folder
            if server.MAIN_BACKUP_LOCATION in result["path"]:
                # Only show backups that are not in the main backup folder
                # e.g.: 01.01.2025/12-05/...
                continue

            # Path (shortened)
            path_label = Gtk.Label(label=os.path.relpath(result["path"], server.backup_folder_name()), xalign=0)
            path_label.set_hexpand(True)
            hbox.append(path_label)

            # Extract backup date/time from the backup path
            #rel_path = os.path.relpath(result["path"], server.backup_folder_name())
            #parts = rel_path.split(os.sep)
            # if len(parts) >= 2:
            #     # Format: 12-05-2025/18-22/...
            #     backup_date_str = f"{parts[0]} {parts[1]}"
            # else:
            #     backup_date_str = "Unknown"

            # Destination label
            # Format: /username/Documents/test.txt:
            # destination: str = result["path"].replace(server.main_backup_folder() + "/", "")
            # destination = os.path.join(server.USER_HOME, destination)
            # print(destination)
            # destination_label = Gtk.Label(label=destination, xalign=0)
            # destination_label.set_hexpand(True)
            # hbox.append(destination_label)

            # Attach file path to row for later use
            row.file_path = result["path"]
            listbox.append(row)

        # Enable restore button only when a row is selected
        def on_row_selected(lb, row):
            restore_button.set_sensitive(row is not None)
        listbox.connect("row-selected", on_row_selected)

        # Restore logic
        def on_restore_clicked(btn):
            restore_button.set_sensitive(False)
            row = listbox.get_selected_row()
            if not row:
                return
            self.restore_button.connect("clicked", self.on_restore_button_clicked)
        restore_button.connect("clicked", on_restore_clicked)
        
        # Add key controller for Spacebar preview
        key_controller = Gtk.EventControllerKey()
        def on_key_press(controller, keyval, keycode, state):
            if keyval == Gdk.KEY_space:
                row = listbox.get_selected_row()
                if row and hasattr(row, "file_path"):
                    self.open_preview_window(row.file_path)
                return True
            return False
        key_controller.connect("key-pressed", on_key_press)
        listbox.add_controller(key_controller)

        win.connect("close-request", on_close)
        win.present()
    
    def on_restore_button_clicked(self, button):
        self.restore_button.set_sensitive(False)

        if self.selected_file_path:
            backup_root = os.path.abspath(server.main_backup_folder())
            abs_selected = os.path.abspath(self.selected_file_path)
            rel_path = os.path.relpath(abs_selected, backup_root)
            destination_path = os.path.join(server.USER_HOME, rel_path)

            def do_restore():
                try:
                    GLib.idle_add(self.restore_progressbar.set_visible, True)
                    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                    src = self.selected_file_path
                    dst = destination_path
                    total_size = os.path.getsize(src)
                    copied = 0
                    chunk_size = 1024 * 1024  # 1MB

                    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                        while True:
                            chunk = fsrc.read(chunk_size)
                            if not chunk:
                                break
                            fdst.write(chunk)
                            copied += len(chunk)
                            progress = copied / total_size if total_size else 1.0
                            GLib.idle_add(self.restore_progressbar.set_fraction, progress)
                    print(f"Restored {src} to {dst}")
                    shutil.copystat(src, dst)
                    self.restore_button.set_sensitive(True)

                    # Open the folder containing the restored file
                    #sub.Popen(["xdg-open", os.path.dirname(dst)])

                    # Close the update window after restore
                    if getattr(self, "update_window", None) is not None:
                        GLib.idle_add(self.update_window.close)
                except Exception as e:
                    print(f"Error restoring file: {e}")
                finally:
                    GLib.idle_add(self.restore_progressbar.set_visible, False)

            threading.Thread(target=do_restore, daemon=True).start()
        else:
            print("No file selected to restore.")

    def on_main_window_close(self, *args):
        self.get_application().quit()
        return False  # Propagate event
    
    def on_window_map(self, *args):
        self.search_entry.grab_focus()
        return False
    
    #########################################################################
    # LOGS
    ##########################################################################
    def show_backup_logs_dialog(self, button):
        """Display backup logs dialog."""
        logs_dialog = Adw.Window(
            transient_for=self,
            title="Backup Logs",
            modal=True,
            default_width=600,
            default_height=400,
        )

        # Read logs file from the server location
        log_file_path = server.LOG_LOCATION  # Make sure this is the correct path to your log files
        try:
            with open(log_file_path, "r") as log_file:
                log_content = log_file.read()
        except FileNotFoundError:
            log_content = "Error: Log file not found."
        except Exception as e:
            log_content = f"Error reading log file: {e}"

        # Header bar with buttons
        header_bar = Gtk.HeaderBar()

        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10)
        main_box.set_halign(Gtk.Align.FILL)
        logs_dialog.set_content(main_box)

        # Terminal-like Logs section
        log_view = Gtk.TextView(editable=False, cursor_visible=False, monospace=True)
        log_buffer = log_view.get_buffer()
        log_view.set_wrap_mode(Gtk.WrapMode.NONE)

        # Insert the log content into the buffer
        log_buffer.set_text(log_content)

        # Create a Scrolled Window for the logs
        logs_scrolled = Gtk.ScrolledWindow()
        logs_scrolled.set_child(log_view)
        logs_scrolled.set_vexpand(True)

        # Pack widgets into the main box
        main_box.append(header_bar)
        main_box.append(logs_scrolled)

        # Show the dialog
        logs_dialog.present()

    def on_restore_system_button_clicked(self, button):
        # Modal window
        win = Gtk.Window(
            title="System Restore",
            modal=True,
            transient_for=self,
            default_width=600,
            default_height=500
        )

        # HeaderBar with Restore button
        header = Gtk.HeaderBar()
        restore_btn = Gtk.Button(label="Restore")
        restore_btn.set_css_classes(["suggested-action"])
        restore_btn.set_halign(Gtk.Align.END)
        header.pack_end(restore_btn)
        win.set_titlebar(header)

        # Stack for pages
        stack = Gtk.Stack()
        win.set_child(stack)

        # --- PAGE 1: Selection ---
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)

        # Applications (Deb/RPM)
        self.apps_checkbox = Gtk.CheckButton(label="Applications (Deb/RPM)")
        vbox.append(self.apps_checkbox)

        # Applications dropdown area (hidden by default), with a scrolled window
        self.apps_dropdown_scrolled = Gtk.ScrolledWindow()
        self.apps_dropdown_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.apps_dropdown_scrolled.set_vexpand(True)
        self.apps_dropdown_scrolled.set_hexpand(True)
        self.apps_dropdown_scrolled.set_visible(False)
        self.apps_dropdown_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=24)
        self.apps_dropdown_scrolled.set_child(self.apps_dropdown_box)
        vbox.append(self.apps_dropdown_scrolled)

        def on_apps_toggled(check, pspec=None):
            self.apps_dropdown_scrolled.set_visible(check.get_active())
            if check.get_active() and not hasattr(self, "_apps_checkboxes_loaded"):
                self._apps_checkboxes_loaded = True
                # Add RPM packages
                rpm_folder = server.rpm_main_folder()
                if os.path.exists(rpm_folder):
                    for pkg in os.listdir(rpm_folder):
                        if pkg.endswith('.rpm'):
                            cb = Gtk.CheckButton(label=f"RPM: {pkg}")
                            cb.package_path = os.path.join(rpm_folder, pkg)
                            self.apps_dropdown_box.append(cb)
                # Add DEB packages
                deb_folder = server.deb_main_folder()
                if os.path.exists(deb_folder):
                    for pkg in os.listdir(deb_folder):
                        if pkg.endswith('.deb'):
                            cb = Gtk.CheckButton(label=f"DEB: {pkg}")
                            cb.package_path = os.path.join(deb_folder, pkg)
                            self.apps_dropdown_box.append(cb)
                if not any(isinstance(child, Gtk.CheckButton) for child in self.apps_dropdown_box):
                    self.apps_dropdown_box.append(Gtk.Label(label="No packages found."))

        self.apps_checkbox.connect("toggled", on_apps_toggled)

        # Files/Folders
        self.files_checkbox = Gtk.CheckButton(label="Files/Folders")
        vbox.append(self.files_checkbox)

        # Files/Folders dropdown area (hidden by default), with a scrolled window
        self.files_dropdown_scrolled = Gtk.ScrolledWindow()
        self.files_dropdown_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.files_dropdown_scrolled.set_vexpand(True)
        self.files_dropdown_scrolled.set_hexpand(True)
        self.files_dropdown_scrolled.set_visible(False)
        self.files_dropdown_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=24)
        self.files_dropdown_scrolled.set_child(self.files_dropdown_box)
        vbox.append(self.files_dropdown_scrolled)

        def on_files_toggled(check, pspec=None):
            self.files_dropdown_scrolled.set_visible(check.get_active())
            if check.get_active() and not hasattr(self, "_files_checkboxes_loaded"):
                self._files_checkboxes_loaded = True
                # List all files and folders in main_backup_folder
                main_folder = server.main_backup_folder()
                if os.path.exists(main_folder):
                    items = sorted(os.listdir(main_folder), key=lambda x: x.lower())
                    for item in items:
                        item_path = os.path.join(main_folder, item)
                        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        if os.path.isdir(item_path):
                            icon = Gtk.Image.new_from_icon_name("folder-symbolic")
                        else:
                            # Use a generic file icon or guess by extension
                            ext = os.path.splitext(item)[1].lower()
                            if ext in [".jpg", ".jpeg", ".png", ".gif"]:
                                icon_name = "image-x-generic-symbolic"
                            elif ext in [".pdf"]:
                                icon_name = "application-pdf-symbolic"
                            elif ext in [".txt", ".md", ".log"]:
                                icon_name = "text-x-generic-symbolic"
                            else:
                                icon_name = "text-x-generic-symbolic"
                            icon = Gtk.Image.new_from_icon_name(icon_name)
                        icon.set_pixel_size(16)
                        hbox.append(icon)
                        hbox.append(Gtk.Label(label=item))
                        cb = Gtk.CheckButton()
                        cb.set_child(hbox)
                        cb.restore_path = item_path
                        cb.is_folder = os.path.isdir(item_path)
                        self.files_dropdown_box.append(cb)
                else:
                    self.files_dropdown_box.append(Gtk.Label(label="No files or folders found."))

        self.files_checkbox.connect("toggled", on_files_toggled)

        # Flatpaks
        flatpak_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.flatpak_checkbox = Gtk.CheckButton(label="Flatpaks")
        flatpak_box.append(self.flatpak_checkbox)
        vbox.append(flatpak_box)

        # Flatpak dropdown area (hidden by default), now with a scrolled window
        self.flatpak_dropdown_scrolled = Gtk.ScrolledWindow()
        self.flatpak_dropdown_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.flatpak_dropdown_scrolled.set_vexpand(True)
        self.flatpak_dropdown_scrolled.set_hexpand(True)
        self.flatpak_dropdown_scrolled.set_visible(False)
        self.flatpak_dropdown_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=24)
        self.flatpak_dropdown_scrolled.set_child(self.flatpak_dropdown_box)
        flatpak_box.append(self.flatpak_dropdown_scrolled)

        def on_flatpak_toggled(check, pspec=None):
            self.flatpak_dropdown_scrolled.set_visible(check.get_active())
            if check.get_active() and not hasattr(self, "_flatpak_checkboxes_loaded"):
                self._flatpak_checkboxes_loaded = True
                # Load flatpak apps from file
                flatpak_txt = server.flatpak_txt_location()
                if os.path.exists(flatpak_txt):
                    with open(flatpak_txt, "r") as f:
                        for line in f:
                            app = line.strip()
                            if app:
                                cb = Gtk.CheckButton(label=app)
                                self.flatpak_dropdown_box.append(cb)
                else:
                    self.flatpak_dropdown_box.append(Gtk.Label(label="No Flatpak list found."))

        self.flatpak_checkbox.connect("toggled", on_flatpak_toggled)

        stack.add_named(vbox, "select")

        # --- PAGE 2: Progress ---
        progress_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            margin_top=32,
            margin_bottom=32,
            margin_start=32, 
            margin_end=32)
        progress_label = Gtk.Label(label="Restoring...")
        progress_label.set_halign(Gtk.Align.CENTER)
        progress_bar = Gtk.ProgressBar()
        progress_bar.set_hexpand(True)
        progress_bar.set_valign(Gtk.Align.CENTER)
        progress_box.append(progress_label)
        progress_box.append(progress_bar)

        # Terminal/log area
        terminal_scrolled = Gtk.ScrolledWindow()
        terminal_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        terminal_scrolled.set_vexpand(True)
        terminal_scrolled.set_hexpand(True)
        progress_box.append(terminal_scrolled)

        terminal_view = Gtk.TextView(editable=False, cursor_visible=False, monospace=True)
        terminal_buffer = terminal_view.get_buffer()
        terminal_scrolled.set_child(terminal_view)

        stack.add_named(progress_box, "progress")

        # --- Restore button handler ---
        def on_restore_clicked(btn):
            restore_btn.set_sensitive(False)
            stack.set_visible_child_name("progress")
            progress_bar.set_fraction(0)
            progress_label.set_text("Restoring...")

            terminal_buffer.set_text("")  # Clear terminal

            # Gather selected items
            restore_tasks = []

            # Applications (DEB/RPM)
            if self.apps_checkbox.get_active():
                child = self.apps_dropdown_box.get_first_child()
                while child:
                    if isinstance(child, Gtk.CheckButton) and child.get_active():
                        label = child.get_label()
                        pkg_path = getattr(child, "package_path", None)
                        if pkg_path and os.path.exists(pkg_path):
                            restore_tasks.append(("app", label, pkg_path))
                    child = child.get_next_sibling()

            # Files/Folders
            if self.files_checkbox.get_active():
                child = self.files_dropdown_box.get_first_child()
                while child:
                    if isinstance(child, Gtk.CheckButton) and child.get_active():
                        # Extract label from the hbox child
                        label = None
                        hbox = child.get_child()
                        if isinstance(hbox, Gtk.Box):
                            for subchild in hbox:
                                if isinstance(subchild, Gtk.Label):
                                    label = subchild.get_text()
                                    break
                        if label is None:
                            label = "Unknown"
                        restore_path = getattr(child, "restore_path", None)
                        is_folder = getattr(child, "is_folder", False)
                        if restore_path and os.path.exists(restore_path):
                            restore_tasks.append(("file", label, restore_path, is_folder))
                    child = child.get_next_sibling()

            # Flatpaks
            if self.flatpak_checkbox.get_active():
                child = self.flatpak_dropdown_box.get_first_child()
                while child:
                    if isinstance(child, Gtk.CheckButton) and child.get_active():
                        label = child.get_label()
                        restore_tasks.append(("flatpak", label, None))
                    child = child.get_next_sibling()

            if not restore_tasks:
                restore_tasks = [("info", "Nothing selected", None)]

            def append_terminal(text):
                end_iter = terminal_buffer.get_end_iter()
                terminal_buffer.insert(end_iter, text + "\n")
                # Scroll to end
                mark = terminal_buffer.create_mark(None, terminal_buffer.get_end_iter(), False)
                terminal_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
            
            # Files and Folders restoration
            def restore_folder_with_incrementals():
                """
                Applies incremental updates by copying, for each file, the latest updated version
                from the update folders (sorted in descending order) to dest_root.

                For each file in the update folders:
                - Compute the file's path relative to the update folder.
                - Remove the first path element if necessary (for example, if the update folder's name
                    is part of the relative path and should not be).
                - If the file has already been updated by a later (newer) update, skip it.
                - Otherwise, copy the file to the destination, ensuring that the directory structure is preserved.
                """
                base_backup_folder = server.main_backup_folder()
                
                # 2. Apply incremental updates (if any)
                updates_root = server.backup_folder_name()
                if os.path.exists(updates_root):
                    incremental_folders = [folder for folder in os.listdir(updates_root)
                                        if os.path.isdir(os.path.join(updates_root, folder))]
                    base_folder_name = os.path.basename(base_backup_folder)
                    if base_folder_name in incremental_folders:
                        incremental_folders.remove(base_folder_name)
                    try:
                        incremental_folders.sort(
                            key=lambda folder: datetime.strptime(folder, "%d-%m-%Y"),
                            reverse=True
                        )
                    except Exception as e:
                        GLib.idle_add(append_terminal, f"Error parsing update folder names: {e}")
                        return

                    updated_files = set()
                    file_count = 0
                    for _, date in enumerate(incremental_folders):
                        update_path = os.path.join(updates_root, str(date))
                        for root, dirs, files in os.walk(update_path):
                            for file in files:
                                rel_path = os.path.relpath(os.path.join(root, file), update_path)
                                rel_path = "/".join(rel_path.split('/')[1:])
                                if rel_path in updated_files:
                                    continue
                                dest_item = os.path.join(server.HOME_USER, rel_path)
                                try:
                                    #os.makedirs(os.path.dirname(dest_item), exist_ok=True)
                                    #shutil.copy2(os.path.join(root, file), dest_item)
                                    updated_files.add(rel_path)
                                    file_count += 1
                                    # Only update UI every 20 files
                                    if file_count % 20 == 0:
                                        GLib.idle_add(progress_label.set_text, f"Restoring: {rel_path}")
                                        GLib.idle_add(append_terminal, f"Incremental: {os.path.join(root, file)} → {dest_item}")
                                        time.sleep(0.01)  # Yield to avoid UI freeze
                                except Exception as e:
                                    GLib.idle_add(append_terminal, f"Error updating {rel_path}: {e}")
                    # Final update for the last file
                    GLib.idle_add(progress_label.set_text, f"Restoring: {rel_path}")
                    GLib.idle_add(append_terminal, f"Incremental: {os.path.join(root, file)} → {dest_item}")

            def restore_folder(src_root: str, dest_root: str):
                count = 0
                for root, dirs, files in os.walk(src_root):
                    for file in files:
                        src_item = os.path.join(root, file)
                        relative_path = os.path.relpath(src_item, src_root)
                        dest_item = os.path.join(dest_root, relative_path)
                        try:
                            os.makedirs(os.path.dirname(dest_item), exist_ok=True)
                            shutil.copy2(src_item, dest_item)
                            count += 1
                            # Only update UI every 20 files
                            if count % 20 == 0:
                                GLib.idle_add(progress_label.set_text, f"Restoring: {relative_path}")
                                GLib.idle_add(append_terminal, f"Restored: {src_item} → {dest_item}")
                                time.sleep(0.01)  # Yield to avoid UI freeze
                        except Exception as e:
                            GLib.idle_add(append_terminal, f"Error copying {src_item}: {e}")
                # Final update for the last file
                GLib.idle_add(progress_label.set_text, f"Restoring: {relative_path}")
                GLib.idle_add(append_terminal, f"Restored: {src_item} → {dest_item}")

            def run_restore():
                total = len(restore_tasks)
                folders_restored = False
                for idx, task in enumerate(restore_tasks):
                    kind = task[0]
                    label = task[1]
                    GLib.idle_add(progress_label.set_text, f"Restoring: {label}")
                    GLib.idle_add(append_terminal, f"Restoring: {label}")

                    if kind == "app":
                        package_manager = check_package_manager()
                        TEST_MODE = False  # Set to True to simulate, False for real install
                        if package_manager == 'deb':
                            cmd = ["dpkg", "-i", pkg_path]
                        elif package_manager == 'rpm':
                            cmd = ["rpm", "-ivh", "--replacepkgs", pkg_path]
                        else:
                            cmd = None

                        if cmd:
                            try:
                                if TEST_MODE:
                                    # Simulate with echo for testing
                                    proc = sub.Popen(
                                        ["echo", f"Simulating install of {label} ({' '.join(cmd)})"],
                                        stdout=sub.PIPE, stderr=sub.PIPE, text=True
                                    )
                                else:
                                    proc = sub.Popen(cmd, stdout=sub.PIPE, stderr=sub.PIPE, text=True)
                                for line in proc.stdout:
                                    GLib.idle_add(append_terminal, line.rstrip())
                                for line in proc.stderr:
                                    GLib.idle_add(append_terminal, line.rstrip())
                                proc.wait()
                                if proc.returncode == 0:
                                    GLib.idle_add(append_terminal, f"Installed: {label}")
                                else:
                                    GLib.idle_add(append_terminal, f"Error installing {label}")
                            except Exception as e:
                                GLib.idle_add(append_terminal, f"Error: {e}")
                    elif kind == "file":
                        restore_path = task[2]
                        is_folder = task[3]
                        TEST_MODE = False  # Set to True to simulate, False for real restore
                        try:
                            if is_folder:
                                if TEST_MODE:
                                    GLib.idle_add(append_terminal, f"[TEST MODE] Would restore folder: {label}")
                                else:
                                    restore_folder(restore_path, server.HOME_USER)
                                    GLib.idle_add(append_terminal, f"Restored folder: {label}")
                            else:
                                dest_item = os.path.join(server.HOME_USER, os.path.basename(restore_path))
                                if TEST_MODE:
                                    GLib.idle_add(progress_label.set_text, f"[TEST MODE] Restoring: {os.path.basename(restore_path)}")
                                    GLib.idle_add(append_terminal, f"[TEST MODE] Would restore file: {restore_path} → {dest_item}")
                                else:
                                    shutil.copy2(restore_path, dest_item)
                                    GLib.idle_add(progress_label.set_text, f"Restoring: {os.path.basename(restore_path)}")
                                    GLib.idle_add(append_terminal, f"Restored file: {restore_path} → {dest_item}")
                        except Exception as e:
                            GLib.idle_add(append_terminal, f"Error restoring {label}: {e}")
                    elif kind == "flatpak":
                        flatpak_ref = label
                        try:
                            GLib.idle_add(progress_label.set_text, f"Installing Flatpak: {flatpak_ref}")
                            GLib.idle_add(append_terminal, f"Installing Flatpak: {flatpak_ref}")
                            print(f"Installing Flatpak: {flatpak_ref}")
                            # --- TEST MODE: set to True to simulate, False to really install ---
                            TEST_MODE = False

                            if TEST_MODE:
                                # Simulate with echo for testing
                                proc = sub.Popen(
                                    ["echo", f"Simulating install of {flatpak_ref}"],
                                    stdout=sub.PIPE, stderr=sub.PIPE, text=True
                                )
                            else:
                                # Real Flatpak install
                                proc = sub.Popen(
                                    ["flatpak", "install", "--system", "--noninteractive", "--assumeyes", flatpak_ref],
                                    stdout=sub.PIPE, stderr=sub.PIPE, text=True
                                )
                            for line in proc.stdout:
                                GLib.idle_add(append_terminal, line.rstrip())
                            for line in proc.stderr:
                                GLib.idle_add(append_terminal, line.rstrip())
                            proc.wait()
                            if proc.returncode == 0:
                                GLib.idle_add(append_terminal, f"Successfully installed Flatpak: {flatpak_ref}")
                            else:
                                GLib.idle_add(append_terminal, f"Failed to install Flatpak '{flatpak_ref}'")
                        except Exception as e:
                            GLib.idle_add(append_terminal, f"Error installing Flatpak {flatpak_ref}: {e}")
                    elif kind == "info":
                        GLib.idle_add(append_terminal, label)

                    GLib.idle_add(progress_bar.set_fraction, (idx + 1) / total)
                    time.sleep(0.2)

                # After all restores, do incrementals if any folder was restored
                if folders_restored:
                    restore_folder_with_incrementals()

                GLib.idle_add(progress_bar.set_fraction, 1.0)
                GLib.idle_add(progress_label.set_text, "Restore Complete!")
                GLib.idle_add(append_terminal, "Restore Complete!")
                GLib.idle_add(restore_btn.set_sensitive, True)

            threading.Thread(target=run_restore, daemon=True).start()

        restore_btn.connect("clicked", on_restore_clicked)
        win.present()


class SettingsWindow(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Settings")
        self.set_default_size(600, 600)

        self.ignored_folders = []
        self.programmatic_change = False  
        self.switch_cooldown_active = False  # To track the cooldown state

        # --- Backups Tab ---
        backups_page = Adw.PreferencesPage(title="Backups")
        backups_page.set_icon_name("backups-app-symbolic")
        backups_group = Adw.PreferencesGroup(title="Back Up Automatically")
        
        auto_backup_row = Adw.ActionRow(title="Enable Automatic Backups")
        self.auto_backup_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.auto_backup_switch.connect("notify::active", self.on_auto_backup_switch_toggled)
        auto_backup_row.add_suffix(self.auto_backup_switch)
        backups_group.add(auto_backup_row)

        # Use a horizontal box for label + switch
        auto_backup_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        backups_group.add(auto_backup_box)
        backups_page.add(backups_group)
        self.add(backups_page)

        # --- Create a new ActionRow for "Exclude Hidden Files" ---
        self.exclude_hidden_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        exclude_hidden_files_row = Adw.ActionRow(title="Ignore hidden files")
        exclude_hidden_files_row.add_suffix(self.exclude_hidden_switch)
        exclude_hidden_files_row.set_activatable_widget(self.exclude_hidden_switch)
        exclude_hidden_files_row.set_selectable(False)
        self.exclude_hidden_switch.connect("notify::active", self.on_exclude_hidden_switch_toggled)
        
        # --- Folders to Ignore Tab ---
        folders_to_ignore_page = Adw.PreferencesPage(title="Folders")
        folders_to_ignore_page.set_icon_name("folder-symbolic")

        # Bold title for the "ignore hidden files"
        self.ignore_hidden_files_group = Adw.PreferencesGroup(title="Ignore Hidden Files")
        # Bold title for the folders group
        self.folders_to_ignore_group = Adw.PreferencesGroup(title="Folders To Ignore")
        
        # Create a vertical box to hold the header and the folder list
        folders_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Horizontal box for label and add button (header)
        folders_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        folders_header.set_halign(Gtk.Align.CENTER)

        add_folder_button = Gtk.Button(icon_name="list-add-symbolic", halign=Gtk.Align.CENTER)
        add_folder_button.add_css_class("flat")
        add_folder_button.connect("clicked", self.on_add_folder_clicked)
        folders_header.append(add_folder_button)

        folders_vbox.append(folders_header)

        # Box for the folder rows
        self.ignore_folders_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        folders_vbox.append(self.ignore_folders_box)
        
        self.ignore_hidden_files_group.add(exclude_hidden_files_row)
        self.folders_to_ignore_group.add(folders_vbox)

        folders_to_ignore_page.add(self.ignore_hidden_files_group)
        folders_to_ignore_page.add(self.folders_to_ignore_group)
        self.add(folders_to_ignore_page)

        ##########################################################################
		# STARTUP
		##########################################################################
        self.auto_backup_checkbox()
        self.auto_select_hidden_itens()  # Exclude hidden files
        self.load_folders_from_config()
        self.display_excluded_folders()  
    
    def display_excluded_folders(self):
        """Display loaded excluded folders."""
        for folder in self.ignored_folders:
            logging.info("Adding folder: %s", folder)
            self.add_folder_to_list(folder)
    
    def load_folders_from_config(self):
        """Loads folders from the config file."""
        config = configparser.ConfigParser()

        if os.path.exists(server.CONF_LOCATION):  # Ensure the config file exists
            config.read(server.CONF_LOCATION)
            if 'EXCLUDE_FOLDER' in config:  # Check if the section exists
                self.ignored_folders = config.get('EXCLUDE_FOLDER', 'folders').split(',')
                # Remove empty strings in case of trailing commas
                self.ignored_folders = [folder.strip() for folder in self.ignored_folders if folder.strip()]
    
    ######################################################################################
    # Automatic Backup Switch
    ######################################################################################
    def auto_backup_checkbox(self):
        # Get stored driver_location and driver_name
        automatically_backup = server.get_database_value(
            section='BACKUP',
            option='automatically_backup')

        self.programmatic_change = True  # Set the flag to indicate programmatic change

        if automatically_backup:
            self.auto_backup_switch.set_active(True)
        else:
            self.auto_backup_switch.set_active(False)
        
        self.programmatic_change = False  # Reset the flag after programmatic change
	
    def enable_switch(self, switch):
        """Re-enable the switch after the cooldown period."""
        self.switch_cooldown_active = False
        self.auto_backup_switch.set_sensitive(True)  # Re-enable the switch
	
    def disable_switch_for_cooldown(self, switch):
        """Disables the switch and re-enables it after the cooldown period."""
        self.switch_cooldown_active = True
        switch.set_sensitive(False)  # Disable the switch to prevent user interaction

        def enable_switch_after_cooldown():
            time.sleep(5)  # Cooldown delay
            GLib.idle_add(self.enable_switch, switch)  # Re-enable in the main thread

        # Start the cooldown in a new thread to avoid blocking the UI
        threading.Thread(target=enable_switch_after_cooldown, daemon=True).start()
	
    def on_auto_backup_switch_toggled(self, switch, pspec):
        """Handle the 'Back Up Automatically' switch toggle."""
        if self.programmatic_change or self.switch_cooldown_active:
            return  # Exit the function if it's a programmatic change or cooldown active

        # Check if the switch is being enabled
        if switch.get_active():
            # Disable the switch immediately and start the cooldown
            self.disable_switch_for_cooldown(switch)

            # Wait for user's confirmation to proceed
            def handle_confirmation(confirmed):
                if not confirmed:
                    # User declined, reset the switch to its previous state
                    self.programmatic_change = True
                    switch.set_active(False)
                    self.programmatic_change = False
                    return

                # User confirmed, proceed with enabling automatic backup
                if not server.is_daemon_running():
                    self.start_daemon()  # Only start if not running
                
                def create_autostart_entry():
                    autostart_dir = os.path.expanduser("~/.config/autostart/")
                    os.makedirs(autostart_dir, exist_ok=True)

                    desktop_file_content = f"""
                        [Desktop Entry]
                        Type=Application
                        Exec=flatpak run --command=python3 {server.ID} /app/share/{server.APP_NAME_CLOSE_LOWER}/src/at_boot.py
                        X-GNOME-Autostart-enabled=true
                        Name={server.APP_NAME}
                        Comment[en_US]=Automatically start {server.APP_NAME}
                        Comment=Automatically start {server.APP_NAME}
                        """

                    with open(os.path.join(autostart_dir, f"{server.APP_NAME_CLOSE_LOWER}_autostart.desktop"), 'w') as f:
                        f.write(desktop_file_content)
                    logging.info("Autostart entry created.")

                create_autostart_entry()  # Create .desktop file for auto startup
                server.write_backup_status(status='Monitoring')  # Update backup status

                # Update the conf file
                server.set_database_value(
                    section='BACKUP',
                    option='automatically_backup',
                    value='true')

            # Show the confirmation dialog
            self.confirm_backup_device(handle_confirmation)
        else:
            # If the switch is being disabled, proceed without showing the dialog
            self.stop_daemon()  # Stop the daemon
            self.remove_autostart_entry()  # Optionally remove autostart entry
            server.write_backup_status(status='Offline')  # Update backup status

            # Update the conf file
            server.set_database_value(
                section='BACKUP',
                option='automatically_backup',
                value='false'
            )

    def confirm_backup_device(self, callback):
        """Show a confirmation dialog to confirm the backup device."""
        device_name = server.get_database_value(
            section='DRIVER',
            option='driver_name'
        )

        # Create the Adw.MessageDialog
        dialog = Adw.MessageDialog(
            transient_for=self,
            modal=True,
            title="Enable Automatic Backup",
            body=f"Do you want to back up to this device: '{device_name}'?"
        )

        # Add responses to the dialog
        dialog.add_response("yes", "Yes")
        dialog.set_response_appearance("yes", Adw.ResponseAppearance.SUGGESTED)
        dialog.add_response("no", "No")
        dialog.set_default_response("no")
        dialog.set_close_response("no")

        # Connect to the response signal
        def on_response(dialog, response):
            dialog.close()
            if response == "yes":
                print(f"User confirmed backup to device: {device_name}")
                callback(True)  # Call the callback with True
            else:
                print("User declined automatic backup.")
                callback(False)  # Call the callback with False

        dialog.connect("response", on_response)

        # Show the dialog
        dialog.show()

    def start_daemon(self):
        """Start the daemon and store its PID, ensuring only one instance runs."""
        # Start a new daemon process
        process = sub.Popen(['python3', server.DAEMON_PY_LOCATION], start_new_session=True)

        # Store the new PID in the file
        with open(server.DAEMON_PID_LOCATION, 'w') as f:
            f.write(str(process.pid))
        print(f"Daemon started with PID {process.pid}.")

    def stop_daemon(self):
        """Stop the daemon by reading its PID."""
        if os.path.exists(server.DAEMON_PID_LOCATION):
            with open(server.DAEMON_PID_LOCATION, 'r') as f:
                pid = int(f.read())

            try:
                os.kill(pid, signal.SIGTERM)  # Send termination signal
                os.waitpid(pid, 0)  # Wait for the process to terminate
                os.remove(server.DAEMON_PID_LOCATION)
                print(f"Daemon with PID {pid} stopped.")
            except OSError as e:
                print(f"Failed to stop daemon with PID {pid}. Error: {e}")
                if e.errno == errno.ESRCH:
                    print(f"Daemon with PID {pid} not found. Removing stale PID file.")
                    os.remove(server.DAEMON_PID_LOCATION)
        else:
            print("Daemon is not running.")

    def remove_autostart_entry(self):
        if os.path.exists(server.autostart_file):
            os.remove(server.autostart_file)
            logging.info("Autostart entry removed.")


    def create_folder_row(self, folder_name):
        """Create a row for folders with a trash icon."""
        row = Adw.ActionRow(title=folder_name)
        trash_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
        trash_button.add_css_class("flat")
        trash_button.connect("clicked", self.on_remove_folder_clicked, row, folder_name)
        row.add_suffix(trash_button)
        return row

    def on_remove_folder_clicked(self, button, row, folder_name):
        """Remove a folder row from the group."""
        parent = row.get_parent()
        parent.remove(row)

        # Remove the folder from the internal list
        if folder_name in self.ignored_folders:
            self.ignored_folders.remove(folder_name)

        # Save the updated list of folders to the config file
        self.save_folders_to_config()

        # Debugging: print the current ignored folders
        logging.info(f"Removed folder: {folder_name}")
        logging.info(f"Remaining ignored folders: {self.ignored_folders}")
        print(f"Removed folder: {folder_name}")
        print(f"Remaining ignored folders: {self.ignored_folders}")

    def on_add_folder_clicked(self, button):
        """Open a folder chooser dialog to add a folder to Ignore group."""
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select a Folder To Ignore")
        dialog.set_modal(True)
        dialog.set_accept_label("_Select")

        def on_select_folder(dialog, result):
            try:
                folder = dialog.select_folder_finish(result)
                if folder:
                    folder_path = folder.get_path()
                    if folder_path not in self.ignored_folders:
                        self.ignored_folders.append(folder_path)
                        print(f"Selected folder: {folder_path}")
                        self.add_folder_to_list(folder_path)
                        self.save_folders_to_config()
            except Exception as e:
                print("Error selecting folder:", e)

        dialog.select_folder(self.get_application().get_active_window(), None, on_select_folder)
    
    def add_folder_to_list(self, folder):
        ignore_row = self.create_folder_row(folder)
        self.folders_to_ignore_group.add(ignore_row)

    def save_folders_to_config(self):
        """Saves the current list of ignored folders to the config file."""
        config = configparser.ConfigParser()
        config['EXCLUDE_FOLDER'] = {'folders': ','.join(self.ignored_folders)}
        
        server.set_database_value(
            section='EXCLUDE_FOLDER', 
            option='folders', 
            value=','.join(self.ignored_folders))
		
    def on_exclude_hidden_switch_toggled(self, switch, pspec):
        """Handle the 'Ignore Hidden Files' switch toggle."""
        true_false: str = 'false'

        # Handle the toggle state of the ignore hidden switch
        if switch.get_active():
            true_false = 'true'

        # Update the conf file
        server.set_database_value(
            section='EXCLUDE',
            option='exclude_hidden_itens',
            value=true_false)
    
    def auto_select_hidden_itens(self):
        exclude_hidden_itens: bool = server.get_database_value(
            section='EXCLUDE',
            option='exclude_hidden_itens')

        if exclude_hidden_itens:
            self.exclude_hidden_switch.set_active(True)
        else:
            self.exclude_hidden_switch.set_active(False)

class BackupApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=server.ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = BackupWindow(application=self)
        win.present()


def main():
    app = BackupApp()
    return app.run(None)


if __name__ == "__main__":
    main()
