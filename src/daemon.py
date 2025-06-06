from concurrent.futures import ProcessPoolExecutor
from has_driver_connection import has_driver_connection
from server import *

WAIT_TIME = 5  # Minutes between backup checks
COPY_CONCURRENCY = 4  # Max parallel copy tasks


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
        "total_files": total_files,
        "total_size": total_size,
        "latest_mtime": latest_mtime
    }


class Daemon:
    def __init__(self):
        self.user_home = server.USER_HOME

        self.executor = ProcessPoolExecutor(max_workers=COPY_CONCURRENCY)
        self.copy_semaphore = asyncio.Semaphore(COPY_CONCURRENCY)

        self.excluded_dirs = {'__pycache__', 'snap'}
        self.excluded_exts = {'.crdownload', '.part', '.tmp'}

        self.ignored_folders = set(os.path.abspath(p) for p in server.load_ignored_folders_from_config())

        self.main_backup_dir = server.main_backup_folder()
        self.update_backup_dir = server.backup_folder_name()

        self.backup_in_progress = False
        self.suspend_flag = False
        self.should_exit = False

    def signal_handler(self, signum, frame):
        if signum == signal.SIGTSTP:
            logging.info(f"Received SIGTSTP (suspend), pausing daemon...")
            self.suspend_flag = True
        else:
            logging.info(f"Received termination signal {signum}, stopping daemon...")
            self.suspend_flag = True
            self.should_exit = True
    
    def resume_handler(self, signum, frame):
        logging.info(f"Received resume signal {signum}, resuming operations.")
        self.suspend_flag = False

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
        except FileNotFoundError:
            return False

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
                            return True
                        if self.file_hash(src) != self.file_hash(backup_file_path):
                            return True
                        return False
                    except Exception:
                        continue

        main_path = os.path.join(self.main_backup_dir, rel_path)
        if os.path.exists(main_path):
            try:
                b_stat = os.stat(main_path)
                if b_stat.st_size != current_stat.st_size or abs(b_stat.st_mtime - current_stat.st_mtime) > 1:
                    return True
                if self.file_hash(src) != self.file_hash(main_path):
                    return True
            except Exception:
                return True

        return False

    async def copy_file(self, src: str, dst: str):
        async with self.copy_semaphore:
            try:
                if not server.has_backup_device_enough_space(src):
                    logging.warning(f"Not enough space to backup: {src}")
                    return
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                loop = asyncio.get_event_loop()

                tmp_dst = dst + ".tmp"

                # Copy file in executor
                await loop.run_in_executor(self.executor, shutil.copy2, src, tmp_dst)

                # Flush file data to disk
                with open(tmp_dst, 'rb') as f:
                    os.fsync(f.fileno())

                os.replace(tmp_dst, dst)
                logging.info(f"Backed up: {src} -> {dst}")
            except Exception as e:
                logging.error(f"Error copying {src} -> {dst}: {e}")
                try:
                    if os.path.exists(tmp_dst):
                        os.remove(tmp_dst)
                except Exception:
                    pass

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
                json.dump(metadata, tmpf)
                temp_path = tmpf.name

            os.replace(temp_path, meta_path)
        except Exception:
            pass
        
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
    
    async def scan_and_backup(self):
        tasks = []
        now = datetime.now()
        date_str = now.strftime('%d-%m-%Y')
        time_str = now.strftime('%H-%M')
        session_backup_dir = os.path.join(self.update_backup_dir, date_str, time_str)
    
        logging.info("Starting scan and backup...")

        with open(server.INTERRUPTED_MAIN, 'w') as f:
            f.write("interrupted")
        
        for entry in os.scandir(self.user_home):
            if entry.name.startswith('.') or entry.name in self.excluded_dirs:
                continue
    
            src_path = entry.path
            top_level_rel_path = os.path.relpath(src_path, self.user_home)
    
            # Skip ignored folders
            if any(os.path.commonpath([src_path, ign]) == ign for ign in self.ignored_folders):
                continue
    
            cached_meta = self.load_folder_metadata(top_level_rel_path)
            new_meta = {}
    
            for root, dirs, files in os.walk(src_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in self.excluded_dirs]
    
                subfolder_key = os.path.relpath(root, src_path).replace("\\", "/")
    
                current_meta = compute_folder_metadata(
                    root,
                    excluded_dirs=self.excluded_dirs,
                    excluded_exts=self.excluded_exts
                )
                new_meta[subfolder_key] = current_meta
    
                if not self.folder_needs_check(subfolder_key, current_meta, cached_meta):
                    continue
    
                for f in files:
                    if f.startswith('.') or any(f.endswith(ext) for ext in self.excluded_exts):
                        continue
                    fsrc = os.path.join(root, f)
                    frel = os.path.relpath(fsrc, self.user_home)
                    main_path = os.path.join(self.main_backup_dir, frel)
    
                    if not os.path.exists(main_path):
                        tasks.append(self.copy_file(fsrc, main_path))
                    elif self.file_was_updated(fsrc, frel):
                        session_backup_path = os.path.join(session_backup_dir, frel)
                        tasks.append(self.copy_file(fsrc, session_backup_path))
    
            self.save_folder_metadata(top_level_rel_path, new_meta)
    
        if tasks:
            await asyncio.gather(*tasks)
            server.update_recent_backup_information()
            logging.info("Backup session complete.")
    
        if os.path.exists(server.INTERRUPTED_MAIN):
            os.remove(server.INTERRUPTED_MAIN)
        
    async def resume_from_interruption(self):
        if os.path.exists(server.INTERRUPTED_MAIN):
            logging.info("Resuming from previous interrupted backup session...")
            await self.scan_and_backup()
            os.remove(server.INTERRUPTED_MAIN)

    async def run(self):
        await self.resume_from_interruption()
        shutdown_event = asyncio.Event()

        def stop_loop(signum, frame):
            self.signal_handler(signum, frame)
            shutdown_event.set()

        signal.signal(signal.SIGTERM, stop_loop)
        signal.signal(signal.SIGINT, stop_loop)
        signal.signal(signal.SIGTSTP, self.signal_handler)  # Suspend (Ctrl+Z)
        signal.signal(signal.SIGCONT, self.resume_handler)  # Resume

        while not self.should_exit:
            if self.suspend_flag:
                logging.info("Daemon suspended... sleeping.")
                await asyncio.sleep(5)
                continue

            if not os.path.exists(server.DAEMON_PID_LOCATION):
                self.signal_handler(signal.SIGTERM, None)
                break

            if has_driver_connection():
                await self.scan_and_backup()

            total_wait = WAIT_TIME * 60
            interval = 1
            elapsed = 0
            
            while elapsed < total_wait and not self.should_exit:
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=interval)
                    break
                except asyncio.TimeoutError:
                    elapsed += interval


if __name__ == "__main__":
    LOG_FILE_PATH = os.path.expanduser("~/logging.log")
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(LOG_FILE_PATH)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    server = SERVER()
    daemon = Daemon()
    setproctitle.setproctitle(f'{server.APP_NAME} - daemon')

    try:
        asyncio.run(daemon.run())
    except Exception as e:
        logging.error(f"Daemon exception: {e}")
    finally:
        logging.info("Daemon shutting down.")
