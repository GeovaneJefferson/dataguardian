from server import *
from has_driver_connection import has_driver_connection

def signal_handler(signum, frame):
    # Save the state when receiving a sleep signal
    #server.save_cache()
    print("Backup process paused...")

def has_base_backup_folder() -> bool:
    # Ensure the destination directory exists
    try:
        if any(os.scandir(server.main_backup_folder())):
            return True
        return False
    except Exception as e:
        return False

def copy_file(src, dst):
    try:
        # Only copy is file was not already back up
        if not os.path.exists(dst):
            # Create the necessary directories
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            # Copy the file
            shutil.copy2(src, dst)
    except (FileNotFoundError, OSError):
        pass

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

async def async_copy_file(src, dst):
    await asyncio.to_thread(copy_file, src, dst)

def backup_flatpaks_names():
    flatpak_location = server.flatpak_txt_location()

    # Ensure the destination directory exists
    try:
        os.makedirs(os.path.dirname(flatpak_location), exist_ok=True)
    except OSError as e:
        print(f"Error creating directory: {e}")
        return

    flatpaks = set()

    try:
        # Create the file and write the flatpak names
        with open(flatpak_location, 'w') as configfile:
            # Use subprocess to handle the flatpak command
            result = sub.run(
                server.GET_FLATPAKS_APPLICATIONS_NAME,
                shell=True,
                text=True,
                capture_output=True,
                check=True)

            flatpak_process = result.stdout.splitlines()

            for flatpak in flatpak_process:
                flatpak_name = flatpak.strip()
                flatpaks.add(flatpak_name)
                configfile.write(flatpak_name + '\n')

        print(f'\033[92m[✓]\033[0m Flatpaks backed up to {flatpak_location}')
    except (IOError, sub.CalledProcessError) as e:
        print(f"Error: {e}")
        print('Error writing to file or executing command.')


class BackupNow:
    def __init__(self):
        self.filtered_home_files = server.get_filtered_home_files()

    def backup_now(self):
        print()
        print('####################')
        print('WARMING UP...')
        print('####################')

        # Check if base backup base folder exists
        if has_base_backup_folder():
            # Check for new file, send them to the backup base folder
            asyncio.run(UpdatedBackup().backup_updates())
        else:
            if server.has_backup_device_enough_space(
                backup_device_path=server.DRIVER_LOCATION,
                backup_list=self.filtered_home_files):

                asyncio.run(FirstBackup().make_first_backup())

        # print()
        # print('####################')
        # print('BACKING UP FLATPAKS...')
        # print('####################')
        # # Flatpaks applications names
        # backup_flatpaks_names()

        print()
        print('####################')
        print('DONE!')
        print('####################')


class FirstBackup:
    def __init__(self):
        # self.total_files = len(server.get_filtered_home_files())  # Set the total number of files
        self.base_backup_folder = server.main_backup_folder()
        self.copied_files: int = 0
        self.start_time = time.time()

    async def make_first_backup(self):
        print()
        print('####################')
        print('BACKING UP...')
        print('####################')

        # Get the files to back up
        files_to_backup = server.get_filtered_home_files()  # Assume this returns a list of files
        for path, rel_path, size in files_to_backup:
            await server.backup_file(path)  # Call the async backup method for each file

        # # Batch process the backups
        # for path, rel_path, size in server.get_filtered_home_files():
        #     dst_path = os.path.join(self.base_backup_folder, rel_path)
        #
        #     # await async_copy_file(path, dst_path)
        #     await server.backup_file(path)


            # # Save updated cache information in memory
            # server.CACHE[rel_path] = {
            #     'last_mod_time': os.path.getmtime(path),
            #     'size': size}

            # self.copied_files += 1
            # if self.copied_files % 10 == 0:
            #     server.print_progress_bar(
            #         progress=self.copied_files,
            #         total=self.total_files,
            #         start_time=self.start_time)

        # Save the cache after all backups are done
        # server.save_cache()


class UpdatedBackup:
    def __init__(self) -> None:
        self.current_date = datetime.now().strftime('%d-%m-%y')
        self.current_time = datetime.now().strftime('%H-%M')
        self.filtered_home_files = server.get_filtered_home_files()
        self.total_files = len(self.filtered_home_files)  # Set the total number of files
        self.to_backup: list = []
        self.copied_files: int = 0
        self.start_time = time.time()

    async def backup_updates(self):
        print()
        print('####################')
        print('BACKING UP...')
        print('####################')

        # Flag to determine if a backup is necessary
        backup_needed = False

        # Iterate through all files in the source directory
        for path, rel_path, size in self.filtered_home_files:
            last_mod_time = os.path.getmtime(path)

            # First compare with the latest date/time folders
            if not check_previous_backups(rel_path, last_mod_time):
                # If not found in date/time folders, compare with .main_backup
                if not check_main_backup(rel_path, last_mod_time):
                    # Backup is needed for this file
                    backup_needed = True
                    break

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
                        # print(f"Backing up: {rel_path}")
                        dst_path = os.path.join(base_backup_dir, rel_path)
                        # self.backup_file(path, dst_path)

                        # Mark the file for backup
                        # self.to_backup.append((path, dst_path))
                        self.to_backup.append((path, rel_path, size))

                        # Update the cache with the new backup info
                        server.CACHE[rel_path] = {
                            'last_mod_time': last_mod_time,
                            'size': size}

        # Backup new files to the base backup folder
        await self.detect_new_files()

        # Now backup all the files in the to_backup list
        if self.to_backup:
            # print(f"Backing up {len(self.to_backup)} files...")

            for path, rel_path, size in self.to_backup:
                dst_path = os.path.join(base_backup_dir, rel_path)

                print(path, dst_path)

                await async_copy_file(path, dst_path)  # Perform the backup

                # Save updated cache information in memory
                server.CACHE[rel_path] = {
                    'last_mod_time': os.path.getmtime(path),
                    'size': size}

                self.copied_files += 1

                # Update the progress bar for each file copied
                if self.copied_files % 10 == 0:
                    server.print_progress_bar(
                        progress=self.copied_files,
                        total=len(self.to_backup),
                        start_time=self.start_time)

        # Save the cache after all backups are done
        server.save_cache()

    async def detect_new_files(self):
        """
        Detect new files that need to be backed up.
        """
        # print("Detecting new files...")

        for path, rel_path, size in self.filtered_home_files:
            dst_path = os.path.join(server.main_backup_folder(), rel_path)

            if not os.path.exists(dst_path):
                self.to_backup.append((path, rel_path, size))

        # print(f"Detected {len(self.to_backup)} new files to back up.")


if __name__ == '__main__':
    server = SERVER()
    main = BackupNow()

    # Register signal handlers
    signal.signal(signal.SIGUSR1, signal_handler)

    if has_driver_connection():
        main.backup_now()
