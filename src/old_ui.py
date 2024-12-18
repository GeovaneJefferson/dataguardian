import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib
from server import *
from device_location import device_location

server = SERVER()

# BUG
# In auto select backup, is auto selecting the first users backup device.

# class MainWindow(Gtk.ApplicationWindow):
# 	def __init__(self, *args, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		self.box1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
# 		self.set_child(self.box1)

# 		self.header = Gtk.HeaderBar()
# 		self.set_titlebar(self.header)

# 		self.open_button = Gtk.Button(label="Open")
# 		self.header.pack_start(self.open_button)

# 		self.open_button.set_icon_name("document-open-symbolic")

# 		# Create a new "Action"
# 		action = Gio.SimpleAction.new("something", None)
# 		# action.connect("activate", self.print_something)
# 		self.add_action(action)  # Here the action is being added to the window, but you could add it to the
# 									# application or an "ActionGroup"

# 		# Create a new menu, containing that action
# 		menu = Gio.Menu.new()
# 		menu.append("Do Something", "win.something")  # Or you would do app.something if you had attached the
# 														# action to the application

# 		# Create a popover
# 		self.popover = Gtk.PopoverMenu()  # Create a new popover menu
# 		self.popover.set_menu_model(menu)

# 		# Create a menu button
# 		self.hamburger = Gtk.MenuButton()
# 		self.hamburger.set_popover(self.popover)
# 		self.hamburger.set_icon_name("open-menu-symbolic")  # Give it a nice icon

# 		# Add menu button to the header bar
# 		self.header.pack_start(self.hamburger)


