import os
import shutil
import asyncio
import logging
import signal
import time
from datetime import datetime
from server import SERVER
from has_driver_connection import has_driver_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
COPY_CONCURRENCY = 10

def signal_handler(signum, frame):
    logging.info("Backup process paused...")

def copy_file(src, dst):
    try:
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            logging.info(f"Copied {src} to {dst}")
    except Exception as e:
        logging.error(f"Error copying {src} to {dst}: {e}")

async def async_copy_file(src, dst, semaphore):
    async with semaphore:
        await asyncio.to_thread(copy_file, src, dst)

def check_main_backup(server, rel_path, last_mod_time):
    backup_file = os.path.join(server.main_backup_folder(), rel_path)
    if os.path.exists(backup_file):
        return os.path.getmtime(backup_file) >= last_mod_time
    return False

def check_previous_backups(server, rel_path, last_mod_time):
    backup_folder = server.backup_folder_name()
    try:
        backup_dates = sorted([d for d in os.listdir(backup_folder) if '-' in d], reverse=True)
    except Exception as e:
        logging.error(f"Error listing backup folders: {e}")
        return False

    for date_folder in backup_dates:
        date_path = os.path.join(backup_folder, date_folder)
        if os.path.isdir(date_path):
            try:
                time_folders = sorted(os.listdir(date_path), reverse=True)
            except Exception as e:
                logging.error(f"Error listing time folders in {date_path}: {e}")
                continue
            for time_folder in time_folders:
                folder_path = os.path.join(date_path, time_folder)
                if os.path.isdir(folder_path):
                    backup_file = os.path.join(folder_path, rel_path)
                    if os.path.exists(backup_file):
                        if os.path.getmtime(backup_file) >= last_mod_time:
                            return True
    return False

def needs_backup(server, rel_path, last_mod_time):
    return not (check_main_backup(server, rel_path, last_mod_time) or check_previous_backups(server, rel_path, last_mod_time))

async def perform_backup(server):
    print("Performing backup...")  # Debug statement
    logging.info("Starting backup process...")
    home_files, total_files = await server.get_filtered_home_files()
    
    # Debug: print the raw tuples to see their order.
    for item in home_files:
        logging.info(f"File tuple: {item}")
    
    # Adjust this unpacking once you know the correct order.
    # For demonstration, assume the tuple is (src, rel_path, size):
    semaphore = asyncio.Semaphore(COPY_CONCURRENCY)
    
    # Incremental backup branch
    logging.info("Performing incremental backup...")
    current_date = datetime.now().strftime('%d-%m-%Y')
    current_time = datetime.now().strftime('%H-%M')
    base_backup_dir = os.path.join(server.backup_folder_name(), current_date, current_time)
    os.makedirs(base_backup_dir, exist_ok=True)
    
    tasks = []
    for src, rel_path, size in home_files:
        try:
            mod_time = os.path.getmtime(src)
        except Exception as e:
            logging.error(f"Error getting modification time for {src}: {e}")
            continue
        # If the returned rel_path is absolute, convert it to relative.
        if os.path.isabs(rel_path):
            rel_path = os.path.relpath(rel_path, server.USER_HOME)
            
        # Debug prints to see what we're processing.
        logging.info(f"src: {src}")
        logging.info(f"rel_path: {rel_path}")
        logging.info(f"size: {size}")
        
        if needs_backup(server, rel_path, mod_time):
            dst = os.path.join(base_backup_dir, rel_path)
            logging.info(f"Copying to: {dst}")
            tasks.append(async_copy_file(src, dst, semaphore))
            server.CACHE[rel_path] = {'last_mod_time': mod_time, 'size': size}
    
    await asyncio.gather(*tasks)
    server.save_cache()
    logging.info("Backup process completed.")

if __name__ == '__main__':
    server = SERVER()
    signal.signal(signal.SIGUSR1, signal_handler)
    if has_driver_connection():
        asyncio.run(perform_backup(server))
    else:
        logging.error("No driver connection available.")
