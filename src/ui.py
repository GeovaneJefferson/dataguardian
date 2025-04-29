import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk
from server import *
from device_location import device_location

server = SERVER()
WIDTH = 600
HEIGHT = 600


class BackupSettingsWindow(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
		##########################################################################
		# WINDOW
		##########################################################################
		# Create a Preferences Window with tabs
        self.set_title("Settings")
        # self.set_size_request(WIDTH, HEIGHT)
        self.set_resizable(True)  # Prevent window from being resized
		
        ##########################################################################
		# VARIABLES
		##########################################################################
        self.ignored_folders = []
        self.documents_path = os.path.expanduser(server.main_backup_folder())
        self.files = self.scan_files_folder_threaded()
        
        
        self.page_size = 50  # Number of results per page
        self.current_page = 0  # Start from the first page

        self.search_results = []  # Store results based on filtering/searching
        self.date_combo = None  # To reference date combo in filtering
        self.search_timer = None  # Initialize in the class constructor
		
        self.programmatic_change = False  
        self.switch_cooldown_active = False  # To track the cooldown state

        ##########################################################################
		# UI
		##########################################################################
        self.create_general_page()
        self.create_folders_page()
        self.create_restore_files_page()

        ##########################################################################
		# STARTUP
		##########################################################################
        self.auto_backup_checkbox()
        self.auto_select_hidden_itens()  # Exclude hidden files
        self.auto_select_backup_device()
        self.load_folders_from_config()
        self.display_excluded_folders()  

        #self.handle_backup_status()  # Backup status: Monitoring, Backing up etc...


##########################################################################
# UI
##########################################################################
    def update_ui_information(self):
        recent_backup_informations = server.get_database_value(
			section='RECENT',
			option='recent_backup_timeframe')
        
        if recent_backup_informations:
            self.recent_backup_label.set_text(recent_backup_informations)
        else:
            self.recent_backup_label.set_text('Never')

    def on_backup_device_selected(self, dropdown, gparam):
        """Handle the change in backup device selection."""
        selected_device = dropdown.get_selected_item()

        if selected_device:
            selected_device_name = selected_device.get_string()  # Use get_string() for Gio.StringObject
            driver_location = f"{device_location()}/{SERVER().USERNAME}/{selected_device_name}"
            
            print(f"Selected backup device: {selected_device_name}")
            
            # Update and add the device to the conf file
            # Devices location
            server.set_database_value(
                section='DRIVER',
                option='driver_location',
                value=str(driver_location)
            )

            # Devices name
            server.set_database_value(
                section='DRIVER',
                option='driver_name',
                value=str(selected_device_name)
            )

            # Enable switch
            # self.auto_backup_switch.set_sensitive(True)

    def create_folders_page(self):
        """Create the Folders tab."""
        preferences_page = Adw.PreferencesPage()
        preferences_page.set_icon_name("folder-open-symbolic")
        preferences_page.set_title("Folders")

        # Hidden file to Ignore group
        self.hidden_ignore_group = Adw.PreferencesGroup(title="Hidden files")

        # Create a new ActionRow for "Exclude Hidden Files"
        exclude_hidden_files_row = Adw.ActionRow(title="Ignore hidden files")
        exclude_hidden_files_row.set_activatable(True)

        # Create the Gtk.Switch widget for toggling the hidden file ignore feature
        self.exclude_hidden_files = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.exclude_hidden_files.connect("notify::active", self.on_ignore_hidden_switch_toggled)

        # Add the switch to the ActionRow as a suffix
        exclude_hidden_files_row.add_suffix(self.exclude_hidden_files)


        # Add the ActionRow to your Hidden ignore group
        self.hidden_ignore_group.add(exclude_hidden_files_row)

        # Folders to Ignore group
        self.ignore_group = Adw.PreferencesGroup(title="Folders to Ignore")
        # ignore_row = self.create_folder_row("Trash")
        # self.ignore_group.add(ignore_row)

        # Add "+" button to Back Up group
        add_folder_button = Gtk.Button(icon_name="list-add-symbolic", halign=Gtk.Align.CENTER)
        add_folder_button.connect("clicked", self.on_add_folder_clicked)
        self.ignore_group.add(add_folder_button)

        preferences_page.add(self.hidden_ignore_group)
        preferences_page.add(self.ignore_group)
        self.add(preferences_page)

        return preferences_page
    
    def create_general_page(self):
        """Create the General tab."""
        preferences_page = Adw.PreferencesPage()
        preferences_page.set_icon_name("settings-symbolic")
        preferences_page.set_title("General")

        # Storage Group
        storage_group = Adw.PreferencesGroup(title="Storage")

        # Dropdown for Storage Location
        location_row = Adw.ActionRow(title="Location")
        location_model = Gio.ListStore.new(Gtk.StringObject)

        for option in ["Local Storage"]:
            location_model.append(Gtk.StringObject.new(option))

        self.location_dropdown = Gtk.DropDown(model=location_model, valign=Gtk.Align.CENTER)
        self.location_dropdown.set_selected(0)
        #self.location_dropdown.add_css_class("flat")

        location_row.add_suffix(self.location_dropdown)
        storage_group.add(location_row)

        # Create a ListStore for the dropdown
        self.backup_device_model = Gio.ListStore.new(Gtk.StringObject)

        # Create the dropdown for available devices
        self.location_dropdown = Gtk.DropDown(
            model=self.backup_device_model,
            valign=Gtk.Align.CENTER
        )
        self.location_dropdown.set_selected(0)
        self.location_dropdown.connect("notify::selected", self.on_backup_device_selected)

        # Add the dropdown to an ActionRow
        self.driver_location_row = Adw.ActionRow(title="Choose a backup device:")
        self.driver_location_row.add_suffix(self.location_dropdown)
        storage_group.add(self.driver_location_row)
        
        # Daemon status
        daemon_satus_row = Adw.ActionRow(title="Backup Status:")
        self.daemon_status_label = Gtk.Label()
        self.daemon_status_label.set_halign(Gtk.Align.START)
        daemon_satus_row.add_suffix(self.daemon_status_label)
        storage_group.add(daemon_satus_row)
        
        # Periodically update the daemon status
        GLib.timeout_add(1000, self.update_daemon_status)

        # Dynamically update the device list
        self.available_devices_location()  # Populate the dropdown initially

        # Back Up Group
        backup_group = Adw.PreferencesGroup(title="Backups")

        # Add "Back Up Automatically" switch
        auto_backup_row = Adw.ActionRow(title="Back Up Automatically")
        self.auto_backup_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.auto_backup_switch.connect("notify::active", self.on_auto_backup_switch_toggled)
        auto_backup_row.add_suffix(self.auto_backup_switch)
        # storage_group.add(auto_backup_row)
        backup_group.add(auto_backup_row)

        # Dialog Group for Logs
        logs_group = Adw.PreferencesGroup(title="Logs")

        log_row = Adw.ActionRow(title="View Backup Logs")
        log_button = Gtk.Button(label="Logs", valign=Gtk.Align.CENTER)
        log_button.connect("clicked", self.show_backup_logs_dialog)  # Show logs, not the progress dialog
        log_row.add_suffix(log_button)
        logs_group.add(log_row)

        # Add "Most Recent Backup" row
        recent_backup_row = Adw.ActionRow(title="Most Recent Backup")
        self.recent_backup_label = Gtk.Label(halign=Gtk.Align.END)
        recent_backup_row.add_suffix(self.recent_backup_label)
        logs_group.add(recent_backup_row)

        # Add other groups to the preferences page
        preferences_page.add(storage_group)
        preferences_page.add(backup_group)
        preferences_page.add(logs_group)

        self.add(preferences_page)

        # UI updates
        self.update_ui_information()
        return preferences_page
    
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

    def update_daemon_status(self):
        """
        Periodically fetch and update the daemon's current action.
        """
        try:
            current_action = server.read_backup_status()  # Fetch the current action from the shared state
            self.daemon_status_label.set_text(f"{current_action}")
            print(current_action)
        except Exception as e:
            logging.error(f"Error updating daemon status: {e}")
        return True  # Continue the timeout
    
    def handle_backup_status(self):
        # Get stored driver_location and driver_name
        backup_status = server.read_backup_status()
        
        # Update every time app main window opens
        self.daemon_status_label.set_text(backup_status)

    def create_restore_files_page(self):
        """Creates the Restore Files page."""
        restore_page = Adw.PreferencesPage(title="Restore Files")
        restore_page.set_icon_name("view-refresh-symbolic")


        # --- Restore Options Group ---
        search_group = Adw.PreferencesGroup(title="Search Settings")
        restore_page.add(search_group)

        # Row for selecting the backup source
        search_entry = Gtk.SearchEntry(placeholder_text="Search backup sources...")
        search_entry.set_tooltip_text("Type to search for a backup source")
        search_entry.connect("search-changed", self.on_search_changed)  # Add handler for searching backup sources
        search_group.add(search_entry)

        # --- Search Results ---
        results_group = Adw.PreferencesGroup(title="Search Results")
        restore_page.add(results_group)

        # Scrollable area to display search results
        scrolled_results = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scrolled_results.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # FlowBox for displaying restore results (e.g., files or folders)
        self.results_grid = Gtk.FlowBox(
            max_children_per_line=5,
            selection_mode=Gtk.SelectionMode.NONE,
            homogeneous=True,
            valign=Gtk.Align.START,
        )
        self.results_grid.set_margin_top(5)
        self.results_grid.set_margin_bottom(5)
        self.results_grid.set_margin_start(5)
        self.results_grid.set_margin_end(5)
        self.results_grid.set_row_spacing(5)
        self.results_grid.set_column_spacing(5)

        scrolled_results.set_child(self.results_grid)
        results_group.add(scrolled_results)

        # Add the restore page to the window
        self.add(restore_page)


    def create_folder_row(self, folder_name):
        """Create a row for folders with a trash icon."""
        row = Adw.ActionRow(title=folder_name)
        trash_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
        trash_button.add_css_class("flat")
        trash_button.connect("clicked", self.on_remove_folder_clicked, row, folder_name)
        row.add_suffix(trash_button)
        return row
        
    def on_add_folder_clicked(self, button):
        """Open a folder chooser dialog to add a folder to Ignore group."""
        dialog = Gtk.FileDialog.new()  # Create a new FileDialog instance
        
        # Set up the dialog properties
        dialog.set_title("Select a Folder To Ignore")
        dialog.set_modal(True)  # Make it modal
        dialog.set_accept_label("_Select")  # Set the accept button label
        
        def on_select_folder(dialog, result):
            """Callback function to handle the selected folder."""
            try:
                folder = dialog.select_folder_finish(result)  # Get the selected folder
                if folder:
                    folder_path = folder.get_path()
                    if folder_path not in self.ignored_folders:
                        self.ignored_folders.append(folder_path)
                        print(f"Selected folder: {folder_path}")

                        self.add_folder_to_list(folder_path)
                        self.save_folders_to_config()
            except:
                pass

        # Use the select_folder method to open the folder selection dialog
        dialog.select_folder(self.get_application().get_active_window(), None, on_select_folder)

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

    def save_folders_to_config(self):
        """Saves the current list of ignored folders to the config file."""
        config = configparser.ConfigParser()
        config['EXCLUDE_FOLDER'] = {'folders': ','.join(self.ignored_folders)}
        
        server.set_database_value(
            section='EXCLUDE_FOLDER', 
            option='folders', 
            value=','.join(self.ignored_folders))
		
    def show_progress_dialog(self, button):
        """Display the progress dialog."""
        progress_dialog = Adw.Window(
            transient_for=self,
            title="Backing Up...",
            modal=True,
            default_width=WIDTH,
            default_height=HEIGHT,
        )

        # Header bar with buttons
        header_bar = Gtk.HeaderBar()
        cloase_button = Gtk.Button(label="Close")
        cloase_button.connect("clicked", lambda b: progress_dialog.close())

        resume_button = Gtk.Button(label="Resume Later")
        resume_button.add_css_class("suggested-action")
        resume_button.connect("clicked", lambda b: progress_dialog.close())

        header_bar.pack_start(cloase_button)
        header_bar.pack_end(resume_button)

        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10)
        main_box.set_halign(Gtk.Align.FILL)
        progress_dialog.set_content(main_box)

        # title_label = Gtk.Label(label="<b>Backing Up...</b>", use_markup=True)
        # title_label.set_halign(Gtk.Align.START)

        status_label = Gtk.Label(label="Creating the first backup. This may take a while.")
        status_label.set_halign(Gtk.Align.START)

        progress_bar = Gtk.ProgressBar(show_text=True)
        progress_bar.set_fraction(0.0)

        # Terminal-like Details section
        details_expander = Gtk.Expander(label="Details")
        log_view = Gtk.TextView(editable=False, cursor_visible=False, monospace=True)
        log_buffer = log_view.get_buffer()
        log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        details_scrolled = Gtk.ScrolledWindow()
        details_scrolled.set_child(log_view)
        details_scrolled.set_vexpand(True)
        details_expander.set_child(details_scrolled)

        # Pack widgets
        main_box.append(header_bar)
        # main_box.append(title_label)
        main_box.append(status_label)
        main_box.append(progress_bar)
        main_box.append(details_expander)

        # Simulate Real-Time Logs
        def update_progress():
            current_fraction = progress_bar.get_fraction()
            if current_fraction < 1.0:
                progress_bar.set_fraction(current_fraction + 0.05)
                end_iter = log_buffer.get_end_iter()
                log_buffer.insert(
                    end_iter,
                    f"Scanning: /home/macbook/file-{int(current_fraction*20)}.txt\n"
                )

                # Simulate an error at 50%
                if current_fraction >= 0.5 and current_fraction < 0.55:
                    log_buffer.insert(end_iter, "ERROR: File corrupted /home/macbook/file-10.txt\n")

                return GLib.SOURCE_CONTINUE
            else:
                status_label.set_label("Backup Complete!")
                log_buffer.insert(log_buffer.get_end_iter(), "Backup finished successfully.\n")
                return GLib.SOURCE_REMOVE

        GLib.timeout_add(500, update_progress)

        progress_dialog.present()
    

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


    ##########################################################################
    # DEVICE LOCATION
    ##########################################################################
    def available_devices_location(self, button=None):
        """Dynamically update the dropdown with available backup devices."""
        location = device_location()  # Get backup device location, e.g., /media or /run

        if location:
            try:
                # Clear previous device items from the ListStore
                self.backup_device_model.remove_all()

                # Iterate over the external devices and add them to the ListStore
                for backup_device in os.listdir(f'{location}/{SERVER().USERNAME}'):
                    # Add the backup device to the dropdown model
                    self.backup_device_model.append(Gtk.StringObject.new(backup_device))
            except FileNotFoundError:
                print(f"Path {location}/{SERVER().USERNAME} does not exist or cannot be accessed.")

        return True  # Keep the timeout running
    

    ##########################################################################
    # AUTOMATICALLY CHECKBOX
    ##########################################################################
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
                self.create_autostart_entry()  # Create .desktop file for auto startup
                server.write_backup_status(status='Monitoring')  # Update backup status

                # Update the conf file
                server.set_database_value(
                    section='BACKUP',
                    option='automatically_backup',
                    value='true'
                )

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

    def create_autostart_entry(self):
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

    def remove_autostart_entry(self):
        if os.path.exists(server.autostart_file):
            os.remove(server.autostart_file)
            logging.info("Autostart entry removed.")

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
    

    ##########################################################################
    # EXCLUDE
    ##########################################################################
    def display_excluded_folders(self):
        """Display loaded excluded folders."""
        for folder in self.ignored_folders:
            logging.info("Adding folder: %s", folder)
            self.add_folder_to_list(folder)

    def auto_select_hidden_itens(self):
        exclude_hidden_itens: bool = server.get_database_value(
            section='EXCLUDE',
            option='exclude_hidden_itens')

        if exclude_hidden_itens:
            self.exclude_hidden_files.set_active(True)
        else:
            self.exclude_hidden_files.set_active(False)

    def on_ignore_hidden_switch_toggled(self, switch, gparam):
        true_false: str = 'false'

        # Handle the toggle state of the ignore hidden switch
        if switch.get_active():
            true_false = 'true'

        # Update the conf file
        server.set_database_value(
            section='EXCLUDE',
            option='exclude_hidden_itens',
            value=true_false)
        
    def add_folder_to_list(self, folder):
        ignore_row = self.create_folder_row(folder)
        self.ignore_group.add(ignore_row)

    def load_folders_from_config(self):
        """Loads folders from the config file."""
        config = configparser.ConfigParser()

        if os.path.exists(server.CONF_LOCATION):  # Ensure the config file exists
            config.read(server.CONF_LOCATION)
            if 'EXCLUDE_FOLDER' in config:  # Check if the section exists
                self.ignored_folders = config.get('EXCLUDE_FOLDER', 'folders').split(',')
                # Remove empty strings in case of trailing commas
                self.ignored_folders = [folder.strip() for folder in self.ignored_folders if folder.strip()]
    

    ##########################################################################
    # BACKUP DEVICE
    ##########################################################################
    def auto_select_backup_device(self):
        # Get stored driver_location and driver_name
        driver_location = server.get_database_value(
            section='DRIVER',
            option='driver_location')

        driver_name = server.get_database_value(
            section='DRIVER',
            option='driver_name')

        # Check if both values are available
        if driver_name and driver_location:
            # Get the model of the DropDown widget
            model = self.location_dropdown.get_model()  

            # Iterate over the items in the model to find the index of the device
            for i, item in enumerate(model):
                if item.get_string() == driver_name:  # Use get_string() to get the device name
                    self.location_dropdown.set_selected(i)  # Select the item by index
                    break

    # TEST
    # def auto_select_backup_device(self):
    #     """Populate the dropdown with available backup devices without auto-selecting."""
    #     # Get stored driver_name (if any)
    #     driver_name = server.get_database_value(
    #         section='DRIVER',
    #         option='driver_name'
    #     )

    #     # Get the model of the DropDown widget
    #     model = self.location_dropdown.get_model()

    #     # Iterate over the items in the model to find the stored device
    #     for i, item in enumerate(model):
    #         if item.get_string() == driver_name:  # Use get_string() to get the device name
    #             self.location_dropdown.set_selected(i)  # Select the stored device by index
    #             break
    

    ##########################################################################
    # SEARCH ENTRY
    ##########################################################################
    def scan_files_folder_threaded(self):
        """Scan files in a background thread."""
        def scan():
            self.files = self.scan_files_folder()
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
            self.search_timer = Timer(0.5, lambda: threading.Thread(target=self.perform_search, args=(query,), daemon=True).start())
            self.search_timer.start()
        else:
            self.populate_results([])
            
    def perform_search(self, query):
        """Perform the search and update the results."""
        try:
            # Simulate fetching search results (replace this with actual logic)
            results = self.search_backup_sources(query)
        except Exception as e:
            print(f"Error during search: {e}")
            results = []

        # Update the UI on the main thread
        GLib.idle_add(self.populate_results, results)

    # def search_backup_sources(self, query):
    #     return [f for f in self.files if query in f["name"].lower()]

    def search_backup_sources(self, query):
        query = query.lower()  # Ensure case-insensitive search

        # Files where name starts with the query
        starts_with = [f for f in self.files if f["name"].lower().startswith(query)]

        # Files where name contains the query but doesn't start with it
        contains = [f for f in self.files if query in f["name"].lower() and not f["name"].lower().startswith(query)]

        # Combine both lists: prioritize files that start with the query
        return starts_with + contains
    
    def populate_results(self, results):
        """Populate the results grid with search results, limiting the number of results."""
        # Clear existing results from the grid
        child = self.results_grid.get_first_child()
        while child:
            next_child = child.get_next_sibling()  # Save reference to the next sibling
            self.results_grid.remove(child)       # Remove the current child
            child = next_child                    # Move to the next child

        # Sort the results by date (latest first)
        # sorted_results = sorted(results, key=lambda x: x["date"], reverse=True)

        # Limit the number of results
        limited_results = results[:self.page_size]

        # Add each result as a thumbnail in the FlowBox
        for result in limited_results:
            self.add_thumbnail_to_results(result)

    def add_thumbnail_to_results(self, source):
        import datetime

        """Add a thumbnail for a source to the results grid."""
        thumbnail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        # Add an icon or thumbnail image
        file_thumbnail = self.create_thumbnail(source["path"])
        thumbnail_icon = Gtk.Image()
        if file_thumbnail:
            thumbnail_icon.set_from_pixbuf(file_thumbnail)
            thumbnail_icon.set_size_request(128, 128)  # Force the Gtk.Image widget size
        else:
            # Add an icon or placeholder image
            thumbnail_icon = Gtk.Image(icon_name="folder-symbolic", pixel_size=48)
            
        thumbnail_box.append(thumbnail_icon)

        # Add a label with the source name
        source_label = Gtk.Label(label=source["name"], halign=Gtk.Align.CENTER, wrap=True)
        thumbnail_box.append(source_label)

        # Convert the timestamp to a human-readable format
        timestamp = source["date"]
        human_readable_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        # Add the human-readable date label
        source_date = Gtk.Label(label=human_readable_date, halign=Gtk.Align.CENTER, wrap=True)
        thumbnail_box.append(source_date)
        
        # Add a restore button
        search_button = Gtk.Button(label="Search", halign=Gtk.Align.CENTER)
        search_button.connect("clicked", lambda b, source=source: self.show_all_file_search(source["name"]))
        thumbnail_box.append(search_button)

        # Add the thumbnail to the results grid
        self.results_grid.append(thumbnail_box)

    def create_thumbnail(self, file_path):
        """Create a thumbnail for the given file if it's an image."""
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file_path, 64, 64) 
            return pixbuf
        except Exception as e:
            pass
        return None

    def paginate_results(self, results):
        """Paginate search results."""
        start = self.current_page * self.page_size
        end = start + self.page_size
        return results[start:end]

    def on_next_page_clicked(self, button):
        """Show the next page of results."""
        self.current_page += 1
        self.populate_results(self.paginate_results(self.search_results))

    def on_previous_page_clicked(self, button):
        """Show the previous page of results."""
        if self.current_page > 0:
            self.current_page -= 1
            self.populate_results(self.paginate_results(self.search_results))
    
    def create_filter_widgets(self):
        """Creates the filter widgets (file type and date)."""
        # File Type ComboBox
        file_type_combo = Gtk.ComboBoxText()
        file_type_combo.append_text("All Files")
        file_type_combo.append_text("Images")
        file_type_combo.append_text("Documents")
        file_type_combo.append_text("Videos")
        file_type_combo.set_active(0)  # Set default to "All Files"
        file_type_combo.connect("changed", self.on_filter_changed)

        # Date Filter ComboBox
        date_combo = Gtk.ComboBoxText()
        date_combo.append_text("Any Time")
        date_combo.append_text("Last 7 Days")
        date_combo.append_text("Last Month")
        date_combo.append_text("Last Year")
        date_combo.set_active(0)  # Set default to "Any Time"
        date_combo.connect("changed", self.on_date_filter_changed)

        # Layout (add widgets to a box, for example)
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        filter_box.append(file_type_combo)
        filter_box.append(date_combo)
        
        self.main_box.append(filter_box)  # Or any container you're using for layout

    def on_filter_changed(self, combo):
        """Filter results based on the selected file type."""
        file_type = combo.get_active_text()
        filtered_files = self.filter_by_file_type(file_type)
        
        # Also apply the date filter
        filtered_files = self.apply_date_filter(filtered_files)
        
        # Update the results
        GLib.idle_add(self.populate_results, filtered_files)

    def filter_by_file_type(self, file_type):
        """Filter files based on file type."""
        if file_type == "All Files":
            return self.files
        elif file_type == "Images":
            return [f for f in self.files if f["name"].endswith((".png", ".jpg", ".jpeg", ".gif"))]
        elif file_type == "Documents":
            return [f for f in self.files if f["name"].endswith((".pdf", ".docx", ".txt"))]
        elif file_type == "Videos":
            return [f for f in self.files if f["name"].endswith((".mp4", ".avi"))]
        return self.files

    def apply_date_filter(self, files):
        """Apply the selected date filter."""
        # Get the selected date filter
        date_filter = self.date_combo.get_active_text()
        
        if date_filter == "Any Time":
            return files  # No date filter, return all files
        
        # Get the current date
        now = datetime.datetime.now()
        
        if date_filter == "Last 7 Days":
            cutoff_date = now - datetime.timedelta(days=7)
        elif date_filter == "Last Month":
            cutoff_date = now - datetime.timedelta(days=30)
        elif date_filter == "Last Year":
            cutoff_date = now - datetime.timedelta(days=365)
        else:
            return files  # No valid filter
        
        # Filter files based on the modification date
        filtered_files = [f for f in files if datetime.datetime.fromtimestamp(f["date"]) >= cutoff_date]
        
        return filtered_files

    def on_date_filter_changed(self, combo):
        """Handle changes to the date filter."""
        self.on_filter_changed(combo)  # Reapply the file type and date filters
    
    def show_restore_success(self, file_name):
        """Show a success message after the restore action."""
        success_message = f"File {file_name} has been restored successfully!"
        
        # Create a Gtk.Label to display the message
        message_label = Gtk.Label(label=success_message, halign=Gtk.Align.CENTER)
        message_label.set_margin_top(10)
        
        # Optionally, set a timer to remove the label after a few seconds
        GLib.timeout_add_seconds(3, lambda: self.remove_restore_message(message_label))
        
        # Add the label to the UI (e.g., status bar, header, etc.)
        self.results_grid.append(message_label)
        # self.results_grid.show_all()  # Update the display to show the label

    def remove_restore_message(self, message_label):
        """Remove the success message after a few seconds."""
        self.results_grid.remove(message_label)
        # self.results_grid.show_all()  # Update the display after removal