class UIWindow(Adw.PreferencesWindow):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.programmatic_change = False  
		self.switch_cooldown_active = False  # To track the cooldown state

		##########################################################################
		# WINDOW
		##########################################################################
		# Create a Preferences Window with tabs
		self.set_title("Settings")
		#self.set_size_request(600, 400)
		self.set_resizable(True)  # Prevent window from being resized

		# Variables
		self.ignored_folders = []

		self.setup_preferences_pages()

		# Load available devices
		self.available_devices_location()

		# Auto-select the backup device based on saved configuration
		self.auto_select_backup_device()

		# Auto-select 'Backup Automatically'
		self.auto_select_auto_backup()
		
		# Auto-select 'Hidden files'
		self.auto_select_hidden_itens()
	
	def setup_preferences_pages(self):
		##########################################################################
		# PAGES - General
		##########################################################################
		# General Tab
		general_page = Adw.PreferencesPage()
		general_page.set_icon_name("settings-symbolic")
		general_group = Adw.PreferencesGroup(
			title="Storage")

		# Location (ComboBox for backup location)
		self.location_row = Adw.ComboRow(
			title="Location:", 
			selected=0)
		
		self.location_row.set_model(Gtk.StringList.new([f"Local Storage"]))
		
		# # Only enable switch if user has registered a backup device
		# driver_name = server.get_database_value(
		# 	section='DRIVER',
		# 	option='driver_name')
		 
		# if driver_name != '':
		# 	self.location_row.set_model(Gtk.StringList.new([driver_name]))
		
		self.location_row.connect("notify::selected", self.on_location_changed)

		# Folder button
		folder_button = Gtk.Button.new_from_icon_name("folder-open-symbolic")
		folder_button.set_tooltip_text("Select folder")
		folder_button.connect("clicked", self.on_folder_button_clicked)

		# Create box to hold folder button
		folder_box = Gtk.Box(
			orientation=Gtk.Orientation.HORIZONTAL, 
			spacing=10)
		# folder_box.append(folder_button)
		folder_box.set_sensitive(False)
		self.location_row.add_suffix(folder_box)

		# Backup Device (Expandable Row)
		self.backup_device_row = Adw.ExpanderRow(
			title="Choose a backup device:")
		self.backup_device_list = Gtk.ComboBoxText()
		self.backup_device_list.set_id_column(0)
		self.backup_device_list.connect("changed", self.on_backup_device_selected)  # Connect the signal
		self.backup_device_row.add_row(self.backup_device_list)
		# self.backup_device_row.add_suffix(refresh_button)

		general_group.add(self.location_row)
		general_group.add(self.backup_device_row)
		general_page.add(general_group)

		##########################################################################
		# PAGES - GENERAL - SCHEDULE
		##########################################################################
		# Schedule section
		schedule_group = Adw.PreferencesGroup(
			title="Real-time protection")

		# Backup Automation Switch
		self.switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

		# Create a label for the switch with your specified text
		label = Gtk.Label(
			label="   Back up new and updated files from your home.")

		# Create the switch
		self.auto_backup_switch = Gtk.Switch()

		# Only enable switch if user has registered a backup device
		driver_name = server.get_database_value(
			section='DRIVER',
			option='driver_name')
		 
		if driver_name != '':
			# Enable switch
			self.auto_backup_switch.set_sensitive(True)
		else:
			# Disable switch
			self.auto_backup_switch.set_sensitive(False)

		self.auto_backup_switch.set_tooltip_text('You will have to wait a few seconds before changing the checkbox state.')
		self.auto_backup_switch.connect("notify::active", self.on_auto_backup_switch_toggled)

		# Add the label to the switch box
		self.switch_box.append(self.auto_backup_switch)
		self.switch_box.append(label)

		######################################################################
		# Add groups
		schedule_group.add(self.switch_box)
		# Schedule groups
		general_page.add(schedule_group)
		# Adding General page to PreferencesWindow
		self.add(general_page)

		##########################################################################
		# PAGES - FOLDERS - FOLDER TO IGNORE
		##########################################################################
		# Folders Tab
		folders_page = Adw.PreferencesPage()
		folders_page.set_icon_name("folder-open-symbolic")
		self.add(folders_page)

		# Create the groups
		ignore_group = Adw.PreferencesGroup(title="Folders to ignore")
		exclude_group = Adw.PreferencesGroup(title="Exclude")

		# Add folder selector to ignore
		folder_select_button = Gtk.Button(label="Add Folder")
		folder_select_button.connect("clicked", self.on_folder_select_button_clicked)
		ignore_group.add(folder_select_button)

		# Create a ScrolledWindow to hold the ListBox
		scrolled_window = Gtk.ScrolledWindow()
		scrolled_window.set_size_request(-1, 300)  # Width is not limited (-1 means no minimum width)
		ignore_group.add(scrolled_window)

		# Create ListBox to display ignored folders
		self.listbox = Gtk.ListBox()
		scrolled_window.set_child(self.listbox)  # Add ListBox to ScrolledWindow

		# Backup Automation Switch
		hidden_switch_box = Gtk.Box(
			orientation=Gtk.Orientation.HORIZONTAL)

		# Create a label for the switch
		label = Gtk.Label(label="   Ignore hidden files.")

		# Create the switch
		self.ignore_hidden_switch = Gtk.Switch()
		self.ignore_hidden_switch.set_active(True)
		# self.ignore_hidden_switch.set_sensitive(False)
		self.ignore_hidden_switch.connect("notify::active", self.on_ignore_hidden_switch_toggled)

		# Add the label to the switch box
		hidden_switch_box.append(self.ignore_hidden_switch)
		hidden_switch_box.append(label)

		# Add the switch box to the exclude group
		exclude_group.add(hidden_switch_box)

		# Add groups to folders_page
		folders_page.add(exclude_group)
		folders_page.add(ignore_group)

		##########################################################################
		# RESTORE FILES
		##########################################################################
		# Folders Tab
		restore_files_page = Adw.PreferencesPage()
		restore_files_page.set_icon_name("folder-download-symbolic")
		self.add(restore_files_page)

		# Create the groups
		latest_backup_group = Adw.PreferencesGroup(
			title="Latest backup files")  # Show latest 5 backup files
		#latest_backup_group = Adw.PreferencesGroup(title="Restore backup files")
		
		# --- Search and Filters Box ---
		search_and_filter_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

		# Search Bar
		search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
		search_box.set_halign(Gtk.Align.CENTER)  # Center search box horizontally

		search_entry = Gtk.SearchEntry()
		search_entry.set_tooltip_text("Type to search")
		search_box.append(search_entry)
		search_and_filter_box.append(search_box)

		# Filters
		filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
		filter_box.set_halign(Gtk.Align.CENTER)  # Center filter box horizontally

		file_type_filter = Gtk.ComboBoxText()
		file_type_filter.append_text("All Files")
		file_type_filter.append_text("Images")
		file_type_filter.append_text("Documents")
		file_type_filter.append_text("Videos")
		file_type_filter.set_active(0)
		filter_box.append(file_type_filter)

		sort_filter = Gtk.ComboBoxText()
		sort_filter.append_text("Sort by Name")
		sort_filter.append_text("Sort by Date")
		sort_filter.set_active(0)
		filter_box.append(sort_filter)
		search_and_filter_box.append(filter_box)

		# --- Results Display ---
		self.results_list = Gtk.ListBox()
		self.results_list.set_vexpand(True)  # Make the listbox expand vertically

		# Create a ScrolledWindow to hold the ListBox
		scrolled_window = Gtk.ScrolledWindow()
		scrolled_window.set_size_request(-1, 300)  # Width is not limited (-1 means no minimum width)
		scrolled_window.set_child(self.results_list)

		# Add the scrolled window to the search_and_filter_box
		search_and_filter_box.append(scrolled_window)

		# Add the search and filters container to the preferences group
		latest_backup_group.add(search_and_filter_box)

		# Pages
		restore_files_page.add(latest_backup_group)

		# Set initial files list by scanning files
		self.documents_path = os.path.expanduser(server.main_backup_folder())
		self.files = self.scan_files_folder()
		#self.files = []

		#########################################################
		# Callback function to update the UI after filtering/sorting
		#self.search_handler = FileSearchHandler(self.documents_path, self.update_search_results)

		# Connect search, file type filter, and sort filter to their respective methods
		search_entry.connect("search-changed", self.on_search_changed)
		file_type_filter.connect("changed", self.on_filter_changed)
		sort_filter.connect("changed", self.on_sort_changed)

		# Set titles for tabs
		general_page.set_title("General")
		folders_page.set_title("Folders")
		restore_files_page.set_title("Restore Files")

		# Load folders from config
		self.load_folders_from_config()

		# Display loaded excluded folders
		for folder in self.ignored_folders:
			self.add_folder_to_list(folder)

	##########################################################################
	# TEST
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
		"""Handle search text change."""
		query = entry.get_text().lower()
		if query:
			# Run the search in a separate thread to avoid UI freeze
			threading.Thread(target=self.perform_search, args=(query,)).start()
		else:
			self.populate_results([])
   
	def perform_search(self, query):
		"""Perform search in a background thread."""
		filtered_files = [f for f in self.files if query in f["name"].lower()]
		self.populate_results(filtered_files)

	def update_search_results(self, filtered_files):
		"""Callback function to update the UI after filtering/sorting files."""
		# This method will be called by the FileSearchHandler to update the UI with results
		#self.populate_results(filtered_files)
		GLib.idle_add(self.populate_results, filtered_files)

	def populate_results(self, files):
		"""Populate the results list with files."""
		# Clear previous items
		child = self.results_list.get_first_child()
		while child:
			next_child = child.get_next_sibling()  # Save reference to the next sibling
			self.results_list.remove(child)       # Remove the current child
			child = next_child                    # Move to the next child

		# Add new items
		count = 0
		for file in files:
			row = Gtk.ListBoxRow()
			# row = Gtk.Button()

			# Create a box for horizontal layout
			hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
			hbox.set_homogeneous(False)

			# # Create a thumbnail for supported files (enlarge the thumbnail size)
			# thumbnail = self.create_thumbnail(file["path"])
			# if thumbnail:
			# 	image = Gtk.Image.new_from_pixbuf(thumbnail)
			# 	# Resize the image to a more reasonable size
			# 	image.set_pixel_size(100)  # Increase this value for a larger thumbnail
			# 	hbox.append(image)

			# File name label
			file_label = Gtk.Label(label=file["name"], xalign=0)
			hbox.append(file_label)

			# File date label
			date_label = Gtk.Label(label=self.format_date(file["date"]))
			hbox.append(date_label)

			# File size label (if the file has a size field)
			if "size" in file:
				size_label = Gtk.Label(label=f"{file['size']} KB")  # Adjust format as needed
				hbox.append(size_label)

			# Set the content of the row to the hbox
			row.set_child(hbox)

			# # Make the row clickable by connecting a signal to open the file with xdg-open
			# def on_row_click(file_path=file["path"]):
			# 	sub.run(["xdg-open", file_path])

			# row.connect("clicked", on_row_click)

			# Append the row to the list
			self.results_list.append(row)

			count += 1
			if count == 10:
				break

	# def populate_results(self, files):
	# 	"""Populate the results list with files."""
	# 	# Clear previous items
	# 	child = self.results_list.get_first_child()
	# 	while child is not None:
	# 		next_child = child.get_next_sibling()  # Save reference to the next sibling
	# 		self.results_list.remove(child)       # Remove the current child
	# 		child = next_child                    # Move to the next child
		
	# 	# Add new items
	# 	count:int = 0
	# 	for file in files:
	# 		row = Gtk.ListBoxRow()
	# 		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

	# 		# Create a thumbnail for supported files
	# 		thumbnail = self.create_thumbnail(file["path"])
	# 		if thumbnail:
	# 			image = Gtk.Image.new_from_pixbuf(thumbnail)
	# 			hbox.append(image)

	# 		# File name label
	# 		file_label = Gtk.Label(label=file["name"], xalign=0)
	# 		hbox.append(file_label)

	# 		# File date label
	# 		date_label = Gtk.Label(label=self.format_date(file["date"]))
	# 		hbox.append(date_label)

	# 		row.set_child(hbox)
	# 		self.results_list.append(row)

	# 		count += 1
	# 		if count == 10:
	# 			break
   
	def open_file(self, widget, path):
		"""Open the file with xdg-open."""
		try:
			sub.run(["xdg-open", path], check=True)
		except sub.CalledProcessError as e:
			print(f"Error opening file {path}: {e}")

	def format_date(self, timestamp):
		"""Format a timestamp into a human-readable date."""
		return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    
	def on_filter_changed(self, combo):
		"""Filter results based on the selected file type."""
		file_type = combo.get_active_text()
		if file_type == "All Files":
			filtered_files = self.files
		elif file_type == "Images":
			filtered_files = [f for f in self.files if f["name"].endswith((".png", ".jpg", ".jpeg", ".gif"))]
		elif file_type == "Documents":
			filtered_files = [f for f in self.files if f["name"].endswith((".pdf", ".docx", ".txt"))]
		elif file_type == "Videos":
			filtered_files = [f for f in self.files if f["name"].endswith((".mp4", ".avi"))]
		else:
			filtered_files = self.files

		# self.populate_results(filtered_files)
		GLib.idle_add(self.populate_results, filtered_files)

	# def on_sort_changed(self, combo):
	# 	"""Handle sorting change."""
	# 	sort_by = combo.get_active_text()
	# 	# Run sorting in a separate thread to avoid UI freeze
	# 	threading.Thread(target=self.perform_sort, args=(sort_by,)).start()

	def on_sort_changed(self, combo):
		"""Sort results based on the selected criterion."""
		sort_by = combo.get_active_text()
		if sort_by == "Sort by Name":
			sorted_files = sorted(self.files, key=lambda f: f["name"])
		elif sort_by == "Sort by Date":
			sorted_files = sorted(self.files, key=lambda f: f["date"], reverse=True)
		else:
			sorted_files = self.files

		# self.populate_results(sorted_files)
		GLib.idle_add(self.populate_results, sorted_files)

	def create_thumbnail(self, file_path):
		"""Create a thumbnail for the given file if it's an image."""
		try:
			#if self.is_thumbnailable(file_path):
			#if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".mp4")):
			pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file_path, 64, 64)
			return pixbuf
		except Exception as e:
			pass
		return None

	##########################################################################
	# SEARCH FILES
	##########################################################################
	# def scan_files_folder(self):
	# 	"""Scan files and return a list of file dictionaries."""
	# 	file_list = []
	# 	if os.path.exists(self.documents_path):
	# 		for root, dirs, files in os.walk(self.documents_path):
	# 			for file_name in files:
	# 				file_path = os.path.join(root, file_name)
	# 				file_date = os.path.getmtime(file_path)
	# 				file_list.append({
	# 					"name": file_name,
	# 					"path": file_path,
	# 					"date": file_date
	# 				})

	# 	print(file_list)
	# 	return file_list

	# def populate_results(self, files):
	# 	"""Populate the results list with files."""
	# 	# Clear previous items
	# 	child = self.results_list.get_first_child()
	# 	while child is not None:
	# 		next_child = child.get_next_sibling()  # Save reference to the next sibling
	# 		self.results_list.remove(child)       # Remove the current child
	# 		child = next_child                    # Move to the next child

	# 	# Add new items
	# 	for file in files:
	# 		row = Gtk.ListBoxRow()
	# 		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
	# 		print(file)
	# 		# # Create a thumbnail for supported files
	# 		# thumbnail = self.create_thumbnail(file["path"])
	# 		# if thumbnail:
	# 		# 	image = Gtk.Image.new_from_pixbuf(thumbnail)
	# 		# 	hbox.append(image)

	# 		# # File name label
	# 		# file_label = Gtk.Label(label=file["name"], xalign=0)
	# 		# hbox.append(file_label)

	# 		# # File date label
	# 		# date_label = Gtk.Label(label=self.format_date(file["date"]))
	# 		# hbox.append(date_label)

	# 		# row.set_child(hbox)
	# 		# self.results_list.append(row)

	# def create_thumbnail(self, file_path):
	# 	"""Create a thumbnail for the given file if it's an image."""
	# 	try:
	# 		#if self.is_thumbnailable(file_path):
	# 		#if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".mp4")):
	# 		pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(file_path, 64, 64)
	# 		return pixbuf
	# 	except Exception as e:
	# 		pass
	# 	return None

	# # Example of checking if a file has a valid extension for a thumbnail or preview
	# def is_thumbnailable(file_path):
	# 	return any(file_path.lower().endswith(ext) for ext in server.thumbnails_extensions_list)

	# def format_date(self, timestamp):
	# 	"""Format a timestamp into a human-readable date."""
	# 	from datetime import datetime
	# 	return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

	# def on_search_changed(self, entry):
	# 	"""Filter results based on the search query."""
	# 	query = entry.get_text().lower()  # Get the search query and make it lowercase

	# 	if query:
	# 		# Scan the folder and filter the results based on the search query
	# 		self.files = self.scan_files_folder()
	# 		filtered_files = [f for f in self.files if query in f["name"].lower()]
	# 		self.populate_results(filtered_files)
	# 	else:
	# 		# If no query is entered, don't show any results
	# 		self.populate_results([])

	# def on_filter_changed(self, combo):
	# 	"""Filter results based on the selected file type."""
	# 	file_type = combo.get_active_text()
	# 	if file_type == "All Files":
	# 		filtered_files = self.files
	# 	elif file_type == "Images":
	# 		filtered_files = [f for f in self.files if f["name"].endswith((".png", ".jpg", ".jpeg", ".gif"))]
	# 	elif file_type == "Documents":
	# 		filtered_files = [f for f in self.files if f["name"].endswith((".pdf", ".docx", ".txt"))]
	# 	elif file_type == "Videos":
	# 		filtered_files = [f for f in self.files if f["name"].endswith((".mp4", ".avi"))]
	# 	else:
	# 		filtered_files = self.files

	# 	self.populate_results(filtered_files)

	# def on_sort_changed(self, combo):
	# 	"""Sort results based on the selected criterion."""
	# 	sort_by = combo.get_active_text()
	# 	if sort_by == "Sort by Name":
	# 		sorted_files = sorted(self.files, key=lambda f: f["name"])
	# 	elif sort_by == "Sort by Date":
	# 		sorted_files = sorted(self.files, key=lambda f: f["date"], reverse=True)
	# 	else:
	# 		sorted_files = self.files

	# 	self.populate_results(sorted_files)

	##########################################################################
	# ABOUT PAGE
	##########################################################################
	def load_folders_from_config(self):
		"""Loads folders from the config file."""
		config = configparser.ConfigParser()

		if os.path.exists(server.CONF_LOCATION):
			config.read(server.CONF_LOCATION)
			if 'EXCLUDE_FOLDER' in config:
				self.ignored_folders = config.get('EXCLUDE_FOLDER', 'folders').split(',')
				# Remove empty strings in case of trailing commas
				self.ignored_folders = [folder.strip() for folder in self.ignored_folders if folder.strip()]
		# else:
		#     # Create the config file if it doesn't exist
		#     os.makedirs(os.path.dirname(server.CONF_LOCATION), exist_ok=True)
		#     with open(server.CONF_LOCATION, 'w') as config_file:
		#         config_file.write('[EXCLUDE_FOLDER]\nfolders=\n')

	def on_ignore_hidden_switch_toggled(self, switch, gparam):
		true_false: str = 'false'

		# Handle the toggle state of the ignore hidden switch
		if switch.get_active():
			print("Ignoring hidden files and folders.")
			true_false = 'true'

		# Update the conf file
		server.set_database_value(
			section='EXCLUDE',
			option='exclude_hidden_itens',
			value=true_false)
		
	def auto_select_backup_device(self):
		# Get stored driver_location and driver_name
		driver_location = server.get_database_value(
			section='DRIVER',
			option='driver_location')

		driver_name = server.get_database_value(
			section='DRIVER',
			option='driver_name')

		# Automatically select the registered device
		if driver_name and driver_location:
			# Iterate over the items in the ComboBoxText to find the index of the device
			model = self.backup_device_list.get_model()
			for i, item in enumerate(model):
				if item[0] == driver_name:  # Use index 0 to access the item text
					self.backup_device_list.set_active(i)
					break

	def auto_select_auto_backup(self):
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
	
	def auto_select_hidden_itens(self):
		exclude_hidden_itens: bool = server.get_database_value(
			section='EXCLUDE',
			option='exclude_hidden_itens')

		# Auto checkbox
		if exclude_hidden_itens:
			self.ignore_hidden_switch.set_active(True)
		else:
			self.ignore_hidden_switch.set_active(False)

	def on_location_changed(self, combo_row, pspec):
		# Handle location changes
		self.available_devices_location()  # Refresh devices list based on selected location

	def on_folder_button_clicked(self, button):
		# Handle folder button click
		print("Folder button clicked")
		# Open a file chooser dialog if needed
	
	def on_auto_backup_switch_toggled(self, switch, pspec):
		if self.programmatic_change or self.switch_cooldown_active:
			return  # Exit the function if it's a programmatic change or cooldown active

		# Disable the switch immediately and start the cooldown
		self.disable_switch_for_cooldown(switch)

		# Handle system tray switch toggling
		auto_backup_active = switch.get_active()
		true_false: str = 'false'

		if auto_backup_active:
			if not server.is_daemon_running():
				self.start_daemon()  # Only start if not running
			true_false = 'true'
			self.create_autostart_entry()  # Create .desktop file for auto startup
		else:
			self.stop_daemon()  # Stop the daemon
			self.remove_autostart_entry()  # Optionally remove autostart entry

		# Update the conf file
		server.set_database_value(
			section='BACKUP',
			option='automatically_backup',
			value=true_false)
		
	def disable_switch_for_cooldown(self, switch):
		"""Disables the switch and re-enables it after the cooldown period."""
		self.switch_cooldown_active = True
		switch.set_sensitive(False)  # Disable the switch to prevent user interaction

		def enable_switch_after_cooldown():
			time.sleep(5)  # Cooldown delay
			GLib.idle_add(self.enable_switch, switch)  # Re-enable in the main thread

		# Start the cooldown in a new thread to avoid blocking the UI
		threading.Thread(target=enable_switch_after_cooldown, daemon=True).start()
	
	def enable_switch(self, switch):
		"""Re-enable the switch after the cooldown period."""
		self.switch_cooldown_active = False
		self.auto_backup_switch.set_sensitive(True)  # Re-enable the switch

	#  TO DELETE
	# def on_auto_backup_switch_toggled(self, switch, pspec):
	# 	if self.programmatic_change:
	# 		return  # Exit the function if it's a programmatic change

	# 	# Handle system tray switch toggling
	# 	auto_backup_active = switch.get_active()
	# 	true_false: str = 'false'

	# 	if auto_backup_active:
	# 		if not server.is_daemon_running():
	# 			self.start_daemon()  # Only start if not running
	# 		true_false = 'true'
	# 		self.create_autostart_entry()  # Create .desktop file for auto startup
	# 	else:
	# 		self.stop_daemon()  # Stop the daemon
	# 		self.remove_autostart_entry()  # Optionally remove autostart entry

	# 	# Update the conf file
	# 	server.set_database_value(
	# 		section='BACKUP',
	# 		option='automatically_backup',
	# 		value=true_false)

	def create_autostart_entry(self):
		autostart_dir = os.path.expanduser("~/.config/autostart/")
		os.makedirs(autostart_dir, exist_ok=True)

		desktop_file_content = f"""
			[Desktop Entry]
			Type=Application
			Exec=flatpak run --command=python3 {server.ID} /app/share/dataguardian/src/at_boot.py
			X-GNOME-Autostart-enabled=true
			Name={server.APP_NAME}
			Comment[en_US]=Automatically start {server.APP_NAME}
			Comment=Automatically start {server.APP_NAME}
			"""

		with open(os.path.join(autostart_dir, f"{server.APP_NAME_CLOSE_LOWER}_autostart.desktop"), 'w') as f:
			f.write(desktop_file_content)
		logging.info("Autostart entry created.")

	def remove_autostart_entry(self):
		# autostart_file = os.path.expanduser(f"~/.config/autostart/{server.APP_NAME.lower()}_autostart.desktop")
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

	def on_folder_select_button_clicked(self, button):
		dialog = Gtk.FileChooserDialog(
			title="Select a Folder To Ignore",
			action=Gtk.FileChooserAction.SELECT_FOLDER,
		)

		# Set the transient parent to ensure proper behavior
		dialog.set_transient_for(self)

		# Add buttons for the dialog
		dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
		dialog.add_button("_Select", Gtk.ResponseType.OK)

		dialog.connect("response", self.on_filechooser_response)

		dialog.present()

	def on_filechooser_response(self, dialog, response):
		if response == Gtk.ResponseType.OK:
			selected_folder = dialog.get_file()
			
			if selected_folder is not None:
				selected_folder = selected_folder.get_path()
				if selected_folder not in self.ignored_folders:
					self.ignored_folders.append(selected_folder)
					self.add_folder_to_list(selected_folder)
					self.save_folders_to_config()
				print(f"Selected folder: {selected_folder}")
		dialog.destroy()

	def save_folders_to_config(self):
		"""Saves the current list of ignored folders to the config file."""
		config = configparser.ConfigParser()
		config['EXCLUDE_FOLDER'] = {'folders': ','.join(self.ignored_folders)}
		
		server.set_database_value(
			section='EXCLUDE_FOLDER', 
			option='folders', 
			value=','.join(self.ignored_folders))
		
	def add_folder_to_list(self, folder):
		# Create a ListBoxRow to represent the folder
		row = Gtk.ListBoxRow()

		# Create a box to hold the label and the remove button
		box = Gtk.Box(
			orientation=Gtk.Orientation.HORIZONTAL, 
			spacing=10)
		
		# Create a label for the folder
		label = Gtk.Label(
			label=f"  {folder}")
		
		# Create a remove button
		remove_button = Gtk.Button(
			label="-")
		remove_button.set_tooltip_text("Remove folder")
		remove_button.connect("clicked", self.on_remove_folder_clicked, row, folder)

		# Add the label and the remove button to the box
		box.append(remove_button)
		box.append(label)

		# Add the box to the ListBoxRow
		row.set_child(box)
		
		# Add the row to the listbox
		self.listbox.append(row)
	
	def on_remove_folder_clicked(self, button, row, folder):
		"""Removes the folder from the ListBox and updates the config."""
		self.listbox.remove(row)
		self.ignored_folders.remove(folder)
		self.save_folders_to_config()

	def on_backup_device_selected(self, combo_box):
		# Handle backup device selection
		selected_device = combo_box.get_active_text()
		driver_location = f"{device_location()}/{SERVER().USERNAME}/{selected_device}"

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
			value=str(selected_device)
		)

		# Enable switch
		self.auto_backup_switch.set_sensitive(True)

	def available_devices_location(self, button=None):
		location = device_location()  # Get backup device location. /media or /run

		if location:
			try:
				# Clear previous device items from the ComboBox
				self.backup_device_list.remove_all()

				# Iterate over the external devices and add them to the list
				for backup_device in os.listdir(f'{location}/{SERVER().USERNAME}'):
					# if "'" not in backup_device and " " not in backup_device:
					self.backup_device_list.append_text(backup_device)

			except FileNotFoundError:
				print(f"Path {location}/{SERVER().USERNAME} does not exist or cannot be accessed.")
		else:
			print("No devices found.")

		return True  # Keep the timeout running


