from has_driver_connection import has_driver_connection
from server import *

WAIT_TIME: int = 5  #Minutes


def hash_file(file_path: str) -> str:
	"""Generate the SHA-256 hash of a file."""
	hash_sha256 = hashlib.sha256()
	with open(file_path, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_sha256.update(chunk)
	return hash_sha256.hexdigest()

def backup_flatpaks_names():
	flatpak_location: str = server.flatpak_txt_location()
	flatpaks: set = set()

	try:
		# Ensure the directory exists
		os.makedirs(os.path.dirname(flatpak_location), exist_ok=True)

		# Create the file only if the command returns output
		with os.popen(server.GET_FLATPAKS_APPLICATIONS_NAME) as flatpak_process:
			flatpak_output = flatpak_process.read()

			# Log if command returns no output
			if not flatpak_output:
				print("Flatpak command returned no output. Check if Flatpaks are installed or if the command is correct.")
				return

			# Process the output
			with open(flatpak_location, 'w') as configfile:
				for flatpak in flatpak_output.splitlines():
					flatpak_name = flatpak.strip()
					if flatpak_name:
						flatpaks.add(flatpak_name)
						configfile.write(flatpak_name + '\n') 

		# Inform the user that the process is complete
		if flatpaks:
			logging.info(f"Flatpaks installations was backed up: {flatpak_location}")
			
	except IOError as e:
		logging.error(f"Error backing up flatpaks installations: {e}")

def is_app_installed():
	"""Check if the Flatpak app is still installed."""
	try:
		# Run the Flatpak list command using flatpak-spawn
		result = sub.run(
			['flatpak', 'list', '--app', 'list', '--columns=application'],
			stdout=sub.PIPE,
			stderr=sub.PIPE,
			text=True  # Capture output as text
		)

		# Check if the app_id is in the output
		installed_apps = result.stdout.splitlines()
		if server.ID in installed_apps:
			return True
		return False
	except Exception as e:
		logging.error(f"Error checking if app is installed: {e}")
		return False


class Daemon:
	def __init__(self):
		self.user_home: str = os.path.expanduser("~")  # Get user's home directory
		self.previous_files: dict = {}
		self.to_backup: list = []  # File, mod time
		self.failed_backup: list = []  # Track files that haven't been successfully backed up
		self.copied_files: int = 0
		self.start_time = time.time()
		self.backup_in_progress: bool = False
		self.a: bool = None
		self.suspend_flag = False  # Flag to handle suspension
		self.main_backup_dir: str = server.main_backup_folder()
		self.updates_backup_dir: str = server.backup_folder_name()

		# self.current_date = datetime.now().strftime('%d-%m-%Y')
		# self.current_time = datetime.now().strftime('%H-%M')

	# TEST
	##########################################################################
	# EXCLUDE FOLDERS
	def load_ignored_folders_from_config(self):
		"""
		Load ignored folders from the configuration file.
		"""
		try:
			# Get the folder string from the config
			folder_string = server.get_database_value(
				section='EXCLUDE_FOLDER', 
				option='folders')
			
			# Split the folder string into a list
			return [folder.strip() for folder in folder_string.split(',')] if folder_string else []
		except ValueError as e:
			print(f"Configuration error: {e}")
			return []
		except Exception as e:
			print(f"Error while loading ignored folders: {e}")
			return []

	async def get_filtered_home_files(self) -> tuple:
		"""
		Retrieve all files from the home directory while optionally excluding hidden items,
		unfinished downloads (e.g., .crdownload), and folders specified in the EXCLUDE_FOLDER config.
		Returns a tuple containing the list of files and the total count of files.
		"""
		home_files = []
		excluded_dirs = ['__pycache__']  # Folders to exclude
		excluded_extensions = ['.crdownload', '.part', '.tmp']  # File extensions to exclude unfinished files

		# Load ignored folders from config
		ignored_folders = self.load_ignored_folders_from_config()
		
		exclude_hidden_itens: bool = server.get_database_value(
			section='EXCLUDE',
			option='exclude_hidden_itens')

		for root, dirs, files in os.walk(server.USER_HOME):
			# Check for suspension flag and handle it
			if self.suspend_flag:
				self.signal_handler(signal.SIGTERM, None)  # Handle suspension as needed

			# Exclude directories that match any ignored folder
			if any(os.path.commonpath([root, ignored_folder]) == ignored_folder for ignored_folder in ignored_folders):
				continue

			for file in files:
				try:
					src_path = os.path.join(root, file)
					rel_path = os.path.relpath(src_path, server.USER_HOME)
					size = os.path.getsize(src_path)

					# # Exclude hidden files, files in excluded directories, and unfinished files by extension
					# is_hidden_file = server.EXCLUDE_HIDDEN_ITENS and (
					# 	file.startswith('.') or
					# 	any(part.startswith('.') or part in excluded_dirs for part in rel_path.split(os.sep))
					# )
					
					# Exclude hidden files if the option is enabled
					if exclude_hidden_itens:  
						is_hidden_file = (
							file.startswith('.') or
							any(part.startswith('.') or part in excluded_dirs for part in rel_path.split(os.sep)))
					else:
						is_hidden_file = False  # Do not exclude hidden files if option is disabled

					is_unfinished_file = any(file.endswith(ext) for ext in excluded_extensions)

					if is_hidden_file or is_unfinished_file:
						continue  # Skip hidden, excluded, or unfinished files
					
					# Add the file info to the home_files list
					home_files.append((src_path, rel_path, size))
				except:
					continue

		return home_files

	def file_was_updated(self, file_path: str, rel_path: str) -> bool:
		"""Check if the file was updated by comparing its size and content hash (if sizes match)."""

		# Get the modification time and size of the current file
		try:
			current_file_size = os.path.getsize(file_path)
		except FileNotFoundError:
			return False

		# Get the list of backup dates to compare
		backup_dates: list = server.has_backup_dates_to_compare()
		
		if backup_dates:
			# Iterate over the sorted date folders (newest to oldest)
			for date_folder in backup_dates:
				date_folder_path = os.path.join(server.backup_folder_name(), date_folder)

				if os.path.isdir(date_folder_path):
					# Sorting time folders by actual time from latest to earliest
					time_folders = sorted(
						[time_folder for time_folder in os.listdir(date_folder_path) if '-' in time_folder],
						key=lambda t: datetime.strptime(t, '%H-%M'),
						reverse=True
					)

					for time_folder in time_folders:
						time_folder_path = os.path.join(date_folder_path, time_folder)

						if os.path.isdir(time_folder_path):
							updated_file_path = os.path.join(time_folder_path, rel_path)

							# If the backup file exists, compare the sizes and hashes if necessary
							if os.path.exists(updated_file_path):
								updated_file_size = os.path.getsize(updated_file_path)
				
								# Compare file sizes first
								if updated_file_size != current_file_size:
									# logging.info(f"File sizes are different. Backup needed for: {file_path}")
									return True
								else:
									# If sizes are the same, compare the file hashes
									current_file_hash = hash_file(file_path)
									updated_file_hash = hash_file(updated_file_path)

									if updated_file_hash != current_file_hash:
										return True
									return False

		# Fallback to .main_backup folder if no matching date-based backup was found
		main_file_path = os.path.join(server.main_backup_folder(), rel_path)

		if os.path.exists(main_file_path):
			main_file_size = os.path.getsize(main_file_path)

			# Compare file sizes first
			if main_file_size != current_file_size:
				return True
			else:
				# If sizes are the same, compare the file hashes
				current_file_hash = hash_file(file_path)
				main_file_hash = hash_file(main_file_path)

				if main_file_hash != current_file_hash:
					return True
		return False
	
	async def _make_first_backup(self):
		server.write_backup_status('Backing up')

		# Before starting the backup, set the flag
		self.a = True
		filtered_home: tuple = await self.get_filtered_home_files()

		for path, rel_path, size in filtered_home:
			# Check if PID file do not exist
			if not os.path.exists(server.DAEMON_PID_LOCATION):
				self.signal_handler(signal.SIGTERM, None)
				return

			# Skip files that were already backed up
			dest_path = os.path.join(self.main_backup_dir, rel_path)
			if os.path.exists(dest_path):
				continue

			if has_driver_connection():
				return

			# Attempt the backup
			await self.backup_file(file=path, new_file=True)
			
		# Update recent backup information
		server.update_recent_backup_information()

		# Backup flatpak 
		backup_flatpaks_names()

		logging.info("Successfully made the first backup.")

		# After finishing the backup process, reset the flag
		self.a = False

		# After finishing the backup process, you can remove the interrupted flag
		if os.path.exists(server.INTERRUPTED_MAIN):
			os.remove(server.INTERRUPTED_MAIN)

	backup_path_cache = {}
	def get_backup_file_path(self, file, date_folder=None):
		# Check if the path is already cached
		if file in self.backup_path_cache:
			return self.backup_path_cache[file]

		# Ensure file is relative to the user home directory
		try:
			relative_path = os.path.relpath(file, self.user_home)
		except ValueError:
			raise ValueError(f"File path '{file}' is not relative to user home '{self.user_home}'.")

		# Use the .main_backup folder or date-based folder if specified
		if date_folder:
			path = os.path.join(self.updates_backup_dir, date_folder, relative_path)
		else:
			path = os.path.join(self.main_backup_dir, relative_path)

		# Cache the calculated path
		self.backup_path_cache[file] = path

		return path

	# def get_backup_file_path(self, file, date_folder=None):
	# 	# Use the .main_backup folder or date-based folder if specified
	# 	if date_folder:
	# 		return os.path.join(self.updates_backup_dir, date_folder, os.path.relpath(file, self.user_home))
	# 	return os.path.join(self.main_backup_dir, os.path.relpath(file, self.user_home))
	
	def has_sufficient_space(self, file):
		statvfs = os.statvfs(self.main_backup_dir)
		available_space = statvfs.f_frsize * statvfs.f_bavail
		compare_size = os.path.getsize(file) <= available_space 
		return compare_size

	async def backup_file(self, file: str, new_file: bool = False):
		"""
		Backs up a file to the appropriate backup directory.
		
		Args:
			file (str): Path to the file to be backed up.
			new_file (bool): If True, backup the file to the main directory; 
							otherwise, use a timestamped directory for updates.
							
		Returns:
			str: Success or error message for logging purposes.
		"""
		self.backup_in_progress = True
		attempt_count = 0  # Number of backup attempts
		max_attempts = 5  # Maximum retries for backup

		while attempt_count < max_attempts:
			try:
				# Determine backup file path
				if new_file:
					# Backup new files to the main backup directory
					backup_file_path = self.get_backup_file_path(file)
				else:
					# Use a timestamped subdirectory for updated files
					date_folder = datetime.now().strftime("%d-%m-%Y/%H-%M")
					backup_file_path = self.get_backup_file_path(file, date_folder)
				
				try:
					# Check if there's sufficient space before attempting to backup
					if not self.has_sufficient_space(file=file):
						backup_dates = server.has_backup_dates_to_compare()

						# Ensure there's at least one backup folder left
						if not backup_dates or len(backup_dates) <= 1:
							error_msg = "Minimum saved backup reached. Aborting backup."
							logging.error(error_msg)
							return error_msg

						# Attempt to delete the oldest backup folder
						try:
							await server.delete_oldest_backup_folder()
							logging.info(f"Oldest backup folder deleted. Retrying backup for {file}.")
							attempt_count += 1
							continue  # Retry the backup process
						except OSError as delete_error:
							error_msg = f"Failed to delete the oldest backup folder: {delete_error}"
							logging.error(error_msg)
							return error_msg
				except Exception as e:
					return

				# Ensure the target backup directory exists
				os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)

				# Try copying the file to the backup path
				try:
					server.write_backup_status('Backing up')
					logging.info(f"Backing up file: {file} to {backup_file_path}")
					shutil.copy2(file, backup_file_path)
					success_msg = f"Successfully backed up: {file} to {backup_file_path}"
					logging.info(success_msg)
					return success_msg  # Exit on successful backup
				except FileNotFoundError as fnf_error:
					error_msg = f"File not found: {file}. Error: {fnf_error}"
					logging.error(error_msg)
					return error_msg
				except Exception as copy_error:
					error_msg = f"Error copying file: {file} to {backup_file_path}. Error: {copy_error}"
					logging.error(error_msg)
					return error_msg
			except OSError as os_error:
				# Catch unexpected OSErrors and abort
				error_msg = f"Unexpected OS error during backup: {os_error}"
				logging.error(error_msg)
				return error_msg

		# If we reach here, max attempts have been exhausted
		error_msg = f"Max attempts reached. Failed to back up {file}. Aborting backup."
		logging.error(error_msg)
		return error_msg

	def save_backup(self, process=None):
		logging.info("Saving settings...")

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

			# Before starting the backup, set the flag
			self.is_backing_up_to_main = True
			filtered_home: tuple = await self.get_filtered_home_files()

			for path, rel_path, size in filtered_home:
				# Check if PID file do not exist
				if not os.path.exists(server.DAEMON_PID_LOCATION):
					self.signal_handler(signal.SIGTERM, None)
					return

				# Skip files that were already backed up
				dest_path = os.path.join(self.main_backup_dir, rel_path)
				if os.path.exists(dest_path):
					continue

				await self.backup_file(file=path, new_file=True)

			logging.info("Successfully back up to .main.")

			# After finishing the backup process, reset the flag
			self.is_backing_up_to_main = False

			# After finishing the backup process, you can remove the interrupted flag
			if os.path.exists(server.INTERRUPTED_MAIN):
				os.remove(server.INTERRUPTED_MAIN)

		# else:
		# 	logging.info("Starting fresh backup to .main_backup.")

		# 	# Check for base folders before continues
		# 	if server.has_backup_device_enough_space(
		# 		file_path=None,
		# 		backup_list=self.get_filtered_home_files()):
		# 		# backup_list=server.get_filtered_home_files()):

		# 		await self._make_first_backup()

	async def process_backups(self):
		tasks: list = []

		try:
			# Fetch filtered home files
			filtered_home: tuple = await self.get_filtered_home_files()

			for file_path, rel_path, size in filtered_home:
				try:
					# Construct backup path
					modded_main_file_path = os.path.join(
						self.main_backup_dir, os.path.relpath(file_path, server.USER_HOME)
					)

					# Check if PID file exists (early termination condition)
					if not os.path.exists(server.DAEMON_PID_LOCATION):
						logging.warning("PID file missing. Stopping backup process.")
						self.signal_handler(signal.SIGTERM, None)
						return

					# Check if file is new or has been updated
					if not os.path.exists(modded_main_file_path):
						print('New file:', file_path)
						tasks.append(self.backup_file(file_path, new_file=True))
				
						# Update recent backup information
						server.update_recent_backup_information()

					elif self.file_was_updated(file_path, rel_path):
						print('Updated file:', file_path)
						tasks.append(self.backup_file(file_path, new_file=False))
				
						# Update recent backup information
						server.update_recent_backup_information()
				except Exception as file_error:
					pass
					# logging.error(f"Error processing file {file_path}: {file_error}")

			# Execute all backup tasks
			if tasks:
				# Backup additional resources (e.g., Flatpaks)
				try:
					backup_flatpaks_names()  # Ensure this is resilient to errors
				except Exception as flatpak_error:
					logging.error(f"Failed to backup Flatpak names: {flatpak_error}")

				try:
					await asyncio.gather(*tasks)
				except Exception as task_error:
					logging.error(f"Error during backup task execution: {task_error}")

		except ValueError as e:
			logging.error(f"ValueError in process_backups: {e}")
		except Exception as e:
			logging.error(f"Unexpected error in process_backups: {e}")

	async def run_backup_cycle(self):
		checked_for_first_backup: bool = False
		connection_logged: bool = False  # Track if connection status has already been logged

		try:
			# Check for unfinished backup to .main
			await self.load_backup()

			while True:
				# BUG
				'''
				Because is a flatpak, can not use '	['flatpak-spawn', '--host', 'flatpak', 'list', '--app', '--columns=application'],
				is a sandbox. Maybe, create a simple script, and send to /home/$USER/.var/app/com.gnome.dataguardian/config/, then call from there.
				'''
				# # Check if app still installed
				# if not is_app_installed():
				# 	logging.error(f"Error checking if app is installed: Closing daemon...")
				# 	# Call the signal handler to stop the daemon
				# 	self.signal_handler(signal.SIGTERM, None)  
				
				# Check if PID file do not exist
				if not os.path.exists(server.DAEMON_PID_LOCATION):
					logging.error("PID file missing. Daemon requires exit.")
					self.signal_handler(signal.SIGTERM, None)
					return
	
				if has_driver_connection():
					if not connection_logged:
						logging.info("Connection established to backup device.")
						connection_logged = True  # Avoid logging the same message multiple times

					# Make first backup if it's the first time and no backups have been made yet
					if not checked_for_first_backup and server.is_first_backup():
						await self._make_first_backup()  # Loop
						checked_for_first_backup = True

					# Process ongoing backups
					await self.process_backups()

				else:
					self.backup_in_progress = False

					if connection_logged:
						if self.is_backing_up_to_main:
							self.save_backup('.main_backup') 

						logging.info("Waiting for connection to backup device...")
						connection_logged = False  # Reset status to log when connection is re-established

				server.write_backup_status(f'Sleeping for: {WAIT_TIME} , Minute(s)')
				print('Resting for:', WAIT_TIME * 60)
				logging.info('Resting for:', WAIT_TIME * 60)
				await asyncio.sleep(WAIT_TIME * 60)  # Wait for the specified interval
		except Exception as e:
			logging.info(f"Error: {e}")
	
	def resume_handler(self, signum, frame):
		"""Handles wake-up signals (SIGCONT) and resumes backup operations."""
		logging.info(f"Received resume signal: {signum}. Resuming operations.")
		self.suspend_flag = False  # Clear suspend flag when system wakes up

	def signal_handler(self, signum, frame):
		"""Handles shutdown and sleep signals."""
		# logging.info(f"Received signal: {signum}. Stopping daemon and saving backup state.")

		# Set the suspend flag to prevent further backups
		self.suspend_flag = True

		# Only save the state if backup was in progress
		if self.backup_in_progress:
			backup_status = '.main_backup' if self.is_backing_up_to_main else 'other backup'
			self.save_backup(backup_status)  # Save current state to JSON

		logging.info("System is going to sleep, shut down, restart, PID file do not exist or just terminated. Stopping backup.")
		exit()


if __name__ == "__main__":
	server = SERVER()
	daemon = Daemon()

	server.setup_logging()

	setproctitle.setproctitle(f'{server.APP_NAME} - daemon')

	signal.signal(signal.SIGTERM, daemon.signal_handler)  # Termination signal
	signal.signal(signal.SIGINT, daemon.signal_handler)   # Interrupt signal (Ctrl+C)
	signal.signal(signal.SIGCONT, daemon.resume_handler)  # Continue signal (wake up)

	logging.info("Starting file monitoring...")

	asyncio.run(daemon.run_backup_cycle())