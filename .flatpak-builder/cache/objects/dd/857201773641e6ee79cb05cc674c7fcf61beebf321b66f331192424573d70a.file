from server import *
from has_driver_connection import has_driver_connection


WAIT_TIME = 5  # Minutes
COPY_CONCURRENCY = 10

# Configure logging for the daemon
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

excluded_dirs = ['__pycache__']
excluded_extensions = ['.crdownload', '.part', '.tmp']


##############################################################################
# Folder Filtering and Handling
##############################################################################
def load_ignored_folders_from_config():
    """
    Load ignored folders from the configuration.

    Returns:
        list: A list of ignored folder paths.
    """
    try:
        folder_string = server.get_database_value('EXCLUDE_FOLDER', 'folders')
        return [folder.strip() for folder in folder_string.split(',')] if folder_string else []
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        return []
    except Exception as e:
        logging.error(f"Error while loading ignored folders: {e}")
        return []
    
def get_top_level_folder_size(folder_path: str) -> int:
    """
    Calculate the total size of the immediate contents of a folder (files and subfolders).

    Args:
        folder_path (str): The path to the folder.

    Returns:
        int: The total size of the folder's immediate contents in bytes.
    """
    total_size = 0
    try:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total_size += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        # Add the size of the directory itself (not its contents)
                        total_size += entry.stat(follow_symlinks=False).st_size
                except FileNotFoundError:
                    logging.warning(f"Skipped missing entry: {entry.name}")
                    continue
                except Exception as e:
                    logging.error(f"Error processing entry {entry.name}: {e}")
                    continue
    except FileNotFoundError:
        logging.warning(f"Folder not found: {folder_path}")
    except Exception as e:
        logging.error(f"Error processing folder {folder_path}: {e}")
    return total_size

def get_changed_subfolders(folder_path: str, backup_folder_path: str) -> list:
    """
    Identify subfolders inside a top-level folder that have changed.

    Args:
        folder_path (str): The path to the top-level folder.
        backup_folder_path (str): The path to the corresponding backup folder.

    Returns:
        list: A list of paths to subfolders that have changed.
    """
    changed_subfolders = []

    # Check if the parent folder has changed
    current_folder_size = get_top_level_folder_size(folder_path)
    backup_folder_size = get_top_level_folder_size(backup_folder_path) if os.path.exists(backup_folder_path) else 0

    if current_folder_size == backup_folder_size:
        #print(f"Skipping folder '{folder_path}' as its size is unchanged.")  # Feedback
        return changed_subfolders  # Skip processing subfolders if the parent folder hasn't changed

    print(f"Folder '{folder_path}' has changed. Checking subfolders...")  # Feedback

    # Process subfolders only if the parent folder has changed
    for sub_entry in os.scandir(folder_path):
        if not sub_entry.is_dir() or sub_entry.name.startswith('.'):
            continue  # Skip files and hidden subfolders

        subfolder_path = sub_entry.path
        backup_subfolder_path = os.path.join(backup_folder_path, sub_entry.name)

        # Get the size of the subfolder and its backup
        current_subfolder_size = get_top_level_folder_size(subfolder_path)
        backup_subfolder_size = get_top_level_folder_size(backup_subfolder_path) if os.path.exists(backup_subfolder_path) else 0

        # Compare subfolder sizes
        if current_subfolder_size != backup_subfolder_size:
            print(f"Subfolder '{sub_entry.name}' has changed.")  # Feedback
            changed_subfolders.append(subfolder_path)
        else:
            print(f"Skipping subfolder '{sub_entry.name}' as its size is unchanged.")  # Feedback

    return changed_subfolders