# def show_all_file_search(self, name):
#     """Display item all previous backup dialog."""
#     restore_dialog = Adw.Window(
#         transient_for=self,
#         title="Restore File",
#         modal=True,
#         default_width=600,
#         default_height=400,
#     )

#     # Header bar with buttons
#     header_bar = Gtk.HeaderBar()

#     # Fetch results
#     results = self.get_files_in_directory(name)

#     # Sort results based on extracted date and time from the path
#     def extract_datetime_from_path(path):
#         """Extracts and converts date and time from the file path."""
#         try:
#             # Assume the path format contains '/<date>/<time>/' near the start
#             date_time = path.replace(server.backup_folder_name() + '/', '').split('/')[:2]
#             file_date = date_time[0]  # e.g., '11-12-2024'
#             file_time = date_time[1]  # e.g., '18-17'
            
#             # Convert date and time into a single datetime object
#             return datetime.datetime.strptime(f"{file_date} {file_time}", "%d-%m-%Y %H-%M")
#         except (IndexError, ValueError) as e:
#             # Handle malformed paths or missing date/time
#             print(f"Error extracting datetime from path {path}: {e}")
#             return datetime.datetime.min  # Return an extremely old date for sorting fallback

#     # Sort using the extracted datetime
#     sorted_results = sorted(results, key=lambda x: extract_datetime_from_path(x["path"]), reverse=True)

