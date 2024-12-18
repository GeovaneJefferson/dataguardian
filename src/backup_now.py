# from server import *
# from prepare_backup import PREPAREBACKUP
# from has_driver_connection import has_driver_connection


# server = SERVER()


# def is_first_backup() -> bool:
#     # Ensure the destination directory exists
#     os.makedirs(server.main_backup_folder(), exist_ok=True)

#     try:
#         if not any(os.scandir(server.main_backup_folder())):
#             return True
#         else:
#             return False
#     except Exception as e:
#         current_function_name = inspect.currentframe().f_code.co_name

#         print(e)
#         print(f'Funtion: {current_function_name}')
#         exit()


# class BackupNow:
#     def backup_now(self) -> None:
#         # Flatpaks applications names
#         self.backup_flatpaks_names()

#         # First backup
#         if is_first_backup():
#             # Backup driver has enough space
#             if PREPAREBACKUP().has_backup_device_enough_space(
#                     first_backup=True,
#                     backup_list=None):
#                 # Create necessaries folders
#                 PREPAREBACKUP().pre_backup_process()

#                 self.make_first_backup()
#         else:
#             # # Need to resume backup to main dir?
#             # # INI
#             # resume_to_main: str = get_database_value(
#             #     section='BACKUP',
#             #     option='resume_to_main',
#             #     func=self.perform_backup)

#             # resume_to_main: str = get_database_value(
#             #     table='BACKUP',
#             #     key='resume_to_main')

#             # Analyse backup for new/updated files
#             AnalyseBackup().compare_and_backup()

#         # # Set 'backup to be resume' to False
#         # set_database_value(
#         #     section='BACKUP',
#         #     option='to_be_resume',
#         #     value='false')


#     ##########################################################################
#     # Home
#     ##########################################################################
#     def make_first_backup(self) -> None:
#         print()
#         print('####################')
#         print('BACKING UP...')
#         print('####################')

#         src_dir: str = os.path.expanduser('~')
#         dst_dir: str = server.main_backup_folder()

#         total_files: int = server.count_total_files(src_dir)
#         copied_files: int = 0
#         start_time = time.time()  # Start timing

#         # Collect all file paths
#         for root, _, files in os.walk(src_dir):
#             for file in files:
#                 src_path: str = os.path.join(root, file)
#                 dst_path: str = os.path.join(dst_dir, os.path.relpath(src_path, src_dir))
#                 dst_path_dir: str = os.path.dirname(dst_path)
#                 only_dirname: str =  src_path.split('/')[3]

#                 # Skip .caches and caches folders
#                 if only_dirname in server.EXCLUDE_FILES:
#                     continue

#                 # Skip hidden itens
#                 if server.EXCLUDE_HIDDEN_ITENS:
#                     if only_dirname.startswith('.'):
#                         continue

#                 try:
#                     # Ensure the destination directory exists
#                     os.makedirs(dst_path_dir, exist_ok=True)

#                     # Copies files
#                     shutil.copy2(src_path, dst_path)

#                     copied_files += 1
#                     if copied_files % 1 == 0:  # Only show after X copied files
#                         print(f"\033[92m[✓]\033[0m {server.get_item_size(item_path=src_path, human_readable=True)} - {src_path} -> {dst_path}")
#                         server.print_progress_bar(copied_files, total_files, start_time)
#                         print()
#                 except Exception as e:
#                     current_function_name = inspect.currentframe().f_code.co_name

#                     print(e)
#                     print(f'Funtion: {current_function_name}')

#     ##########################################################################
#     # Flatpak
#     ##########################################################################
#     def backup_flatpak_data(self) -> None:
#         # Backup flatpaks names
#         self.backup_flatpaks_names()

#         # # Backup flatpak var
#         # self.backup_flatpak_var()

#         # # Backup flatpak lcoal
#         # self.backup_flatpak_local()

#     def backup_flatpaks_names(self) -> None:
#         print()
#         print('####################')
#         print('BACKING UP FLATPAKS...')
#         print('####################')

#         flatpak_location = server.flatpak_txt_location()

#         # Ensure the destination directory exists
#         # os.makedirs(flatpak_location, exist_ok=True)

#         flatpaks = set()

#         try:
#             # Ensure the directory exists
#             os.makedirs(os.path.dirname(flatpak_location), exist_ok=True)