def process_changed_subfolder(subfolder_path: str, backup_subfolder_path: str, home_files: list):
    """
    Process files inside a changed subfolder to identify new or updated files.

    Args:
        subfolder_path (str): The path to the changed subfolder.
        backup_subfolder_path (str): The path to the corresponding backup subfolder.
        home_files (list): The list to store identified files.
    """
    print(f"Processing subfolder: {subfolder_path}")  # Feedback
    print(f"Backup subfolder path: {backup_subfolder_path}")  # Feedback

    for root, dirs, files in os.walk(subfolder_path):
        # Exclude hidden subdirectories and directories in excluded_dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in excluded_dirs]
        for file in files:
            try:
                if file.startswith('.'):  # Skip hidden files
                    print(f"Skipping hidden file: {file}")  # Feedback
                    continue

                src_path = os.path.join(root, file)
                if not os.path.exists(src_path):  # Skip files that don't exist
                    print(f"File not found: {src_path}")  # Feedback
                    continue

                rel_path = os.path.relpath(src_path, server.USER_HOME)
                size = os.path.getsize(src_path)

                # Check if the file is in an excluded directory or has an excluded extension
                is_unfinished_file = any(file.endswith(ext) for ext in excluded_extensions)

                if is_unfinished_file:
                    print(f"Skipping unfinished file: {file}")  # Feedback
                    continue

                home_files.append((src_path, rel_path, size))
            except FileNotFoundError:
                logging.warning(f"Skipped missing file: {file}")
                print(f"Warning: Skipped missing file: {file}")  # Feedback
                continue
            except Exception as e:
                logging.error(f"Error processing file {file}: {e}")
                print(f"Error processing file {file}: {e}")  # Feedback
                continue


##############################################################################
# Copying Handling
##############################################################################
def copy_file_worker(src: str, dest: str):
    """
    Worker function to copy a file or directory in a separate process.

    Args:
        src (str): Source file path.
        dest (str): Destination file path.
    """
    print(f"Copying from {src} to {dest}")  # Feedback

    try:
        if os.path.isdir(src):
            # If the source is a directory, use shutil.copytree
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            # If the source is a file, use shutil.copy2
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
    except Exception as e:
        logging.error(f"Error copying {src} to {dest}: {e}")
        raise


##############################################################################
# Flatpak Handling
##############################################################################
def backup_flatpaks_names():
    """
    Back up the names of installed Flatpak applications.

    This function retrieves the list of installed Flatpak applications and saves their names
    to a file for backup purposes.
    """
    flatpak_location = server.flatpak_txt_location()
    flatpaks = set()

    try:
        # Ensure the directory for the Flatpak backup file exists
        os.makedirs(os.path.dirname(flatpak_location), exist_ok=True)

        # Retrieve the list of installed Flatpak applications
        with os.popen(server.GET_FLATPAKS_APPLICATIONS_NAME) as flatpak_process:
            flatpak_output = flatpak_process.read()
            if not flatpak_output:
                logging.warning("Flatpak command returned no output. Check if Flatpaks are installed or if the command is correct.")
                return

            # Write the Flatpak names to the backup file
            with open(flatpak_location, 'w') as configfile:
                for flatpak in flatpak_output.splitlines():
                    flatpak_name = flatpak.strip()
                    if flatpak_name:
                        flatpaks.add(flatpak_name)
                        configfile.write(flatpak_name + '\n')

        if flatpaks:
            logging.info(f"Flatpaks installations were backed up: {flatpak_location}")
    except IOError as e:
        logging.error(f"Error backing up Flatpaks installations: {e}")