#     # Limit the number of results
#     limited_results = sorted_results[:self.page_size]

#     # Scrollable area to display search results
#     scrolled_results = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
#     scrolled_results.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

#     # FlowBox for displaying restore results (e.g., files or folders)
#     results_grid = Gtk.FlowBox(
#         max_children_per_line=5,
#         selection_mode=Gtk.SelectionMode.NONE,
#         homogeneous=True,
#         valign=Gtk.Align.START,
#     )
#     results_grid.set_margin_top(10)
#     results_grid.set_margin_bottom(10)
#     results_grid.set_margin_start(10)
#     results_grid.set_margin_end(10)
#     results_grid.set_row_spacing(10)
#     results_grid.set_column_spacing(10)

#     scrolled_results.set_child(results_grid)

#     for result in limited_results:
#         """Add a thumbnail for a source to the results grid."""
#         thumbnail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

#         # Add an icon or placeholder image
#         thumbnail_icon = Gtk.Image(icon_name="folder-symbolic", pixel_size=48)
#         thumbnail_box.append(thumbnail_icon)

#         # Add a label with the source name
#         source_label = Gtk.Label(label=result['name'], halign=Gtk.Align.CENTER, wrap=True)
#         thumbnail_box.append(source_label)

#         # Extract and format the date and time
#         dateframe = str(result['path']).replace(server.backup_folder_name() + '/', '')
#         try:
#             # Extract folder date and time
#             date = dateframe.split('/')[0]  # e.g., '11-12-2024'
#             time = dateframe.split('/')[1]  # e.g., '18-17'
#             human_readable_date = f"{date} {time}"  # Combine for display
#         except (IndexError, ValueError) as e:
#             # Handle malformed paths or missing data
#             human_readable_date = "Invalid Timestamp"
#             print(f"Error extracting date/time from path {result['path']}: {e}")

