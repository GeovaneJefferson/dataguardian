from server import *
from has_driver_connection import has_driver_connection
from ui import UIWindow

UPDATE_DELAY: int = 5

async def backup_flatpaks_names():
	flatpak_location: str = server.flatpak_txt_location()
	flatpaks: set = set()

	try:
		# Ensure the directory exists
		os.makedirs(os.path.dirname(flatpak_location), exist_ok=True)

		# Create the file if it doesn't exist and write the flatpak names
		with open(flatpak_location, 'w') as configfile:
			with os.popen(server.GET_FLATPAKS_APPLICATIONS_NAME) as flatpak_process:
				for flatpak in flatpak_process:
					flatpak_name = flatpak.strip()
					flatpaks.add(flatpak_name)
					configfile.write(flatpak_name + '\n')
		logging.info(f"Flatpaks installations was backed up: {flatpak_location}")
	except IOError as e:
		logging.error(f"Error backing up flatpaks installations: {e}")

def check_main_backup(rel_path, last_mod_time):
	"""
	Compare the file with the .main_backup folder to check if it's new or updated.
	"""
	backup_file_path = os.path.join(server.main_backup_folder(), rel_path)
	if os.path.exists(backup_file_path):
		backup_mod_time = os.path.getmtime(backup_file_path)
		if backup_mod_time >= last_mod_time:
			return True  # No need to backup
	return False  # File needs to be backed up

def check_previous_backups(rel_path, last_mod_time):
	"""
	Check the latest to oldest date/time folders for the file and its modification time.

	Parameters:
	- rel_path: The relative path of the file being checked.
	- last_mod_time: The last modification time of the file to compare against.

	Returns:
	- True if the file is already backed up and up-to-date; otherwise, False.
	"""
	# Filter for folders that have a '-' in their name (to include date folders like 'yy-mm-dd')
	backup_dates = sorted(
		[date for date in os.listdir(server.backup_folder_name()) if '-' in date],
		reverse=True  # Sort dates from newest to oldest
	)

	# Iterate over the sorted date folders (newest to oldest)
	for date_folder in backup_dates:
		date_folder_path = os.path.join(server.backup_folder_name(), date_folder)
		# print(f"Checking date folder: {date_folder_path}")

		# Ensure that the path is indeed a directory
		if os.path.isdir(date_folder_path):
			# Sort the time subfolders within the date folder (latest to oldest)
			time_folders = sorted(os.listdir(date_folder_path), reverse=True)

			# Iterate over the sorted time folders
			for time_folder in time_folders:
				time_folder_path = os.path.join(date_folder_path, time_folder)
				# print(f"Checking time folder: {time_folder_path}")

				# Ensure that the path is indeed a directory
				if os.path.isdir(time_folder_path):
					backup_file_path = os.path.join(time_folder_path, rel_path)

					# Check if the backup file exists in the current time folder
					if os.path.exists(backup_file_path):
						backup_mod_time = os.path.getmtime(backup_file_path)

						# Compare the modification times
						if backup_mod_time >= last_mod_time:
							# print(f"File {rel_path} is already backed up in {time_folder_path}.")
							return True  # File is already backed up and up-to-date
	return False  # File needs to be backed up


