from has_driver_connection import has_driver_connection
from server import *

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


class Daemon:
	def __init__(self):
		self.user_home: str = os.path.expanduser("~")  # Get user's home directory
		self.previous_files: dict = {}
		self.to_backup: list = []  # File, mod time
		self.failed_backup: list = []  # Track files that haven't been successfully backed up
		self.copied_files: int = 0
		self.start_time = time.time()
		self.backup_in_progress: bool = False
		self.is_backing_up_to_main: bool = False
		self.suspend_flag = False  # Flag to handle suspension
		self.main_backup_dir: str = server.main_backup_folder()
		self.updates_backup_dir: str = server.backup_folder_name()
		self.filtered_home_files: tuple = server.get_filtered_home_files()  # File, rel_path and size

		self.current_date = datetime.now().strftime('%d-%m-%Y')
		self.current_time = datetime.now().strftime('%H-%M')

		if has_driver_connection():
			server.setup_logging()

	def file_was_updated(self, file_path: str, rel_path: str) -> bool:
		# Get the modification time of the current file
		file_mod_time = os.path.getmtime(file_path)
		
		# Get the list of backup dates to compare
		backup_dates: list = server.has_backup_dates_to_compare()

		if backup_dates:
			# Iterate over the sorted date folders (newest to oldest)
			for date_folder in backup_dates:
				date_folder_path = os.path.join(server.backup_folder_name(), date_folder)

				if os.path.isdir(date_folder_path):
					# Sort and iterate over the time subfolders within the date folder (latest to oldest)
					time_folders = sorted(os.listdir(date_folder_path), reverse=True)

					for time_folder in time_folders:
						time_folder_path = os.path.join(date_folder_path, time_folder)

						if os.path.isdir(time_folder_path):
							updated_file_path = os.path.join(time_folder_path, rel_path)

							# If the backup file exists, compare the modification times
							if os.path.exists(updated_file_path):
								updated_mod_time = os.path.getmtime(updated_file_path)

								if updated_mod_time != file_mod_time:
									# File modification time is different, backup is needed
									return True
		else:
			# No backup dates, compare with the .main_backup folder
			main_file_path = os.path.join(server.main_backup_folder(), rel_path)

			if os.path.exists(main_file_path):
				main_mod_time = os.path.getmtime(main_file_path)

				if main_mod_time != file_mod_time:
					# File modification time is different, backup is needed
					return True

		# No updates required
		return False

	async def make_first_backup(self):
		# Before starting the backup, set the flag
		self.is_backing_up_to_main = True

		for path, rel_path, size in self.filtered_home_files:
			# Skip files that were already backed up
			dest_path = os.path.join(self.main_backup_dir, rel_path)
			if os.path.exists(dest_path):
				continue

			await server.backup_file(path)

		logging.info("Successfully made the first backup.")

		# After finishing the backup process, reset the flag
		self.is_backing_up_to_main = False

		# After finishing the backup process, you can remove the interrupted flag
		if os.path.exists(server.INTERRUPTED_MAIN):
			os.remove(server.INTERRUPTED_MAIN)

	def get_backup_file_path(self, file, date_folder=None):
		# Use the .main_backup folder or date-based folder if specified
		if date_folder:
			return os.path.join(self.updates_backup_dir, date_folder, os.path.relpath(file, self.user_home))
		return os.path.join(self.main_backup_dir, os.path.relpath(file, self.user_home))

	async def backup_file(self, file, new_file=False):
		if new_file:
			# Backup to .main_backup if it's a new file
			backup_file_path = self.get_backup_file_path(file)
			os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
			logging.info(f"File backed up: {file} to {backup_file_path}")
		else:
			# Create the folder for the current date and time for updated files
			date_folder = datetime.now().strftime("%d-%m-%Y/%H-%M")
			backup_file_path = self.get_backup_file_path(file, date_folder)
			os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
			logging.info(f"File backed up (update): {file} to {backup_file_path}")
		
		try:
			shutil.copy2(file, backup_file_path)
		except FileNotFoundError as r:
			pass
		except Exception as e:
			logging.error(f"Error: {e}")

	def save_backup(self, process=None):
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
					continue
				await server.backup_file(path)
		else:
			logging.info("Starting fresh backup to .main_backup.")

			# Check for base folders before continues
			if server.has_backup_device_enough_space(
				file_path=None,
				backup_list=self.filtered_home_files):

				await self.make_first_backup()
	
	async def process_backups(self):
		tasks: list = []

		try:
			# Have to check the file 
			for file_path, rel_path, size in server.get_filtered_home_files():
				modded_main_file_path = os.path.join(self.main_backup_dir,  os.path.relpath(file_path, server.USER_HOME))
				
				# Check for new files
				if not os.path.exists(modded_main_file_path):
					tasks.append(self.backup_file(file_path, new_file=True))
				# Check from latest to oldest date/time dir
				elif self.file_was_updated(file_path, rel_path):
					# Fx. /media/macbkook/dataguardian/.main_backup/20-10-2024/10-10/
					tasks.append(self.backup_file(file_path, new_file=False))
			
			if tasks:
				tasks.append(backup_flatpaks_names())

			await asyncio.gather(*tasks)

		except ValueError as e:
			logging.error(f"ValueError: {e}")

	async def run_backup_cycle(self):
		# Make first backup
		if server.is_first_backup():
			await self.make_first_backup()

		while True:
			if has_driver_connection():
				await self.process_backups()
			
			await asyncio.sleep(30)  # Wait for the specified interval
	
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
	server = SERVER()
	daemon = Daemon()

	setproctitle.setproctitle(f'{server.APP_NAME} - daemon')
	signal.signal(signal.SIGTERM, daemon.signal_handler)  # Termination signal
	signal.signal(signal.SIGINT, daemon.signal_handler)   # Interrupt signal (Ctrl+C)
	logging.info("Starting file monitoring...")
	asyncio.run(daemon.run_backup_cycle())