#         # Add the human-readable date label
#         source_date = Gtk.Label(label=human_readable_date, halign=Gtk.Align.CENTER, wrap=True)
#         thumbnail_box.append(source_date)

#         # Add a restore button
#         open_button = Gtk.Button(label="Open Location", halign=Gtk.Align.CENTER)
#         open_button.connect("clicked", lambda b, path=result["path"]: threading.Thread(target=self.open_file_location, args=(path, restore_dialog,), daemon=True).start())

#         restore_button = Gtk.Button(label="Restore", halign=Gtk.Align.CENTER)
#         restore_button.connect("clicked", lambda b, path=result["path"]: threading.Thread(target=self.on_restore_source_clicked, args=(path, restore_dialog,), daemon=True).start())

#         thumbnail_box.append(open_button)
#         thumbnail_box.append(restore_button)

#         # Add the thumbnail to the results grid
#         results_grid.append(thumbnail_box)

#     # Main content
#     main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10)
#     main_box.set_halign(Gtk.Align.FILL)
#     restore_dialog.set_content(main_box)

#     # Create status label and progress bar
#     self.restore_status_label = Gtk.Label()
#     self.restore_status_label.set_halign(Gtk.Align.CENTER)
#     self.restore_status_label.set_valign(Gtk.Align.CENTER)