#             # Create the file if it doesn't exist and write the flatpak names
#             with open(flatpak_location, 'w') as configfile:
#                 with os.popen(server.GET_FLATPAKS_APPLICATIONS_NAME) as flatpak_process:
#                     for flatpak in flatpak_process:
#                         flatpak_name = flatpak.strip()
#                         flatpaks.add(flatpak_name)
#                         configfile.write(flatpak_name + '\n')

#             print(f'\033[92m[✓]\033[0m Flatpaks backed up to {flatpak_location}')
#         except IOError as e:
#             print(e)
#             print(f'Error writing')

#     def backup_flatpak_var(self) -> None:
#         destination: str = server.flatpak_var_folder()

#         # Check if exists
#         if os.path.exists(destination):
#             # .var/app
#             flatpak_var_location = os.path.join(server.HOME_USER, '.var/app/')
#             for _, flatpak in enumerate(os.listdir(flatpak_var_location)):
#                 source = os.path.join(flatpak_var_location, flatpak)

#                 try:
#                     # Backup flatpaks folders
#                     shutil.copytree(source, destination)
#                     print(f"\033[92m[✓]\033[0m {source} -> {destination}")  # Successful
#                 except Exception as e:
#                     current_function_name = inspect.currentframe().f_code.co_name

#                     print(e)
#                     print(f'Funtion: {current_function_name}')
#                     # print(f"\033[91m[X]\033[0m {source} -> {destination} \n{e}")  # Error
#         else:
#             print(f'{flatpak_var_location} could not be found.')

#     def backup_flatpak_local(self) -> None:
#         destination: str = server.flatpak_local_folder()

#         # Check if exists
#         if os.path.exists(destination):
#             # .local/share/flatpak
#             flatpak_local_location = os.path.join(server.HOME_USER, '.local/share/flatpak/')
#             for _, flatpak in enumerate(os.listdir(flatpak_local_location)):
#                 source = os.path.join(flatpak_local_location, flatpak)

#                 try:
#                     # Backup flatpaks folders
#                     shutil.copytree(source, destination)
#                     print(f"\033[92m[✓]\033[0m {source} -> {destination}")
#                 except Exception as e:
#                     current_function_name = inspect.currentframe().f_code.co_name

#                     print(e)
#                     print(f'Funtion: {current_function_name}')
#                     # print(f"\033[91m[X]\033[0m {source} -> {destination} \n{e}")
#         else:
#             print(f'{flatpak_local_location} could not be found.')


# class AnalyseBackup:
#     def __init__(self) -> None:
#         self.home_source_dir: str = server.HOME_USER
#         self.main_backup_dir: str = server.main_backup_folder()
#         self.backup_dir_location: str = server.backup_folder_name()

#         self.has_datetime_backup_folders: list = server.has_backup_dates_to_compare()  # Dates
#         self.report_data: list = []
#         self.new_files: list = []
#         self.modified_files: list = []

#         self.home_source_files_dict: dict = {}  # path, (rel_path, size)
#         self.main_backup_files_dict: dict = {}  # path, (rel_path, size)

#     def get_all_files(self, directory: str) -> list:
#         all_files: list = []
#         for root, _, files in os.walk(directory):
#             for file in files:
#                 file: str = str(file)
#                 file_path: str = os.path.join(root, file)
#                 only_dirname: str =  file_path.split('/')[3]

#                 # Skip .caches and caches folders
#                 if only_dirname in server.EXCLUDE_FILES:
#                     continue

#                 # Skip hidden itens
#                 if server.EXCLUDE_HIDDEN_ITENS:
#                     if only_dirname.startswith('.'):
#                         continue

#                 try:
#                     relative_path = os.path.relpath(file_path, self.home_source_dir)
#                     file_size = server.get_item_size(item_path=file_path, human_readable=True)

#                     all_files.append((file_path, relative_path, file_size))
#                 except Exception as e:
#                     current_function_name = inspect.currentframe().f_code.co_name

#                     print(e)
#                     print(f'Funtion: {current_function_name}')

#         return all_files

#     def compare_and_backup(self) -> None:
#         print()
#         print('####################')
#         print('BACKING UP HOME...')
#         print('####################')

#         # SOURCE - .main_backup
#         for path, rel_path, size in self.get_all_files(self.home_source_dir):
#             self.home_source_files_dict[path] = (rel_path, size)

#         # BACKUP
#         for path, rel_path, size in self.get_all_files(self.main_backup_dir):
#             self.main_backup_files_dict[path] = (rel_path, size)

#         # ######################################################################
#         # NEW FILES/FOLDERS
#         for path, (rel_path, size) in self.home_source_files_dict.items():
#             rel_path: str = rel_path
#             main_full_backup_path = os.path.join(self.main_backup_dir, rel_path)
#             only_dirname: str =  main_full_backup_path.split('/')[3]