class FileSearchHandler:
    def __init__(self, documents_path, update_results_callback):
        self.documents_path = documents_path
        self.update_results_callback = update_results_callback
        self.files = []

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
        self.files = file_list
        return file_list

    def filter_files(self, query):
        """Filter results based on the search query."""
        return [f for f in self.files if query.lower() in f["name"].lower()]

    def filter_by_file_type(self, file_type):
        """Filter results based on the selected file type."""
        if file_type == "All Files":
            return self.files
        elif file_type == "Images":
            return [f for f in self.files if f["name"].endswith((".png", ".jpg", ".jpeg", ".gif"))]
        elif file_type == "Documents":
            return [f for f in self.files if f["name"].endswith((".pdf", ".docx", ".txt"))]
        elif file_type == "Videos":
            return [f for f in self.files if f["name"].endswith((".mp4", ".avi"))]
        return self.files

    def sort_files(self, sort_by):
        """Sort results based on the selected criterion."""
        if sort_by == "Sort by Name":
            return sorted(self.files, key=lambda f: f["name"])
        elif sort_by == "Sort by Date":
            return sorted(self.files, key=lambda f: f["date"], reverse=True)
        return self.files

    def format_date(self, timestamp):
        """Format a timestamp into a human-readable date."""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


if __name__ == '__main__':
	app = Adw.Application()
	win = UIWindow(application=app)
	app.run()