class Daemon:
	def __init__(self):
		self.user_home: str = os.path.expanduser("~")  # Get user's home directory
		self.previous_files: dict = {}
		self.to_backup: list = []  # File, mod time and size
		self.failed_backup: list = []  # Track files that haven't been successfully backed up
		self.copied_files: int = 0
		self.start_time = time.time()
		self.backup_in_progress: bool = False
		self.is_backing_up_to_main: bool = False
		self.suspend_flag = False  # Flag to handle suspension
		self.main_backup_dir: str = server.main_backup_folder()
		self.updates_backup_dir: str = server.backup_folder_name()
		self.filtered_home_files = server.get_filtered_home_files()

		self.current_date = datetime.now().strftime('%d-%m-%Y')
		self.current_time = datetime.now().strftime('%H-%M')

		if has_driver_connection():
			server.setup_logging()
			# asyncio.run(self.load_backup())

	def save_backup(self, process=None):
		"""Saves only the remaining unbacked files to a JSON file."""
		print('Saving state...')

		if process == '.main_backup':
			# Create the interrupted file if it doesn't exist
			if not os.path.exists(server.INTERRUPTED_MAIN):
				with open(server.INTERRUPTED_MAIN, 'w') as f:
					f.write('Backup to .main_backup was interrupted.')
				logging.info(f"Created interrupted file: {server.INTERRUPTED_MAIN}")

	async def load_backup(self):
		"""Loads the backup state from the interrupted file if it exists."""
		if os.path.exists(server.INTERRUPTED_MAIN):
			logging.info("Resuming backup to .main_backup from interrupted state.")
			for path, rel_path, size in self.filtered_home_files:
				# Skip files that were already backed up
				dest_path = os.path.join(self.main_backup_dir, rel_path)
				if os.path.exists(dest_path):
					# logging.info(f"File already backed up: {dest_path}, skipping...")
					continue

				# Backup the file asynchronously
				await server.backup_file(path)
		else:
			logging.info("Starting fresh backup to .main_backup.")

			# Check for base folders before continues
			if server.has_backup_device_enough_space(
				file_path=None,
				backup_list=self.filtered_home_files):

				await self.make_first_backup()  # Call your method for the initial backup

	async def make_first_backup(self):
		# Before starting the backup, set the flag
		self.is_backing_up_to_main = True

		for path, rel_path, size in self.filtered_home_files:
			# Skip files that were already backed up
			dest_path = os.path.join(self.main_backup_dir, rel_path)
			if os.path.exists(dest_path):
				# logging.info(f"File already backed up: {dest_path}, skipping...")
				continue

			await server.backup_file(path)

		logging.info("Successfully made the first backup.")

		# After finishing the backup process, reset the flag
		self.is_backing_up_to_main = False

		# After finishing the backup process, you can remove the interrupted flag
		if os.path.exists(server.INTERRUPTED_MAIN):
			os.remove(server.INTERRUPTED_MAIN)

			# self.copied_files += 1
			# if self.copied_files % 10 == 0:
			#     server.print_progress_bar(
			#         progress=self.copied_files,
			#         total=self.total_file_count,
			#         start_time=self.start_time)

	async def check_for_new_files(self):
		current_files = self.get_file_modification_times()
		tasks: list = []

		try:
			# Check for new files
			for file, mod_time in current_files.items():
				if file not in self.previous_files:
					if not os.path.exists(os.path.join(self.main_backup_dir, os.path.relpath(file, self.user_home))):
						tasks.append(server.backup_file(file, mod_time))
						logging.info(f"Successfully backed up: {file} to {os.path.join(self.main_backup_dir, os.path.relpath(file, self.user_home))}")
					# Append file with modification time for tracking
					if (file, mod_time) not in self.to_backup:
						file_size = os.path.getsize(file)  
						# self.to_backup.append((file, mod_time, file_size))  #  2 - os.path.relpath(file, self.user_home)
						self.to_backup.append((file, os.path.relpath(file, self.user_home), file_size))  #  2 - os.path.relpath(file, self.user_home)
		except ValueError as e:
			logging.error(f"ValueError: {e}")

		await asyncio.gather(*tasks)

	async def backup_updates(self, file, mod_time=None):
		"""Backup updated files in a timestamped directory while retaining the original folder structure."""
		attempt_count = 0  # Track the number of backup attempts

		while True:
			try:
				# Get the relative path of the file from the user home directory
				relative_path = os.path.relpath(file, self.user_home)

				# If mod_time is not provided, use the current modification time
				mod_time = mod_time or os.path.getmtime(file)
				timestamp = datetime.fromtimestamp(mod_time).strftime("%d-%m-%Y/%H-%M")

				# Construct the destination path using the original folder structure
				dest_path = os.path.join(self.updates_backup_dir, timestamp, relative_path)

				# Create the directory if it doesn't exist
				os.makedirs(os.path.dirname(dest_path), exist_ok=True)

				# Check if there is enough space on the backup device
				if not server.has_backup_device_enough_space(
						file_path=file, 
						backup_list=None):
					raise OSError("Not enough space on the backup device")

				# Copy the file to the update backup location
				shutil.copy2(file, dest_path)
				logging.info(f"Successfully backed up (update): {file} to {dest_path}")

				# If backup is successful, remove it from failed_backup if it was there
				self.failed_backup = [fb for fb in self.failed_backup if fb[0] != file]
				break  # Break out of the loop on success

			except OSError as e:
				if "No space left" in str(e) or "Not enough space" in str(e):
					logging.warning(f"Not enough space to back up updated file {file}. Attempting to delete the oldest backup folder...")
					if attempt_count >= 5:  # Limit the number of attempts to avoid infinite loop
						logging.error(f"Maximum number of backup attempts reached for file {file}.")
						break

					# Delete the oldest backup folder and retry
					try:
						server.delete_oldest_backup_folder()
						attempt_count += 1
					except OSError as delete_error:
						logging.error(f"Failed to delete the oldest backup folder: {delete_error}")
						break

				logging.error(f"Error backing up updated file {file}: {e}")
				self.failed_backup.append((file, mod_time))
				break

	def get_file_modification_times(self):
		"""Returns a dictionary of file paths and their last modification times, only for non-empty files."""
		mod_times = {}
		for root, dirs, files in os.walk(self.user_home):
			dirs[:] = [d for d in dirs if not d.startswith('.') and d not in server.EXCLUDE_FILES]
			for file in files:
				if not file.startswith('.'):  # Ignore the log file
					file_path = os.path.join(root, file)
					try:
						if os.path.getsize(file_path) > 0:  # Only consider files greater than 0 bytes
							mod_times[file_path] = os.path.getmtime(file_path)
					except OSError:
						pass  # Optionally log the error if needed
		return mod_times

	async def startup_monitor_for_updates(self):
		backup_needed: bool = False
		tasks: list = []

		# Iterate through all files in the source directory
		for path, rel_path, size in self.filtered_home_files:
			last_mod_time = os.path.getmtime(path)

			# First compare with the latest date/time folders
			if not check_previous_backups(rel_path, last_mod_time):
				# If not found in date/time folders, compare with .main_backup
				if not check_main_backup(rel_path, last_mod_time):
					# Backup is needed for this file
					backup_needed = True

		# Only create the backup directory if a backup is needed
		if backup_needed:
			base_backup_dir = os.path.join(
				server.backup_folder_name(),
				self.current_date,
				self.current_time)

			os.makedirs(base_backup_dir, exist_ok=True)

			# Now perform the actual backup
			for path, rel_path, size in self.filtered_home_files:
				last_mod_time = os.path.getmtime(path)
				if not check_previous_backups(rel_path, last_mod_time):
					if not check_main_backup(rel_path, last_mod_time):
						# Mark the file for backup
						self.to_backup.append((path, rel_path, size))

			# Now backup all the files in the to_backup list
			if self.to_backup:
				for path, rel_path, size in self.to_backup:
					dst_path = os.path.join(base_backup_dir, rel_path)
					os.makedirs(os.path.dirname(dst_path), exist_ok=True)
					shutil.copy2(path, dst_path)
					logging.info(f"File backed up (update): {path} to {dst_path}")
					
		await asyncio.gather(*tasks)

	async def process_file_changes(self, current_files):
		"""Logs changes between previous and current file states."""
		# Log modified or new files and back them up
		tasks: list = []
		for file, mod_time in current_files.items():
			if file not in self.previous_files or self.previous_files[file] != mod_time:
				# If it's a new file or an update, check if it already exists in base backup
				if os.path.exists(os.path.join(self.main_backup_dir, os.path.relpath(file, self.user_home))):
					tasks.append(self.backup_updates(file, mod_time))

				# Add the file to to_backup only if it was modified or newly added
				if file not in self.to_backup:
					self.to_backup.append(file)

		# # Log deleted files
		# deleted_files = set(self.previous_files) - set(current_files)
		# for file in deleted_files:
		#     logging.info(f"File deleted: {file}")

		# Update to_backup with new files that are not backed up yet
		for file in current_files:
			if file not in self.previous_files:
				self.to_backup.append(file)

		if tasks:
			tasks.append(backup_flatpaks_names())

		await asyncio.gather(*tasks)

	async def monitor(self):
		"""Monitors the user home directory for changes and logs them."""
		if has_driver_connection():
			# Set backup in progress to True
			self.backup_in_progress = True

			# Make first backup
			if server.is_first_backup():
				await self.make_first_backup()

			await self.check_for_new_files()
			# Fetch the initial state of the files
			self.previous_files = self.get_file_modification_times()

			# await self.startup_monitor_for_updates()
			
			# Set backup in progress to False
			self.backup_in_progress = False
				
		while not self.backup_in_progress:
			# Check initial connection to the backup device
			if has_driver_connection():
				# Set backup in progress to True
				self.backup_in_progress = True

				await self.check_for_new_files()

				# Check for file changes
				current_files = self.get_file_modification_times()
				await self.process_file_changes(current_files)
				# Update the previous file state
				self.previous_files = current_files

				# # Close application pid file can not be found
				# if not UIWindow().is_daemon_running():
				# 	break
				
				# Set backup in progress to False
				self.backup_in_progress = False
				
			await asyncio.sleep(UPDATE_DELAY)  # Wait for the specified interval

	def signal_handler(self, signum, frame):
		"""Handles shutdown and sleep signals."""
		logging.info(f"Received signal: {signum}. Stopping daemon and saving backup state.")

		# Set the suspend flag to prevent further backups
		self.suspend_flag = True

		# Only save the state if backup was in progress
		if self.backup_in_progress:
			backup_status = '.main_backup' if self.is_backing_up_to_main else 'other backup'
			self.save_backup(backup_status)  # Save current state to JSON

		logging.info("System is going to sleep, shut down, restart or just terminated. Stopping backup.")
		sys.exit(0)


if __name__ == "__main__":
	# Set up signal handlers for shutdown and sleep
	server = SERVER()
	daemon = Daemon()

	setproctitle.setproctitle(f'{server.APP_NAME} - daemon')
	signal.signal(signal.SIGTERM, daemon.signal_handler)  # Termination signal
	signal.signal(signal.SIGINT, daemon.signal_handler)   # Interrupt signal (Ctrl+C)
	logging.info("Starting file monitoring...")
	asyncio.run(daemon.monitor())