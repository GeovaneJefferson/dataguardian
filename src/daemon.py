from concurrent.futures import ThreadPoolExecutor
from has_driver_connection import has_driver_connection
from server import *
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WAIT_TIME = 5  # Minutes between backup checks

# Concurrency settings for copying files
# Default, can be adjusted based on system resources and current load
DEFAULT_COPY_CONCURRENCY = 2


def compute_folder_metadata(folder_path, excluded_dirs=None, excluded_exts=None):
    """Compute total size, file count, and latest modification time for a folder."""
    total_size = 0
    latest_mtime = 0
    total_files = 0

    excluded_dirs = excluded_dirs or set()
    excluded_exts = excluded_exts or set()

    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in excluded_dirs]
        for f in files:
            if f.startswith('.') or any(f.endswith(ext) for ext in excluded_exts):
                continue
            try:
                full_path = os.path.join(root, f)
                stat = os.stat(full_path)
                total_size += stat.st_size
                if stat.st_mtime > latest_mtime:
                    latest_mtime = stat.st_mtime
                total_files += 1
            except Exception:
                pass  # Skip unreadable files

    return {
        "path": folder_path, # Store the path for which metadata was computed
        "computed_at": time.time(), # Timestamp of when this metadata was computed
        # Consider adding a hash of file list and their mtimes for more robust change detection
        "total_files": total_files,
        "total_size": total_size,
        "latest_mtime": latest_mtime
    }

def send_to_ui(message: str):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(server.SOCKET_PATH)
        sock.sendall(message.encode("utf-8"))
        sock.close()
    except Exception:
        pass  # UI might not be running, ignore

class DownloadsEventHandler(FileSystemEventHandler):
    def __init__(self, daemon_instance):
        super().__init__()
        self.daemon = daemon_instance
        # Ensure user_home is correctly referenced from the daemon instance
        self.downloads_path = os.path.join(self.daemon.user_home, "Downloads")

    def on_created(self, event):
        if event.is_directory:
            return

        src_path = event.src_path
        # Check if the event is within the Downloads folder
        # and not a subdirectory (recursive=False for observer)
        if os.path.dirname(src_path) != self.downloads_path:
            return

        filename = os.path.basename(src_path)
        if filename.endswith((".deb", ".rpm")):
            logging.info(f"Watchdog: Detected new package in Downloads: {src_path}")
            if hasattr(self.daemon, 'loop') and self.daemon.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.daemon._handle_downloaded_package(src_path),
                    self.daemon.loop
                )
            else:
                logging.warning("Daemon event loop not available for handling downloaded package from watchdog.")