#             # File not found in .main_backup folder
#             if not os.path.exists(main_full_backup_path):
#                 if os.path.exists(path):  # Home path exists
#                     # try:
#                     # File size higher than 0 Bytes
#                     if int(str(size[:-2]).replace('.', '')) > 0:
#                         # Skip .caches and caches folders
#                         if only_dirname in server.EXCLUDE_FILES:
#                             continue

#                         # Skip hidden itens
#                         if server.EXCLUDE_HIDDEN_ITENS:
#                             if only_dirname.startswith('.'):
#                                 continue

#                         self.new_files.append((path, rel_path, size))
#                     # except Exception as e:
#                     #     handle_errors(e)

#         # ######################################################################
#         # UPDATED FILES/FOLDERS
#         if not self.has_datetime_backup_folders:  # No date/time backup yet made
#             # Compare with base backup folder
#             self.main_backup_updates()
#         else:
#             # Search datetime folders for new updates
#             self.datetime_updates()

#         ######################################################################
#         # # Outputs
#         # if self.new_files:
#         #     print("New Files:")
#         #     for path, rel_path, size in self.new_files:
#         #         print(f"- {path}, {size}, NEW")

#         # if self.modified_files:
#         #     print("\nModified Files:")
#         #     for path, rel_path, size in self.modified_files:
#         #         # Check itens in list, to make sure the some itens was not already updated
#         #         print(f"- {path}, {rel_path}, {size}, UPDATED")

#         ######################################################################
#         # New
#         self.report_data.extend(
#             [(path, size, datetime.now().timestamp(), datetime.now().day, datetime.now().hour,
#                 'New')
#                 for path, _, size in self.new_files])

#         # Updated
#         self.report_data.extend(
#             [(path, size, datetime.now().timestamp(), datetime.now().day, datetime.now().hour,
#                 'Updated')
#                 for path, _, size in self.modified_files])

#         ######################################################################
#         if self.new_files or self.modified_files:
#             # Check if it has enough space to mae the backup
#             if PREPAREBACKUP().has_backup_device_enough_space(
#                 first_backup=False,
#                 backup_list=self.report_data):  # has enough space
#                 self.write_to_csv()
#                 self.handle_report_data()

#             # INI
#             # set_database_value(
#             #     section='BACKUP',
#             #     option='resume_to_latest_date',
#             #     value='false',
#             #     func=self.compare_and_backup)

#             # SQLIT3
#             # set_database_value(
#             #     table='BACKUP',
#             #     key='resume_to_latest_date',
#             #     value='false')

#             # server.report_to_log(
#             #     msg_type='info',
#             #     msg='Backup completed.')  # Report to the log file.


#             #     # INI
#             #     # set_database_value(
#             #     #     section='BACKUP',
#             #     #     option='resume_to_latest_date',
#             #     #     value='false',
#             #     #     func=self.compare_and_backup)

#             #     # SQLIT3
#             #     # set_database_value(
#             #     #     table='BACKUP',
#             #     #     key='resume_to_latest_date',
#             #     #     value='false')

#             #     server.report_to_log(
#             #         msg_type='info',
#             #         msg='Backup completed.')  # Report to the log file.
#         else:
#             print(f'\033[91m[X]\033[0m No need to backup right now...')

#     def main_backup_updates(self) -> None:
#         # print('Comparing updates files/folders with main backup folder...')

#         try:
#             for path, (rel_path, size) in self.home_source_files_dict.items():
#                 rel_path: str = rel_path  # File name + extension
#                 home_file_path: str = os.path.join(server.HOME_USER, rel_path)
#                 main_full_backup_path: str = os.path.join(self.main_backup_dir, rel_path)
#                 only_dirname: str =  home_file_path.split('/')[3]

#                 # Skip hidden itens
#                 if server.EXCLUDE_HIDDEN_ITENS:
#                     if only_dirname.startswith('.'):
#                         continue

#                 # Skip .caches and caches folders
#                 if only_dirname in server.EXCLUDE_FILES:
#                     continue

#                 # File exists in both home and main backup folder
#                 if os.path.exists(home_file_path) and os.path.exists(main_full_backup_path):
#                     # Compare sizes betweem home and backup file/folder in main backup folder
#                     main_backup_file_size = server.get_item_size(main_full_backup_path, human_readable=True)