#     self.restore_progress_bar = Gtk.ProgressBar(show_text=True)
#     self.restore_progress_bar.set_fraction(0.0)
#     self.restore_progress_bar.hide()

#     # Create a Scrolled Window for the logs
#     logs_scrolled = Gtk.ScrolledWindow()
#     logs_scrolled.set_child(scrolled_results)
#     logs_scrolled.set_vexpand(True)

#     # Pack widgets into the main box
#     main_box.append(header_bar)
#     main_box.append(self.restore_status_label)
#     main_box.append(self.restore_progress_bar)
#     main_box.append(logs_scrolled)

#     # Show the dialog
#     restore_dialog.present()

    #########################################################################
    # SEARCH ALL 
    ##########################################################################
    def show_all_file_search(self, name):
        """Display item all previous backup dialog."""
        restore_dialog = Adw.Window(
            transient_for=self,
            title="Restore File",
            modal=True,
            default_width=600,
            default_height=400,
        )

        # Header bar with buttons
        header_bar = Gtk.HeaderBar()

        results = self.get_files_in_directory(name)
        # Sort results based on extracted date and time from the path
        sorted_results = sorted(results, key=lambda x: x["date"], reverse=True)

        # Limit the number of results
        limited_results = sorted_results[:self.page_size]

        # Extrac date and timeframe
        
        # Scrollable area to display search results
        scrolled_results = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        scrolled_results.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # FlowBox for displaying restore results (e.g., files or folders)
        results_grid = Gtk.FlowBox(
            max_children_per_line=5,
            selection_mode=Gtk.SelectionMode.NONE,
            homogeneous=True,
            valign=Gtk.Align.START,
        )
        # results_grid.set_margin_top(10)
        # results_grid.set_margin_bottom(10)
        # results_grid.set_margin_start(10)
        # results_grid.set_margin_end(10)
        # results_grid.set_row_spacing(10)
        # results_grid.set_column_spacing(10)

        scrolled_results.set_child(results_grid)

        for result in limited_results:
            import datetime

            """Add a thumbnail for a source to the results grid."""
            thumbnail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

            # Add an icon or placeholder image
            thumbnail_icon = Gtk.Image(icon_name="folder-symbolic", pixel_size=48)
            thumbnail_box.append(thumbnail_icon)

            # Add a label with the source name
            source_label = Gtk.Label(label=result['name'], halign=Gtk.Align.CENTER, wrap=True)
            thumbnail_box.append(source_label)

            # Convert the timestamp to a human-readable format
            timestamp = result['date']
            dateframe = str(result['path']).replace(server.backup_folder_name() + '/', '')

            #human_readable_date = datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M:%S')
            
            try:
                # Handle both integer and fractional timestamps
                # human_readable_date = datetime.datetime.fromtimestamp(float(timestamp)).strftime('%d-%m-%Y %H:%M:%S')
                date = dateframe.split('/')[:1][0]
                time = dateframe.split('/')[1:][0]
                human_readable_date = date + ' ' + time
            except ValueError as e:
                # Handle cases where the timestamp is invalid
                # human_readable_date = "Invalid Timestamp"
                date = dateframe.split('/')[:1][0]
                time = dateframe.split('/')[1:][0]
                human_readable_date = "Invalid Timestamp"
                print(f"Error converting timestamp {timestamp}: {e}")

            # Add the human-readable date label
            source_date = Gtk.Label(label=human_readable_date, halign=Gtk.Align.CENTER, wrap=True)
            thumbnail_box.append(source_date)

            # Add a restore button
            open_button = Gtk.Button(label="Open Location", halign=Gtk.Align.CENTER)
            open_button.connect("clicked", lambda b, path=result["path"]: threading.Thread(target=self.open_file_location, args=(path, restore_dialog,), daemon=True).start())

            restore_button = Gtk.Button(label="Restore", halign=Gtk.Align.CENTER)
            # Ensure the correct path is passed to the restore function
            # restore_button.connect("clicked", lambda b, path=result["path"]: self.on_restore_source_clicked(path, restore_dialog))
            restore_button.connect("clicked", lambda b, path=result["path"]: threading.Thread(target=self.on_restore_source_clicked, args=(path, restore_dialog,), daemon=True).start())
            
            # self.search_timer = Timer(0.5, lambda: threading.Thread(target=self.perform_search, args=(query,), daemon=True).start())

            thumbnail_box.append(open_button)
            thumbnail_box.append(restore_button)

            # Add the thumbnail to the results grid
            results_grid.append(thumbnail_box)

        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10)
        main_box.set_halign(Gtk.Align.FILL)
        restore_dialog.set_content(main_box)

        # Create status label and progress bar
        self.restore_status_label = Gtk.Label()
        self.restore_status_label.set_halign(Gtk.Align.CENTER)
        self.restore_status_label.set_valign(Gtk.Align.CENTER)  # Center vertically

        self.restore_progress_bar = Gtk.ProgressBar(show_text=True)
        self.restore_progress_bar.set_fraction(0.0)
        self.restore_progress_bar.hide()
        
        # Create a Scrolled Window for the logs
        logs_scrolled = Gtk.ScrolledWindow()
        logs_scrolled.set_child(scrolled_results)
        logs_scrolled.set_vexpand(True)

        # # Pack widgets into the main box
        main_box.append(header_bar)
        main_box.append(self.restore_status_label)
        main_box.append(self.restore_progress_bar)
        main_box.append(logs_scrolled)

        # Show the dialog
        restore_dialog.present()
    
    def get_files_in_directory(self, name):
        """Return a list of files in the given directory."""
        file_list = []
        for root, dirs, files in os.walk(server.backup_folder_name()):
            for file_name in files:
                if name in file_name:
                    file_path = os.path.join(root, file_name)
                    file_date = os.path.getmtime(file_path)
                    file_list.append({
                        "name": file_name,
                        "path": file_path,
                        "date": file_date
                    })
        return file_list
    
    def open_file_location(self, source, logs_dialog):
        file_location: str = '/'.join(str(source).split('/')[:-1])
        print(file_location)
        process = sub.run(
            ['xdg-open', file_location],
                stdout=sub.PIPE,
                stderr=sub.PIPE,
                text=True)

    
    def on_restore_source_clicked(self, source, logs_dialog):
        """Handle the restore action for the clicked file."""
        try:
            # Update the UI to indicate the restore process has started
            self.restore_status_label.set_label("Restoring file...")
            self.restore_progress_bar.show()

            # Determine the destination path by removing the backup folder prefix
            # and reconstructing the path relative to the user's home directory
            destination = str(source).replace(server.backup_folder_name(), '')
            destination = '/'.join((destination.split('/')[3:]))  # Remove date and timeframe
            destination = os.path.join(server.USER_HOME, destination)  # Join user home with modded path

            # Debugging: Print the source and destination paths
            print('Restoring:', source)
            print('To:', destination)

            # Ensure the restore directory exists
            # Uncomment the following line to create the directory if it doesn't exist
            # os.makedirs(destination, exist_ok=True)

            # Perform the restore by copying the file to the destination
            try:
                shutil.copy2(source, destination)
            except FileNotFoundError:
                # Log an error if the source file is not found
                logging.error(f"Source file not found: {source}")
            except PermissionError:
                # Log an error if there are permission issues during the copy
                logging.error(f"Permission denied while copying to: {destination}")

            # Debugging: Print a success message
            print(f"Restored {source} to {destination}")
            
            # Update the UI to indicate the restore process is complete
            self.restore_status_label.set_label("Backup Complete!")
            self.restore_progress_bar.hide()

            # Once done, close the dialog
            GLib.idle_add(logs_dialog.close)

            # Optionally, you can update the UI or show a success message
            # GLib.idle_add(self.update_progress, source)
            # GLib.timeout_add(500, self.update_progress)
        except Exception as e:
            # Log any unexpected errors during the restore process
            print(f"Error restoring file: {e}")

    def update_progress(self, source):
        """Update the progress bar during the restore process."""
        current_fraction = self.restore_progress_bar.get_fraction()
        if current_fraction < 1.0:
            # Increment the progress bar fraction
            self.restore_progress_bar.set_fraction(current_fraction + 0.05)
            return GLib.SOURCE_CONTINUE
        else:
            # Once the progress is complete, update the status label
            self.restore_status_label.set_label("Backup Complete!")
            return GLib.SOURCE_REMOVE


if __name__ == '__main__':
	app = Adw.Application()
	win = BackupSettingsWindow(application=app)
	app.run()