class Daemon:
    """
    The Daemon class handles the backup process, including file monitoring,
    backup creation, and resuming interrupted backups.
    """
    def __init__(self):
        # Initialize daemon attributes
        self.user_home = os.path.expanduser("~")
        self.previous_files = {}
        self.to_backup = []
        self.failed_backup = []
        self.copied_files = 0
        self.start_time = time.time()
        self.backup_in_progress = False
        self.suspend_flag = False
        self.main_backup_dir = server.main_backup_folder()
        self.updates_backup_dir = server.backup_folder_name()
        self.backup_path_cache = {}
        self.hash_cache = {}
        self.executor = ProcessPoolExecutor()
        self.current_action = "Idle"  # Track the current action

        asyncio.run(self.start_conciderations())
        
    async def start_conciderations(self):
        self.filtered_home = await self.get_filtered_home_files()

    ##############################################################################
    # Signal, Loading and Saving Handling
    ##############################################################################
    def signal_handler(self, signum, frame):
        logging.info(f"Received signal: {signum}. Stopping daemon and saving backup state.")
        self.suspend_flag = True
        if self.backup_in_progress:
            backup_status = '.main_backup' if self.is_backing_up_to_main else 'other backup'
            self.save_backup(backup_status)
        logging.info("System is going to sleep, shut down, restart, PID file do not exist or just terminated. Stopping backup.")
        exit()
    
    def resume_handler(self, signum, frame):
        logging.info(f"Received resume signal: {signum}. Resuming operations.")
        self.suspend_flag = False
    
    async def load_backup(self):
        if os.path.exists(server.INTERRUPTED_MAIN):
            logging.info("Resuming backup to .main_backup from interrupted state.")
            print("Resuming backup to .main_backup from interrupted state.")  # Feedback
            self.is_backing_up_to_main = True
            #filtered_home = await self.get_filtered_home_files()

            for path, rel_path, size in self.filtered_home:
                if not os.path.exists(server.DAEMON_PID_LOCATION):
                    self.signal_handler(signal.SIGTERM, None)
                    return

                dest_path = os.path.join(self.main_backup_dir, rel_path)
                if os.path.exists(dest_path):
                    continue

                print(f"Backing up interrupted file: {path}")  # Feedback
                await self.backup_file(file=path, new_file=True, executor=self.executor)

            logging.info("Successfully backed up to .main.")
            print("Successfully backed up to .main.")  # Feedback
            self.is_backing_up_to_main = False

            if os.path.exists(server.INTERRUPTED_MAIN):
                os.remove(server.INTERRUPTED_MAIN)
                print(f"Removed interrupted file: {server.INTERRUPTED_MAIN}")  # Feedback

    def save_backup(self, process=None):
        logging.info("Saving settings...")
        print("Saving settings...")  # Feedback
        if process == '.main_backup':
            if not os.path.exists(server.INTERRUPTED_MAIN):
                with open(server.INTERRUPTED_MAIN, 'w') as f:
                    f.write('Backup to .main_backup was interrupted.')
                logging.info(f"Created interrupted file: {server.INTERRUPTED_MAIN}")
                print(f"Created interrupted file: {server.INTERRUPTED_MAIN}")  # Feedback
    

    ##############################################################################
    # File Size Handling
    ##############################################################################
    def hash_file_with_cache(self, file_path: str) -> str:
        """
        Generate and cache the hash of a file.

        Args:
            file_path (str): The path to the file to hash.

        Returns:
            str: The SHA-256 hash of the file.
        """
        if file_path in self.hash_cache:
            return self.hash_cache[file_path]
        file_hash = self.hash_file(file_path)
        self.hash_cache[file_path] = file_hash
        return file_hash

    def hash_file(self, file_path: str) -> str:
        """
        Generate the SHA-256 hash of a file.

        Args:
            file_path (str): The path to the file to hash.

        Returns:
            str: The SHA-256 hash of the file.
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


    ##############################################################################
    # Space Handling
    ##############################################################################
    def has_sufficient_space(self, file):
        statvfs = os.statvfs(self.main_backup_dir)
        available_space = statvfs.f_frsize * statvfs.f_bavail
        return os.path.getsize(file) <= available_space


    async def get_filtered_home_files(self):
        """
        Retrieve a list of files in the user's home directory, excluding ignored files
        and hidden files/folders, and optimize by first checking the size of top-level folders
        and their subfolders.

        Returns:
            list: A list of tuples containing file paths, relative paths, and sizes.
        """
        home_files = []
        ignored_folders = load_ignored_folders_from_config()

        # Get the list of top-level folders in the user's home directory
        for entry in os.scandir(server.USER_HOME):
            if entry.name.startswith('.') or entry.name in excluded_dirs:
                continue  # Skip hidden folders and excluded directories

            top_level_folder: str = entry.name
            folder_path: str = entry.path
            backup_folder_path: str = os.path.join(self.main_backup_dir, top_level_folder)

            # Skip ignored folders
            if any(os.path.commonpath([folder_path, ignored_folder]) == ignored_folder for ignored_folder in ignored_folders):
                continue

            # Get the size of the top-level folder and its backup
            current_folder_size = get_top_level_folder_size(folder_path)
            backup_folder_size = get_top_level_folder_size(backup_folder_path) if os.path.exists(backup_folder_path) else 0

            # Compare folder sizes
            if current_folder_size == backup_folder_size:
                print(f"Skipping folder '{top_level_folder}' as its size is unchanged.")  # Feedback
                continue

            print(f"Processing folder '{top_level_folder}' as its size has changed.")  # Feedback

            # Get changed subfolders
            changed_subfolders = get_changed_subfolders(folder_path, backup_folder_path)

            # Process each changed subfolder
            for subfolder_path in changed_subfolders:
                print(f"Processing changed subfolder '{subfolder_path}'...")  # Feedback
                backup_subfolder_path = os.path.join(backup_folder_path, os.path.basename(subfolder_path))
                process_changed_subfolder(subfolder_path, backup_subfolder_path, home_files)

        return home_files
   

    ##############################################################################
    # Backup Handling
    ##############################################################################
    # This function is used to filter and backup Home to backup device folder
    async def make_first_backup(self):
        """
        Perform the first backup by iterating through the user's home directory
        and backing up all files to the main backup directory.

        Args:
            daemon: The Daemon instance to access its methods and attributes.
        """
        try:
            # Update the backup status
            server.write_backup_status('Performing first backup...')
            logging.info("Starting the first backup process.")

            # Create necessary directories
            os.makedirs(self.main_backup_dir, exist_ok=True)
            
            # Retrieve the filetered list of files to back up
            async def filtered_first_backup():
                home_files = []
                ignored_folders = load_ignored_folders_from_config()

                # Get the list of top-level folders in the user's home directory
                for entry in os.scandir(server.USER_HOME):
                    if entry.name.startswith('.') or entry.name in excluded_dirs:
                        continue  # Skip hidden folders and excluded directories

                    folder_path: str = entry.path

                    # Skip ignored folders
                    if any(os.path.commonpath([folder_path, ignored_folder]) == ignored_folder for ignored_folder in ignored_folders):
                        continue
                    
                    home_files.append((folder_path, os.path.relpath(folder_path, server.USER_HOME), os.path.getsize(folder_path)))
                return home_files
            
            filtered_home_files = await filtered_first_backup()

            # Generate a date folder for the backup
            date_folder = datetime.now().strftime("%d-%m-%Y/%H-%M")
            os.makedirs(os.path.join(self.updates_backup_dir, date_folder), exist_ok=True)
            logging.info(f"Generated date folder: {date_folder}")
            print(f"Generated date folder: {date_folder}")  # Feedback

            # Iterate through the files and back them up
            for file_path, rel_path, size in filtered_home_files:
                if not os.path.exists(server.DAEMON_PID_LOCATION):
                    logging.error("PID file missing. Stopping first backup.")
                    print("PID file missing. Stopping first backup.")  # Feedback
                    self.signal_handler(signal.SIGTERM, None)
                    return

                # File already exists in the backup device
                dest_path = os.path.join(self.main_backup_dir, rel_path)
                if os.path.exists(dest_path):
                    logging.info(f"File already exists in backup: {dest_path}")
                    continue

                # No connection to the backup device
                if not has_driver_connection():
                    logging.info("Backup device disconnected. Stopping first backup.")
                    return "Backup device disconnected. Stopping first backup."

                # Back up the file
                await self.backup_file(
                    file=file_path, 
                    new_file=True, 
                    executor=self.executor, 
                    date_folder=None)

            # Update the server with recent backup information
            server.update_recent_backup_information()
            backup_flatpaks_names()  # Backup Flatpak names
            logging.info("First backup completed successfully.")

            # Remove interrupted backup marker if it exists
            if os.path.exists(server.INTERRUPTED_MAIN):
                os.remove(server.INTERRUPTED_MAIN)
                logging.info(f"Removed interrupted backup marker: {server.INTERRUPTED_MAIN}")

        except Exception as e:
            logging.error(f"Error during first backup: {e}")
            print(f"Error during first backup: {e}")  # Feedback
    
    async def backup_file(self, file: str, new_file: bool, executor: ProcessPoolExecutor, progress: int = 0, total_files: int = 0, start_time: float = 0, date_folder: str = None):
        """
        Back up a file to the appropriate backup directory using multiprocessing.

        Args:
            file (str): The path to the file to be backed up.
            new_file (bool): Indicates whether the file is new or an update to an existing file.
            executor (ProcessPoolExecutor): The process pool executor.
            progress (int): The current progress count.
            total_files (int): The total number of files to back up.
            start_time (float): The start time for the progress bar.
            date_folder (str): The date folder for the current backup session.

        Returns:
            str: A message indicating the success or failure of the backup operation.
        """
        self.backup_in_progress = True
        attempt_count = 0
        max_attempts = 5

        while attempt_count < max_attempts:
            attempt_count += 1
            try:
                # Determine the backup file path
                if new_file:
                    backup_file_path = self.get_backup_file_path(file)
                else:
                    # Use the provided date_folder instead of generating a new one
                    #date_folder = datetime.now().strftime("%d-%m-%Y/%H-%M")
                    backup_file_path = self.get_backup_file_path(file, date_folder)

                # Check if there is sufficient space
                if not self.has_sufficient_space(file):
                    print("Insufficient space for backup.")
                    logging.error("Insufficient space for backup.")
                    return "Insufficient space for backup."
                
                server.write_backup_status(f"Backing up: {file}")

                # Copy the file using multiprocessing
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(executor, copy_file_worker, file, backup_file_path)
                #self.generate_folder_log(file)
                
                print(f"Backing up file: {file} to {backup_file_path}")  # Debugging
                logging.info(f"Successfully backed up: {file} to {backup_file_path}")
                return f"Successfully backed up: {file} to {backup_file_path}"

            except Exception as e:
                logging.error(f"Error backing up {file}: {e}")
                if attempt_count >= max_attempts:
                    return f"Failed to back up {file} after {max_attempts} attempts."
    
    def get_backup_file_path(self, file, date_folder=None):
        if file in self.backup_path_cache:
            return self.backup_path_cache[file]

        try:
            relative_path = os.path.relpath(file, self.user_home)
        except ValueError:
            raise ValueError(f"File path '{file}' is not relative to user home '{self.user_home}'.")

        if date_folder:
            path = os.path.join(self.updates_backup_dir, date_folder, relative_path)
        else:
            path = os.path.join(self.main_backup_dir, relative_path)

        self.backup_path_cache[file] = path
        return path

    def file_was_updated(self, file_path: str, rel_path: str):
        """
        Checks if a file has been updated by comparing its size, modification time, and hash with the latest backup.

        Args:
            file_path (str): The path to the file to check.
            rel_path (str): The relative path of the file in the backup directory.

        Returns:
            bool: True if the file has been updated, False otherwise.
        """
        try:
            # Get the current file size and modification time
            current_file_size = os.path.getsize(file_path)
            current_file_mtime = os.path.getmtime(file_path)
            logging.debug(f"Checking file: {file_path}")
            logging.debug(f"Current size: {current_file_size}, Current mtime: {current_file_mtime}")
        except FileNotFoundError:
            logging.warning(f"File not found: {file_path}")
            return False

        # Check the file against all backup dates
        backup_dates = server.has_backup_dates_to_compare()
        if backup_dates:
            for date_folder in backup_dates:
                date_folder_path = os.path.join(server.backup_folder_name(), date_folder)
                if os.path.isdir(date_folder_path):
                    # Sort time folders in reverse chronological order
                    time_folders = sorted(
                        [time_folder for time_folder in os.listdir(date_folder_path) if '-' in time_folder],
                        key=lambda t: datetime.strptime(t, '%H-%M'),
                        reverse=True
                    )

                    # Check the latest time folder
                    for time_folder in time_folders:
                        time_folder_path = os.path.join(date_folder_path, time_folder)

                        # Check if is a directory
                        if os.path.isdir(time_folder_path):
                            updated_file_path = os.path.join(time_folder_path, rel_path)
                            # print(f"Checking updated file: {updated_file_path}")  # Debugging

                            # Compare file with self previous backup version 
                            if os.path.exists(updated_file_path):
                                # Get the backup file size and modification time
                                updated_file_size = os.path.getsize(updated_file_path)
                                updated_file_mtime = os.path.getmtime(updated_file_path)
                                logging.debug(f"Comparing with backup: {updated_file_path}")
                                logging.debug(f"Backup size: {updated_file_size}, Backup mtime: {updated_file_mtime}")

                                # Compare file size
                                if updated_file_size != current_file_size:
                                    print(file_path)
                                    print(updated_file_path)
                                    logging.info("File size mismatch detected.")
                                    print(f"File size mismatch detected. Current: {current_file_size}, Backup: {updated_file_size}")  # Debugging
                                    return True

                                # Compare modification time
                                if updated_file_mtime != current_file_mtime:
                                    logging.info("Modification time mismatch detected.")
                                    print("Modification time mismatch detected.")
                                    return True

                                # Compare file hashes
                                current_file_hash = self.hash_file_with_cache(file_path)
                                updated_file_hash = self.hash_file_with_cache(updated_file_path)

                                print()
                                print()
                                print("-" * 40)
                                print(f"Updated backup file: {updated_file_path}")  # Debugging
                                print(f"Updated backup file size: {updated_file_size}", updated_file_size==current_file_size)  # Debugging
                                print("Updated file mtime:", updated_file_mtime, updated_file_mtime==current_file_mtime)  # Debugging
                                print(updated_file_hash, updated_file_hash==current_file_hash)  # Debugging
                                print()
                                print(f"Current file: {file_path}")  # Debugging
                                print("current_file_size:", current_file_size)  # Debugging
                                print("current_file_mtime:", current_file_mtime)  # Debugging
                                print(current_file_hash)
                                print("-" * 40)

                                logging.debug(f"Current hash: {current_file_hash}, Backup hash: {updated_file_hash}")
                                if updated_file_hash != current_file_hash:
                                    logging.info("Hash mismatch detected.")
                                    return True
                                
                                # If all checks pass, the file is unchanged
                                logging.info(f"File is unchanged in backup folder: {updated_file_path}")
                                return False  # Skip to the next file

        ######################################################################
        # FALLBACK TO MAIN BACKUP
        # If the file is not found in the date folders, compare self file with the main backup
        main_file_path = os.path.join(server.main_backup_folder(), rel_path)
        # print(f"Checking main backup file: {main_file_path}")  # Debugging

        # Check if the main backup file exists
        if os.path.exists(main_file_path):
            main_file_size = os.path.getsize(main_file_path)
            main_file_mtime = os.path.getmtime(main_file_path)
            
            logging.debug(f"Comparing with main backup: {main_file_path}")
            logging.debug(f"Main size: {main_file_size}, Main mtime: {main_file_mtime}")

            # Compare file size
            if main_file_size != current_file_size:
                logging.info("File size mismatch detected in main backup.")
                print("File size mismatch detected in main backup.")
                return True

            # Compare modification time
            if main_file_mtime != current_file_mtime:
                logging.info("Modification time mismatch detected in main backup.")
                print("Modification time mismatch detected in main backup.")
                return True

            # Compare file hashes
            current_file_hash = self.hash_file_with_cache(file_path)
            main_file_hash = self.hash_file_with_cache(main_file_path)
            
            print()
            print()
            print("-" * 40)
            print(f"Main backup file: {main_file_path}")  # Debugging
            print(f"Main backup file size: {main_file_size}")  # Debugging
            print("Main_file_mtime:", main_file_mtime)  # Debugging
            print(main_file_hash)
            print()
            print(f"Current file: {file_path}")  # Debugging
            print("current_file_mtime:", current_file_size)  # Debugging
            print("current_file_size:", current_file_mtime)  # Debugging
            print(current_file_hash)
            print("-" * 40)

            logging.debug(f"Current hash: {current_file_hash}, Main backup hash: {main_file_hash}")
            if main_file_hash != current_file_hash:
                logging.info("Hash mismatch detected in main backup.")
                print("Hash mismatch detected in main backup.")
                return True

        # If the file is not found in any backup location, assume it has not been updated
        logging.info(f"File is unchanged: {file_path}")
        print("File is unchanged:", file_path)  # Debugging
        return False
    

    ##############################################################################
    # Start Daemon
    ##############################################################################
    async def run_backup_cycle(self):
        checked_for_first_backup = False
        connection_logged: bool = False

        try:
            await self.load_backup()

            while True:
                if not os.path.exists(server.DAEMON_PID_LOCATION):
                    logging.error("PID file missing. Daemon requires exit.")
                    print("PID file missing. Daemon requires exit.")  # Feedback
                    self.signal_handler(signal.SIGTERM, None)
                    return

                # Has connection to the backup device
                if has_driver_connection():
                    if not connection_logged:
                        logging.info("Connection established to backup device.")
                        connection_logged = True

                    # First Backup Checker
                    if not checked_for_first_backup and server.is_first_backup():
                        await self.make_first_backup()
                        checked_for_first_backup = True

                    # Analyse for New/Updated Files
                    await self.process_backups()
                else:
                    self.backup_in_progress = False

                    if connection_logged:
                        if self.is_backing_up_to_main:
                            self.save_backup('.main_backup')

                        logging.info("Waiting for connection to backup device...")
                        connection_logged = False

                # server.write_backup_status(f'Sleeping for: {WAIT_TIME} minute(s)')
                logging.info(f'Resting for: {WAIT_TIME * 60} seconds')
                print(f"Resting for: {WAIT_TIME * 60} seconds")
                await asyncio.sleep(WAIT_TIME * 60)

        except Exception as e:
            logging.error(f"Error: {e}")
            print(f"Error: {e}")  # Feedback

    async def process_backups(self):
        tasks = []
        executor = ProcessPoolExecutor()
        progress = 0  # Track the number of files processed
        start_time = time.time()  # Track the start time for the progress bar
        batch_size = 10  # Number of files to process in each batch
        #date_folder_was_created: bool = False  # Flag to check if the date folder was created
        date_folder: bool = None  # Defer creation of the date folder

        logging.info("Processing backups...")

        try:
            total_files = len(self.filtered_home)  # Total number of files to back up

            print("-" * 40)
            print(f"Total files to back up: {total_files}")  # Feedback
            print("-" * 40)

            # Generate the date folder once for the entire backup session
            date_folder = datetime.now().strftime("%d-%m-%Y/%H-%M")
            os.makedirs(os.path.join(self.updates_backup_dir, date_folder), exist_ok=True)  # Ensure the folder is created
            print(f"Generated date folder: {date_folder}")  # Debugging

            # Split files into batches
            for i in range(0, total_files, batch_size):
                batch = self.filtered_home[i:i + batch_size]
                for file_path, rel_path, size in batch:  # file_path = Home file path
                    try:
                        # # This is used to check if file exists in the main backup folder
                        modded_main_file_path = os.path.join(self.main_backup_dir, os.path.relpath(file_path, server.USER_HOME))
                        if not os.path.exists(server.DAEMON_PID_LOCATION):
                            logging.warning("PID file missing. Stopping backup process.")
                            self.signal_handler(signal.SIGTERM, None)
                            return

                        # Detection for New/Updated Files
                        if not os.path.exists(modded_main_file_path):
                            logging.info(f"New file: {file_path}")
                            tasks.append(
                                self.backup_file(
                                    file_path, 
                                    new_file=True, 
                                    executor=executor, 
                                    progress=progress, 
                                    total_files=total_files, 
                                    start_time=start_time,
                                    date_folder=None))
                        elif self.file_was_updated(file_path, rel_path):
                            logging.info(f"Updated file: {file_path}")
                            
                            # # A date folder was not already created
                            # if not date_folder_was_created:
                            #     date_folder_was_created = True  # Set the flag to True
                            #     date_folder = datetime.now().strftime("%d-%m-%Y/%H-%M")
                            #     os.makedirs(os.path.join(self.updates_backup_dir, date_folder), exist_ok=True)
                            #     print(f"Generated date folder: {date_folder}")  # Debugging

                            tasks.append(
                                self.backup_file(
                                    file_path, 
                                    new_file=False, 
                                    executor=executor, 
                                    progress=progress, 
                                    total_files=total_files, 
                                    start_time=start_time,
                                    date_folder=date_folder))

                    except Exception as file_error:
                        logging.error(f"Error processing file {file_path}: {file_error}")
                        print(f"Error processing file {file_path}: {file_error}")  # Feedback

                # Process the current batch
                if tasks:
                    print()
                    print("-" * 40)
                    print(f"Processing batch of {len(batch)} files...")  # Feedback
                    await asyncio.gather(*tasks)
                    tasks = []  # Clear tasks for the next batch

            server.update_recent_backup_information()
            logging.info("Backup tasks completed successfully")
            #date_folder_was_created = False  # Reset the date folder creation flag

        except Exception as e:
            logging.error(f"Error in process_backups: {e}")
            print(f"Error in process_backups: {e}")  # Feedback
        finally:
            executor.shutdown()
            print("Backup process completed.")  # Feedback


if __name__ == "__main__":
    server = SERVER()
    daemon = Daemon()
        
    server.setup_logging()
    setproctitle.setproctitle(f'{server.APP_NAME} - daemon')

    signal.signal(signal.SIGTERM, daemon.signal_handler)
    signal.signal(signal.SIGINT, daemon.signal_handler)
    signal.signal(signal.SIGCONT, daemon.resume_handler)

    logging.info("Starting file monitoring...")
    asyncio.run(daemon.run_backup_cycle())