#                     # Home file <-> Main backup file
#                     # File has changed size
#                     if (size != main_backup_file_size and
#                         home_file_path not in self.modified_files):
#                         # Add file to be updated
#                         self.modified_files.append(
#                             (home_file_path, rel_path, size))
#         except KeyboardInterrupt as e:
#             server.report_to_log(
#                 msg_type='warning',
#                 msg=e)
#             exit()

#             # # Set 'backup to be resume' to True
#             # set_database_value(
#             #     section='BACKUP',
#             #     option='to_be_resume',
#             #     value='true',
#             #     func=)
#         except Exception as e:
#             current_function_name = inspect.currentframe().f_code.co_name

#             print(e)
#             print(f'Funtion: {current_function_name}')
#             # handle_errors(e)
#             # print(f"\033[91m[X]\033[0m {home_file_path} -> {main_full_backup_path}")  # \n{e}

#     def datetime_updates(self) -> None:
#         already_checked: list = []

#         try:
#             print('Comparing to:')

#             # Sort dates
#             self.has_datetime_backup_folders.sort(reverse=True)

#             # Collect full paths to the date folders
#             dates_list: list = []
#             for _, date in enumerate(self.has_datetime_backup_folders):
#                 datetime_full_dir_location = os.path.join(self.backup_dir_location, date)
#                 print(' - Date \033[92m[✓]\033[0m:', datetime_full_dir_location)
#                 dates_list.append(datetime_full_dir_location)

#             # Loop thourgh current date
#             date_time_list: list = []
#             for _, i in enumerate(dates_list):
#                 # Collect all times folder for the current date
#                 for x in os.listdir(i):
#                     date_time_list.append(os.path.join(i, x))

#             # Sort dates/times
#             date_time_list.sort(reverse=True)
#             for _, i in enumerate(date_time_list):
#                 # Check dates folders for this file (from the latest to oldest date)
#                 for root, _, files in os.walk(i):
#                     for file in files:
#                         src_path: str = os.path.join(root, file)
#                         # dst_path: str = os.path.join(dst_dir, os.path.relpath(src_path, src_dir))
#                         # dst_path_dir: str = os.path.dirname(dst_path)
#                         only_dirname: str =  src_path.split('/')[3]

#                         # Date/time file
#                         src_path_size = server.get_item_size(
#                                 item_path=src_path,
#                                 human_readable=True)

#                         # Home file
#                         home_file: str = src_path.replace(
#                             i, '')
#                         # home_file: str = '/'.join(
#                         #     home_file)
#                         home_file = os.path.join(
#                             os.path.expanduser('~'), home_file[1:])  # Exclude '/' with [1:], then join

#                         # Home file size
#                         home_file_size = server.get_item_size(
#                             item_path=home_file,
#                             human_readable=True)

#                         # Skip .caches and caches folders
#                         if only_dirname in server.EXCLUDE_FILES:
#                             continue

#                         # Skip hidden itens
#                         if server.EXCLUDE_HIDDEN_ITENS:
#                             if only_dirname.startswith('.'):
#                                 continue

#                         # Pass if item already was checked
#                         if home_file not in already_checked:
#                             already_checked.append(home_file)

#                             # Path exists in users' home
#                             if os.path.exists(home_file):
#                                 # Compare found latest item size (datetime) with home file size
#                                 if src_path_size != home_file_size:
#                                     if (home_file, file, home_file_size) not in self.modified_files:
#                                         self.modified_files.append(
#                                             (home_file, file, home_file_size))
#         except KeyboardInterrupt as e:
#             # User cancel the backup process, with keyboard or system restart or shutdown.
#             # Report to the log file.
#             server.report_to_log(
#                 msg_type='warning',
#                 msg=e)

#             # # Set 'backup to be resume' to True
#             # set_database_value(
#             #     section='BACKUP',
#             #     option='to_be_resume',
#             #     value='true',
#             #     func=)
#         except Exception as e:
#             current_function_name = inspect.currentframe().f_code.co_name

#             print(e)
#             print(f'Funtion: {current_function_name}')

#     def get_latest_datetime_dir(self) -> str:
#         # Sort dates
#         self.has_datetime_backup_folders.sort(reverse=True)

#         # Collect full paths to the date folders
#         dates_list: list = []
#         for _, date in enumerate(self.has_datetime_backup_folders):
#             datetime_full_dir_location = os.path.join(self.backup_dir_location, date)
#             print(' - Date \033[92m[✓]\033[0m:', datetime_full_dir_location)
#             dates_list.append(datetime_full_dir_location)
#             break