class Daemon:
    ############################################################################
    # INITIALIZATION AND CONFIGURATION
    ############################################################################
    def __init__(self):  # NONSONAR 
        """Initialize the daemon with necessary configurations and signal handlers."""
        # Determine copy concurrency based on CPU cores and current load
        try:
            cpu_cores = os.cpu_count()
            # Get a snapshot of CPU utilization over a short interval
            # interval=None would be non-blocking but might give the load since last call or system boot,
            # interval=0.1 gives a more current snapshot.
            cpu_load = psutil.cpu_percent(interval=0.1)

            HIGH_CPU_THRESHOLD = 75.0  # Percent, e.g., if CPU is over 75% busy
            # When CPU is high, use a very conservative concurrency, e.g., 1 or 2, or a small fraction of cores
            LOW_CONCURRENCY_ON_HIGH_LOAD = max(1, (cpu_cores // 4) if cpu_cores else 1)

            if cpu_load > HIGH_CPU_THRESHOLD:
                self.copy_concurrency = LOW_CONCURRENCY_ON_HIGH_LOAD
                logging.info(
                    f"High CPU load ({cpu_load}%) detected. "
                    f"Setting COPY_CONCURRENCY to a conservative {self.copy_concurrency}."
                )
            else:
                # Use between 1 and 8 (configurable max), based on cores, but not more than available cores.
                # If cpu_cores is None, it defaults to DEFAULT_COPY_CONCURRENCY
                self.copy_concurrency = max(1, min(cpu_cores if cpu_cores else DEFAULT_COPY_CONCURRENCY, 8))
                logging.info(
                    f"CPU load ({cpu_load}%) is moderate. "
                    f"Setting COPY_CONCURRENCY to {self.copy_concurrency} based on {cpu_cores or 'default'} CPU cores."
                )
        except Exception as e:
            logging.warning(
                f"Could not determine CPU cores/load, defaulting COPY_CONCURRENCY to {DEFAULT_COPY_CONCURRENCY}. Error: {e}"
            )
            self.copy_concurrency = DEFAULT_COPY_CONCURRENCY

        self.user_home = server.USER_HOME

        self.excluded_dirs = {'__pycache__', 'snap'}
        self.excluded_exts = {'.crdownload', '.part', '.tmp'}

        self.ignored_folders = set(os.path.abspath(p) for p in server.load_ignored_folders_from_config())

        self.main_backup_dir = server.main_backup_folder()
        self.update_backup_dir = server.backup_folder_name()
        self.interruped_main_file = server.get_interrupted_main_file()

        self.executor = ThreadPoolExecutor(max_workers=self.copy_concurrency)
        self.copy_semaphore = asyncio.Semaphore(self.copy_concurrency)

        self.backup_in_progress = False
        self.suspend_flag = False
        self.should_exit = False
        self.had_writability_issue = False # Tracks if a writability issue was logged
        self.downloads_observer = None # For watchdog

    ############################################################################
    # SIGNAL HANDLING
    ############################################################################
    def signal_handler(self, signum, frame):
        if signum == signal.SIGTSTP:
            logging.info(f"Received SIGTSTP (suspend), pausing daemon...")
            self.suspend_flag = True
        else:
            logging.info(f"Received termination signal {signum}, stopping daemon...")
            self.suspend_flag = True
            if self.downloads_observer:
                self.downloads_observer.stop()
                # self.downloads_observer.join() # Join in cleanup or finally
            # self.executor.shutdown(wait=False) # Consider graceful shutdown for executor
            self.should_exit = True
    
    def resume_handler(self, signum, frame):
        logging.info(f"Received resume signal {signum}, resuming operations.")
        self.suspend_flag = False

    ############################################################################
    # BACKUP LOCATION AND PERMISSIONS
    ############################################################################
    def is_backup_location_writable(self) -> bool:
        """Checks if the base backup folder is writable."""
        base_path = server.create_base_folder()
        # Check if the path itself can be formed (e.g. DRIVER_LOCATION is set)
        if not base_path:
            logging.error("Backup base path is not configured (DRIVER_LOCATION might be empty). Cannot check writability.")
            return False

        if not os.path.exists(base_path):
            try:
                os.makedirs(base_path, exist_ok=True)
            except OSError as e:
                logging.error(f"Backup base path {base_path} does not exist and cannot be created: {e}")
                return False
        
        test_file_path = os.path.join(base_path, ".writetest.tmp")
        try:
            with open(test_file_path, "w") as f:
                f.write("test")
            os.remove(test_file_path)
            return True
        except OSError as e:
            logging.error(f"Backup location {base_path} is not writable: {e}")
            return False

    ############################################################################
    # FILE HASHING AND COMPARISON
    ############################################################################
    def file_hash(self, path: str) -> str:
        """Compute SHA-256 hash of a file."""
        try:
            h = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            logging.error(f"Hash error: {path}: {e}")
            return ""

    def file_was_updated(self, src: str, rel_path: str) -> bool:
        """Check if a file differs from its backup versions."""
        try:
            current_stat = os.stat(src)
        except FileNotFoundError: #NOSONAR
            logging.warning(f"File '{rel_path}' not found at source '{src}'. Cannot compare.")
            return False
        # Add a src_hash_cache to avoid re-calculating hash for the same source file

        backup_dates = server.has_backup_dates_to_compare()
        for date_folder in backup_dates:
            try:
                datetime.strptime(date_folder, "%d-%m-%Y")
            except ValueError:
                continue

            date_path = os.path.join(self.update_backup_dir, date_folder)
            if not os.path.isdir(date_path):
                continue

            time_folders = []
            for t in os.listdir(date_path):
                try:
                    datetime.strptime(t, '%H-%M')
                    full_time_path = os.path.join(date_path, t)
                    if os.path.isdir(full_time_path):
                        time_folders.append(t)
                except ValueError:
                    continue

            time_folders.sort(reverse=True)

            for time_folder in time_folders:
                backup_file_path = os.path.join(date_path, time_folder, rel_path)
                if os.path.exists(backup_file_path):
                    try:
                        b_stat = os.stat(backup_file_path)
                        if b_stat.st_size != current_stat.st_size or abs(b_stat.st_mtime - current_stat.st_mtime) > 1:
                            # logging.info(f"File '{rel_path}' updated (size/mtime mismatch with incremental backup {backup_file_path}). Src size: {current_stat.st_size}, Dst size: {b_stat.st_size}. Src mtime: {current_stat.st_mtime}, Dst mtime: {b_stat.st_mtime}")
                            return True
                        if self.file_hash(src) != self.file_hash(backup_file_path):
                            # logging.info(f"File '{rel_path}' updated (hash mismatch with incremental backup {backup_file_path}).")
                            return True
                        return False
                    except Exception as e:
                        # logging.warning(f"Error comparing '{src}' with incremental backup '{backup_file_path}': {e}. Trying older versions or main.")
                        continue

        main_path = os.path.join(self.main_backup_dir, rel_path)
        if os.path.exists(main_path):
            try:
                b_stat = os.stat(main_path)
                if b_stat.st_size != current_stat.st_size or abs(b_stat.st_mtime - current_stat.st_mtime) > 1:
                    # logging.info(f"File '{rel_path}' updated (size/mtime mismatch with main backup {main_path}). Src size: {current_stat.st_size}, Dst size: {b_stat.st_size}. Src mtime: {current_stat.st_mtime}, Dst mtime: {b_stat.st_mtime}")
                    return True
                if self.file_hash(src) != self.file_hash(main_path):
                    # logging.info(f"File '{rel_path}' updated (hash mismatch with main backup {main_path}).")
                    return True
                return False # Explicitly return False if it matches the main backup
            except Exception as e:
                # logging.warning(f"Error comparing '{src}' with main backup '{main_path}': {e}. Assuming update needed.")
                return True
            
        # If no backup (main or incremental) exists, or if main backup comparison failed, it's considered new/updated.
        logging.info(f"File '{rel_path}' is new or no existing valid backup was definitively matched. Marking for backup.")
        return True # Default to True if no existing backup is found or if errors occurred in main comparison

    ############################################################################
    # FILE COPYING (CORE BACKUP LOGIC)
    ############################################################################
    async def copy_file(self, src: str, dst: str, rel_path: str):
        async with self.copy_semaphore:
            file_id = rel_path  # Use rel_path as a unique ID for the UI
            filename = os.path.basename(src)
            total_size_bytes = 0
            human_readable_size = "N/A"

            try:
                total_size_bytes = os.path.getsize(src)
                human_readable_size = server.get_item_size(src, True)
            except OSError as e:
                logging.error(f"Cannot get size of {src}: {e}")
                error_msg = {"id": file_id, "filename": filename, "size": human_readable_size, "eta": "error", "progress": 0.0, "error": f"Cannot access file: {e}"}
                send_to_ui(json.dumps(error_msg))
                return

            # Check for sufficient disk space
            threshold_bytes = 2 * 1024 * 1024 * 1024  # 2 GB
            try:
                _, _, device_free_size = shutil.disk_usage(server.DRIVER_LOCATION)
                if device_free_size <= (total_size_bytes + threshold_bytes):
                    logging.warning(f"Not enough space to backup: {src}. Required: {total_size_bytes}, Free: {device_free_size}")
                    error_msg = {"id": file_id, "filename": filename, "size": human_readable_size, "eta": "no space", "progress": 0.0, "error": "Not enough disk space"}
                    send_to_ui(json.dumps(error_msg))
                    return
            except Exception as e:
                logging.error(f"Error checking disk space: {e}")
                error_msg = {"id": file_id, "filename": filename, "size": human_readable_size, "eta": "error", "progress": 0.0, "error": f"Disk check failed: {e}"}
                send_to_ui(json.dumps(error_msg))
                return

            os.makedirs(os.path.dirname(dst), exist_ok=True)
            loop = asyncio.get_event_loop()
            tmp_dst = dst + ".tmp"

            copied_bytes = 0
            start_time = time.time()
            last_update_time = start_time
            prev_progress = -0.01 # Ensure first update is sent

            # Send initial progress
            initial_msg = {
                "type": "transfer_progress",
                "id": file_id,
                "filename": filename,
                "size": human_readable_size,
                "eta": "calculating...",
                "progress": 0.0
            }
            send_to_ui(json.dumps(initial_msg))

            try:
                with open(src, 'rb') as fsrc, open(tmp_dst, 'wb') as fdst:
                    while True:
                        if self.should_exit or self.suspend_flag:
                            logging.info(f"Copy of {src} interrupted or suspended.")
                            if os.path.exists(tmp_dst): os.remove(tmp_dst)
                            # Optionally send a "cancelled" or "paused" status to UI
                            return

                        chunk = await loop.run_in_executor(self.executor, fsrc.read, 8192 * 16) # 128KB chunk
                        if not chunk:
                            break
                        await loop.run_in_executor(self.executor, fdst.write, chunk)
                        copied_bytes += len(chunk)
                        
                        progress = copied_bytes / total_size_bytes if total_size_bytes > 0 else 1.0
                        
                        current_time = time.time()
                        if progress > prev_progress + 0.01 or current_time - last_update_time > 0.5: # Update every 1% or 0.5s
                            elapsed_time = current_time - start_time
                            eta_str = "calculating..."
                            if progress > 0.001 and elapsed_time > 0.1:
                                bytes_per_second = copied_bytes / elapsed_time
                                if bytes_per_second > 0:
                                    remaining_bytes = total_size_bytes - copied_bytes
                                    remaining_seconds = remaining_bytes / bytes_per_second if remaining_bytes > 0 else 0
                                    eta_str = f"{int(remaining_seconds // 60)}m {int(remaining_seconds % 60)}s"
                                else:
                                    eta_str = "stalled"
                            
                            progress_msg = {
                                "type": "transfer_progress",
                                "id": file_id, 
                                "filename": filename, 
                                "size": human_readable_size, 
                                "eta": eta_str, "progress": progress}
                            send_to_ui(json.dumps(progress_msg))
                            prev_progress = progress
                            last_update_time = current_time

                with open(tmp_dst, 'rb') as f_tmp_for_fsync:
                    await loop.run_in_executor(self.executor, os.fsync, f_tmp_for_fsync.fileno())

                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.replace(tmp_dst, dst)
                # Preserve metadata (including mtime) from src to dst
                await loop.run_in_executor(self.executor, shutil.copystat, src, dst)

                logging.info(f"Backed up: {src} -> {dst}")
                final_msg = {
                    "type": "transfer_progress",
                    "id": file_id, 
                    "filename": filename, 
                    "size": human_readable_size, 
                    "eta": "done", "progress": 1.0}
                send_to_ui(json.dumps(final_msg))
            except Exception as e:
                logging.error(f"Error copying {src} -> {dst}: {e}")
                try:
                    if os.path.exists(tmp_dst):
                        os.remove(tmp_dst)
                except Exception:
                    pass
                error_msg = {
                    "type": "transfer_progress", # Or a dedicated "transfer_error" type
                    "id": file_id,
                    "filename": filename,
                    "size": human_readable_size,
                    "eta": "error",
                    "progress": prev_progress if prev_progress > 0 else 0.0,
                    "error": str(e)}
                send_to_ui(json.dumps(error_msg))

    async def _backup_package_file(self, src_path: str, dest_folder: str):
        """Backs up a package file from Downloads to the specified destination folder."""
        filename = os.path.basename(src_path)
        dest_path = os.path.join(dest_folder, filename)
        try:
            # Ensure the destination directory exists
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: os.makedirs(dest_folder, exist_ok=True)
            )
            # Copy the file
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: shutil.copy2(src_path, dest_path)  # copy2 preserves metadata
            )
            logging.info(f"Backed up downloaded package: {src_path} -> {dest_path}")
        except Exception as e:
            logging.error(f"Error backing up downloaded package {src_path} to {dest_path}: {e}")

    async def _handle_downloaded_package(self, src_path: str):
        """Handles a .deb or .rpm file detected in the Downloads folder."""
        if not os.path.isfile(src_path): # Ensure it's a file and still exists
            return

        filename = os.path.basename(src_path)
        dest_folder = None
        if filename.endswith(".deb"): dest_folder = server.deb_main_folder()
        elif filename.endswith(".rpm"): dest_folder = server.rpm_main_folder()

        if dest_folder and server.DRIVER_LOCATION and self.is_backup_location_writable():
            await self._backup_package_file(src_path, dest_folder)
        elif not dest_folder: logging.debug(f"File {filename} is not a .deb or .rpm package. Ignoring.")
        elif not server.DRIVER_LOCATION: logging.warning(f"Backup driver location not set. Cannot backup {filename}.")
        elif not self.is_backup_location_writable(): logging.warning(f"Backup location not writable. Cannot backup {filename}.")

    ############################################################################
    # FOLDER METADATA HANDLING
    ############################################################################
    def load_folder_metadata(self, top_rel_path):
        meta_path = os.path.join(self.main_backup_dir, top_rel_path, '.backup_meta.json')
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r') as f:
                    data = json.load(f)
                return data
            except Exception:
                pass
        return {}
    
    def save_folder_metadata(self, top_rel_path, metadata):
        meta_path = os.path.join(self.main_backup_dir, top_rel_path, '.backup_meta.json')
        try:
            os.makedirs(os.path.dirname(meta_path), exist_ok=True)

            with tempfile.NamedTemporaryFile('w', delete=False, dir=os.path.dirname(meta_path)) as tmpf:
                json.dump(metadata, tmpf, indent=4) # Added indent for readability
                temp_path = tmpf.name
            # Ensure data is written to disk before replacing
            # For NamedTemporaryFile, flush and fsync can be explicit if needed,
            # but os.replace is atomic on POSIX if src and dst are on the same filesystem.
            os.replace(temp_path, meta_path)
        except OSError as e:
            logging.error(f"OSError while saving folder metadata for {top_rel_path} at {meta_path}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while saving folder metadata for {top_rel_path} at {meta_path}: {e}")
        
    def folder_needs_check(self, rel_folder, current_meta, cached_meta):
        cached = cached_meta.get(rel_folder)
        if cached is None:
            return True
        for key in ('total_files', 'total_size', 'latest_mtime'):
            cached_val = cached.get(key)
            current_val = current_meta.get(key)
            if cached_val != current_val:
                return True
        return False
    
    ############################################################################
    # MAIN BACKUP PROCESS
    ############################################################################
    async def scan_and_backup(self):
        tasks = []
        now = datetime.now()
        date_str = now.strftime('%d-%m-%Y')
        time_str = now.strftime('%H-%M')
        session_backup_dir = os.path.join(self.update_backup_dir, date_str, time_str)

        # Reload ignored folders and hidden items preference at the start of each scan
        self.ignored_folders = set(os.path.abspath(p) for p in server.load_ignored_folders_from_config())
        exclude_hidden_master_switch = server.get_database_value(section='EXCLUDE', option='exclude_hidden_itens')
        if exclude_hidden_master_switch is None: # Default to True if not set
            exclude_hidden_master_switch = True

        try:
            with open(self.interruped_main_file, 'w') as f:
                f.write("interrupted")
        except OSError as e:
            logging.error(f"Could not write to interrupted_main_file {self.interruped_main_file}: {e}. "
                          "Backup may not resume correctly if interrupted again. "
                          "This may indicate a read-only filesystem.")
            # Depending on severity, might return or raise to stop the backup cycle
        for entry in os.scandir(self.user_home):
            if (exclude_hidden_master_switch and entry.name.startswith('.')) or \
               entry.name in self.excluded_dirs:
                continue

            src_path = entry.path
            top_level_rel_path = os.path.relpath(src_path, self.user_home)

            # Skip ignored folders
            if any(os.path.commonpath([src_path, ign]) == ign for ign in self.ignored_folders):
                continue

            if entry.is_dir():
                cached_meta = self.load_folder_metadata(top_level_rel_path)
                new_meta = {}

                for root, dirs, files_in_dir in os.walk(src_path): # Renamed 'files' to 'files_in_dir'
                    # Filter directories based on hidden status and excluded_dirs
                    dirs[:] = [d for d in dirs if not ((exclude_hidden_master_switch and d.startswith('.')) or \
                                                       d in self.excluded_dirs)]
                    send_to_ui(json.dumps({
                        "type": "scanning",
                        "folder": os.path.relpath(root, self.user_home).replace("\\", "/")
                    }))
                    subfolder_key = os.path.relpath(root, src_path).replace("\\", "/")
        
                    current_meta = compute_folder_metadata(
                        root,
                        excluded_dirs=self.excluded_dirs,
                        excluded_exts=self.excluded_exts
                    )
                    new_meta[subfolder_key] = current_meta

                    if not self.folder_needs_check(subfolder_key, current_meta, cached_meta):
                        continue

                    for f_in_dir_loop in files_in_dir: # Renamed 'f' to avoid conflict
                        if (exclude_hidden_master_switch and f_in_dir_loop.startswith('.')) or \
                           any(f_in_dir_loop.endswith(ext) for ext in self.excluded_exts):
                            continue

                        fsrc_loop = os.path.join(root, f_in_dir_loop)
                        frel_loop = os.path.relpath(fsrc_loop, self.user_home)
                        main_path_loop = os.path.join(self.main_backup_dir, frel_loop)

                        if not os.path.exists(main_path_loop):
                            tasks.append(self.copy_file(fsrc_loop, main_path_loop, frel_loop))
                        elif self.file_was_updated(fsrc_loop, frel_loop):
                            session_backup_path_loop = os.path.join(session_backup_dir, frel_loop)
                            tasks.append(self.copy_file(fsrc_loop, session_backup_path_loop, frel_loop))

                self.save_folder_metadata(top_level_rel_path, new_meta)
            
            elif entry.is_file():
                # This is a top-level file in user_home
                fsrc = src_path 
                frel = top_level_rel_path # Relative path of the top-level file

                # Apply hidden/excluded extension checks for top-level files
                if (exclude_hidden_master_switch and entry.name.startswith('.')) or \
                   any(entry.name.endswith(ext) for ext in self.excluded_exts):
                    continue
                
                main_path = os.path.join(self.main_backup_dir, frel)

                if not os.path.exists(main_path):
                    tasks.append(self.copy_file(fsrc, main_path, frel))
                elif self.file_was_updated(fsrc, frel):
                    session_backup_path = os.path.join(session_backup_dir, frel)
                    tasks.append(self.copy_file(fsrc, session_backup_path, frel))
    
        if tasks:
            await asyncio.gather(*tasks)
            server.update_recent_backup_information()
            # After backup tasks are complete, generate the summary
            try:
                sub.run(['python3', os.path.join(os.path.dirname(__file__), 'generate_backup_summary.py')], check=True)
            except Exception as e:
                logging.error(f"Failed to generate backup summary: {e}")
            logging.info("Backup session complete.")
        
        try:
            if os.path.exists(self.interruped_main_file):
                os.remove(self.interruped_main_file)
        except OSError as e:
            logging.error(f"Could not remove interrupted_main_file {self.interruped_main_file}: {e}. "
                          "This may indicate a read-only filesystem.")
        
        # Cleanup empty incremental folders
        if os.path.exists(session_backup_dir): # Check if session_backup_dir was even created
            self._cleanup_empty_incremental_folders(session_backup_dir)

    ############################################################################
    # CLEANUP OF EMPTY INCREMENTAL FOLDERS
    ############################################################################
    def _cleanup_empty_incremental_folders(self, session_backup_dir: str):
        """
        Removes the session backup directory if it's empty.
        Also removes the parent date directory if it becomes empty as a result.
        """
        try:
            if not os.listdir(session_backup_dir): # Check if HH-MM folder is empty
                logging.info(f"Removing empty incremental session folder: {session_backup_dir}")
                os.rmdir(session_backup_dir)

                # Check and remove parent date folder if it's now empty
                date_dir = os.path.dirname(session_backup_dir)
                if os.path.exists(date_dir) and not os.listdir(date_dir):
                    logging.info(f"Removing empty incremental date folder: {date_dir}")
                    os.rmdir(date_dir)
            # else:
                # logging.info(f"Incremental session folder {session_backup_dir} is not empty.")
        except OSError as e:
            logging.error(f"Error during cleanup of empty incremental folders for {session_backup_dir}: {e}")

    ############################################################################
    # INTERRUPTION HANDLING
    ############################################################################
    async def resume_from_interruption(self):
        if os.path.exists(self.interruped_main_file):
            logging.info("Interrupted backup session file found.")
            if self.is_backup_location_writable():
                logging.info("Backup location is writable. Attempting to resume interrupted backup...")
                await self.scan_and_backup() 
            else:
                logging.warning("Backup location not writable. Cannot resume interrupted backup at this time. Will retry later.")

    ############################################################################
    # DAEMON MAIN RUN LOOP
    ############################################################################
    async def run(self):
        self.loop = asyncio.get_running_loop() # Store the loop for threadsafe calls
        await self.resume_from_interruption()
        shutdown_event = asyncio.Event()

        def stop_loop(signum, frame):
            self.signal_handler(signum, frame)
            shutdown_event.set()

        signal.signal(signal.SIGTERM, stop_loop)
        signal.signal(signal.SIGINT, stop_loop)
        signal.signal(signal.SIGTSTP, self.signal_handler)  # Suspend (Ctrl+Z)
        signal.signal(signal.SIGCONT, self.resume_handler)  # Resume

        logging.info("Starting scan and backup...")

        # Start Downloads watchdog observer
        downloads_path = os.path.join(self.user_home, "Downloads")
        if os.path.exists(downloads_path):
            event_handler = DownloadsEventHandler(self)
            self.downloads_observer = Observer()
            self.downloads_observer.schedule(event_handler, downloads_path, recursive=False)
            self.downloads_observer.start()
            logging.info(f"Started watchdog for Downloads folder: {downloads_path}")
        else:
            logging.warning(f"Downloads folder not found: {downloads_path}. Watchdog not started.")

        while not self.should_exit:
            if self.suspend_flag:
                logging.info("Daemon suspended... sleeping.")
                await asyncio.sleep(5)
                continue

            if not os.path.exists(server.DAEMON_PID_LOCATION): # Check if daemon should still be running
                logging.warning("Daemon PID file not found. Shutting down.")
                self.signal_handler(signal.SIGTERM, None)
                break

            if has_driver_connection():
                if self.is_backup_location_writable():
                    # Reset a flag indicating writability issue if it was set
                    self.had_writability_issue = False
                    await self.scan_and_backup()
                else:
                    # Log critical only if this is a new or persistent issue
                    if not getattr(self, "had_writability_issue", False):
                        logging.critical(f"[CRITICAL]: Backup location {server.create_base_folder()} is not writable. Automatic backups will be disabled by the UI if running.")
                        self.had_writability_issue = True # Set flag to avoid repeated critical logs for the same issue in one session
                    else:
                        logging.error(f"Backup location {server.create_base_folder()} is still not writable. Skipping backup cycle.")
            else:
                logging.info("Backup drive not connected. Skipping backup cycle.")
                if getattr(self, "had_writability_issue", False): # Reset if drive disconnected
                    self.had_writability_issue = False

            logging.debug(f"Waiting for {WAIT_TIME} minutes before next cycle.")
            total_wait = WAIT_TIME * 60
            interval = 1
            elapsed = 0
            
            while elapsed < total_wait and not self.should_exit:
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
                    break
                except asyncio.TimeoutError:
                    elapsed += interval
            
            # Check if auto backup is still enabled
            auto_backup_enabled = server.get_database_value('BACKUP', 'automatically_backup')
            if str(auto_backup_enabled).lower() != 'true':
                logging.info("Automatic backup is disabled in configuration. Daemon initiated by auto-start will shut down.")
                self.signal_handler(signal.SIGTERM, None) # Trigger shutdown
                break # Exit the loop

        # Cleanup observer
        if self.downloads_observer and self.downloads_observer.is_alive():
            self.downloads_observer.stop()
            self.downloads_observer.join()
            logging.info("Stopped watchdog for Downloads folder.")
        self.executor.shutdown(wait=True) # Ensure executor tasks complete
################################################################################
# MAIN EXECUTION BLOCK
################################################################################
if __name__ == "__main__":
    server = SERVER()

    # Ensure the directory for the log file exists, attempt to create if not.
    # This is important if DRIVER_LOCATION is initially unavailable.
    log_file_path = server.get_log_file_path()
    # if os.path.exists(log_file_path): # Optional: remove old log on start
    #     os.remove(log_file_path)
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True) 
    
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    setproctitle.setproctitle(f'{server.APP_NAME} - daemon')

    try:
        daemon = Daemon()
        asyncio.run(daemon.run())
    except Exception as e:
        logging.error(f"Daemon exception: {e}")
    finally:
        logging.info("Daemon shutting down.")