#         # Loop thourgh current date
#         date_time_list: list = []
#         for _, i in enumerate(dates_list):
#             # Collect all times folder for the current date
#             for x in os.listdir(i):
#                 date_time_list.append(os.path.join(i, x))

#         # Sort dates/times
#         date_time_list.sort(reverse=True)

#         # Resume backtup to the latest date/time dir
#         return date_time_list[0]

#         # server.backup_to_dst(
#         #     src_path=0,
#         #     dst_path=date_time_list[0])


#     def write_to_csv(self) -> None:
#         # Write to it
#         with open(server.REPORT_CSV_LOCATION, 'w', newline='') as csvfile:
#             writer = csv.writer(csvfile)
#             writer.writerow(['Location', 'Size (bytes)', 'Time', 'Day', 'Hour', 'Status'])
#             for row in self.report_data:
#                 writer.writerow(row)

#     def handle_report_data(self) -> None:
#         backup_folder_location: str = server.backup_folder_name()

#         created_datetime: bool = False

#         total_files: int = len(self.report_data)
#         copied_files: int = 0
#         start_time = time.time()  # Start timing

#         # Create a folder with current datetime information
#         current_date = datetime.now().strftime('%d-%m-%Y')
#         current_time = datetime.now().strftime('%H-%M')
#         current_datetime = os.path.join(current_date, current_time)
#         # item: str  # modifield destination

#         datetime_folder: str

#         for path, size, _, day, hour, status in self.report_data:
#             src_path: str = path
#             rel_path = os.path.relpath(src_path, self.home_source_dir)

#             if status == 'New':
#                 # Backup to the .main_backup/
#                 dst_path = os.path.join(self.main_backup_dir, rel_path)
#             elif status == 'Updated':
#                 modified_rel_path = os.path.join(self.home_source_dir, os.path.basename(rel_path))
#                 # Remove home user name
#                 modified_rel_path = modified_rel_path.replace(os.path.expanduser("~/"), '')
#                 # Adjusting the relative path to match the new backup structure
#                 adjusted_rel_path = os.path.join(current_datetime, modified_rel_path)

#                 ##############################################################
#                 # Need to be resume?
#                 # INI
#                 resume_to_latest_datetime: str = server.get_database_value(
#                     section='BACKUP',
#                     option='resume_to_latest_date')

#                 # SQLITE3
#                 # resume_to_latest_datetime: str = server.get_database_value(
#                 #     table='BACKUP',
#                 #     key='resume_to_latest_date')

#                 if resume_to_latest_datetime:
#                     datetime_folder = self.get_latest_datetime_dir()
#                 ##########################################################
#                 else:
#                     # Create current date folder and time folder, once.
#                     if not created_datetime:
#                         created_datetime = True

#                         # Backup to the backups/
#                         datetime_dir_location = os.path.join(
#                             backup_folder_location, os.path.dirname(adjusted_rel_path))
#                         datetime_dir_location = os.path.join(
#                             datetime_dir_location, os.path.basename(rel_path))
#                         datetime_dir_location = os.path.join(
#                             server.backup_folder_name(), adjusted_rel_path)

#                         # Create datetime folder: fx. /media/USERNAME/BACKUP/dataguardian/backups/10-07-2024/11-33
#                         datetime_folder = '/'.join(datetime_dir_location.split('/')[:-1])

#                         # Ensure the destination directory exists
#                         os.makedirs(datetime_folder, exist_ok=True)

#                 # File destination location
#                 dst_path = os.path.join(
#                     datetime_folder,
#                     src_path.replace(os.path.expanduser("~/"), ''))

#             server.backup_to_dst(
#                 src_path=src_path,
#                 dst_path=dst_path)

#             try:
#                 copied_files += 1
#                 if copied_files % 1000 == 0:  # Only show after X copied files
#                     print(f"\033[92m[✓]\033[0m {server.get_item_size(item_path=src_path, human_readable=True)} - {src_path} -> {dst_path}")
#                     server.print_progress_bar(copied_files, total_files, start_time)
#                     print()
#             except FileNotFoundError as e:
#                 print(e)
#                 # handle_errors(e)
#         try:
#             print()
#             print('####################')
#             print('OUTPUT')
#             print('####################')
#             print(f'\033[92m[✓]\033[0m {datetime_folder}')
#         except:
#             pass
#         # print(f'\033[92m[✓]\033[0m Flatpaks backed up to {self.main_backup_dir}')


# if __name__ == "__main__":
#     pass

#     # Has connection with the backup device
#     if has_driver_connection():
#         # Backup home
#         BackupNow().backup_now()


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
