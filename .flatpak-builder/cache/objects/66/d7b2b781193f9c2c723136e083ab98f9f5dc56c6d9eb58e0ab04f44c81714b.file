from server import *

serverMain = SERVER()


class PREPAREBACKUP:
    def pre_backup_process(self) -> None:
        print()
        print('####################')
        print('PREPARING BACKUP...')
        print('####################')

        dir_to_create: list = [
            serverMain.create_base_folder(),
            serverMain.backup_folder_name(),
            serverMain.main_backup_folder(),
            # MAIN_INI_FILE.include_to_backup(),
            # MAIN_INI_FILE.application_main_folder(),
            # create_flatpak_folder(),
            # MAIN_INI_FILE.pip_packages_txt_location(),
            # flatpak_txt_location(),  # Fix wirte error
            # flatpak_var_folder(),
            # flatpak_local_folder(),
            # MAIN_INI_FILE.wallpaper_main_folder(),
            # MAIN_INI_FILE.rpm_main_folder(),
            # MAIN_INI_FILE.deb_main_folder()
        ]

        for folder in dir_to_create:
            print(folder)
            # Ensure the destination directory exists
            os.makedirs(folder, exist_ok=True)

        # # Check and create necessary GNOME folders
        # if get_user_de() in ['gnome', 'unity']:
        #     gnome_folders = [
        #         MAIN_INI_FILE.gnome_main_folder(),
        #         MAIN_INI_FILE.gnome_configurations_folder_main_folder(),
        #         MAIN_INI_FILE.gnome_local_share_main_folder(),
        #         MAIN_INI_FILE.gnome_config_main_folder()
        #     ]
        #     for folder in gnome_folders:
        #         self.create_directory_if_not_exists(folder)

        # # Check and create necessary KDE folders
        # elif get_user_de() == 'kde':
        #     kde_folders = [
        #         MAIN_INI_FILE.kde_main_folder(),
        #         MAIN_INI_FILE.kde_configurations_folder_main_folder(),
        #         MAIN_INI_FILE.kde_local_share_main_folder(),
        #         MAIN_INI_FILE.kde_config_main_folder(),
        #         MAIN_INI_FILE.kde_share_config_main_folder()
        #     ]
        #     for folder in kde_folders:
        #         self.create_directory_if_not_exists(folder)

        # Create restore_settings.ini file
        # self.create_file_if_not_exists(MAIN_INI_FILE.restore_settings_location())

    def get_available_space(self, path:str) -> int:
        try:
            fs_stat = os.statvfs(path)
            return fs_stat.f_frsize * fs_stat.f_bavail  # In Bytes
        except Exception as e:
            print(f"\033[91m[X]\033[0m Error getting available space for {path}: {e}")

    # def get_user_home_size_bytes(self):
    #     """Gets the size of the user's home directory in bytes.

    #     Returns:
    #         The size of the user's home directory in bytes.
    #     """

    #     user_home = os.path.expanduser('~')
    #     total_size = 0

    #     for dirpath, _, filenames in os.walk(user_home):
    #         for file in filenames:
    #             file_path = os.path.join(dirpath, file)
    #             try:
    #                 total_size += os.path.getsize(file_path)
    #             except OSError:
    #                 pass  # Ignore files that cannot be accessed

    #     return total_size  # In Bytes


    # def has_backup_device_enough_space(
    #         self, first_backup: bool, list_to_backup: list) -> bool:
    #     """Checks if there's sufficient space for the backup."""
    #     """Args:
    #         first_backup: Whether it's the first backup.
    #         backup_list: A list of files or directories to be backed up.

    #     Returns:
    #         True if there's sufficient space, False otherwise.

    #     """
    #     print()
    #     print('####################')
    #     print('ANALYSING SIZE...')
    #     print('####################')
       
    #     # Threshold for available space (at least 2 GB)
    #     threshold_bytes = 2 * 1024 * 1024 * 1024  # 2 GB
        
    #     # Get available space on the backup device
    #     device_available_space = self.get_available_space(
    #         path=serverMain.get_database_value(
    #             section='DRIVER',
    #             option='driver_location'))  

    #     total_size_bytes = 0

    #     # Calculate the total size of all files and directories to be backed up
    #     for item in list_to_backup:
    #         try:
    #             if os.path.isfile(item):
    #                 # For a file, just add its size
    #                 total_size_bytes += os.path.getsize(item)
    #             elif os.path.isdir(item):
    #                 # For a directory, sum the sizes of all its contents
    #                 for root, dirs, files in os.walk(item):
    #                     for file in files:
    #                         file_path = os.path.join(root, file)
    #                         total_size_bytes += os.path.getsize(file_path)
    #         except (OSError, ValueError) as e:
    #             print(f"Error processing {item}: {e}")

    #     # Check if available space is enough
    #     if device_available_space > (total_size_bytes + threshold_bytes):
    #         print(f"\033[92m[✓]\033[0m Enough space for backup!")
    #         print()
    #         return True
    #     else:
    #         print(f"\033[91m[X]\033[0m Not enough space for backup")
    #         return False

        
    # def has_backup_device_enough_space(
    #         self, first_backup:bool, backup_list:list) -> bool:
    #     """Checks if there's sufficient space for the backup.

    #     Args:
    #         first_backup: Whether it's the first backup.
    #         backup_list: A list of files or directories to be backed up.

    #     Returns:
    #         True if there's sufficient space, False otherwise.
    #     """
    #     print()
    #     print('####################')
    #     print('ANALYSING SIZE...')
    #     print('####################')

    #     # Threshold for available space (at least 2 GB)
    #     threshold_bytes = 2 * 1024 * 1024 * 1024  # 2 GB

    #     try:
    #         # INI
    #         device_available_space = self.get_available_space(
    #             path=serverMain.get_database_value(
    #                 section='DRIVER',
    #                 option='driver_location'))  # func=self.has_sufficient_dst_drive_space)
    #     except Exception as e:
    #         print(e)
    #         exit()

    #     if first_backup:
    #         # Get Home user available space
    #         home_folder_path = self.get_available_space(
    #             os.path.expanduser('~'))

    #         # Check if available space is above the threshold
    #         if device_available_space > (home_folder_path + threshold_bytes):  # Has enough space
    #             print(f"\033[92m[✓]\033[0m Enough space for backup!")
    #             print()
    #             return True
            
    #         destination_driver: str = serverMain.get_database_value(
    #             section='DRIVER',
    #             option='driver_location',
    #             func=self.has_backup_device_enough_space)

    #         print(f"\033[91m[X]\033[0m Not enough space in {destination_driver} to continue with the backup")

    #         # serverMain.report_to_log(
    #         #     msg_type='error',
    #         #     msg=f'Not enough space in {destination_driver} to continue with the backup.')  # Report to the log file.exit()
    #         # print()
    #         return False
    #     else:
    #         ######################################################################
    #         # Analyse necessary space for the next backup
    #         total_size_bytes = 0
    #         location: str
    #         size_str: str

    #         # Calculate total size
    #         for row in backup_list:
    #             location, size_str, *_ = row
    #             try:
    #                 if os.path.exists(location):
    #                     if size_str == "0.00 B":
    #                         # Handle zero-sized files or invalid sizes
    #                         size_bytes = 0
    #                     elif "KB" in size_str:
    #                         size_bytes = float(size_str.replace(" KB", "")) * 1024
    #                     elif "MB" in size_str:
    #                         size_bytes = float(size_str.replace(" MB", "")) * 1024 * 1024
    #                     elif "GB" in size_str:
    #                         size_bytes = float(size_str.replace(" GB", "")) * 1024 * 1024 * 1024
    #                     else:
    #                         size_bytes = float(size_str)
    #                     total_size_bytes += size_bytes
    #             except (ValueError, OSError) as e:
    #                 pass

    #         # print()
    #         # print(f'device_available_space (bytes): {device_available_space}')
    #         # print(f"Total size (bytes): {total_size_bytes}")

    #         # Check if available space is above the threshold
    #         if device_available_space > (total_size_bytes + threshold_bytes):  # Has enough space
    #             return True
    #         else:
    #             return False

    def has_backup_device_enough_space(backup_device_path: str, backup_list: list) -> bool:
        """
        Checks if the backup device has enough space to back up the files.
        
        Args:
            backup_device_path (str): Path to the backup device/directory.
            backup_list (list): List of files or directories to be backed up (each item is a tuple: (src_path, rel_path, size)).
        
        Returns:
            bool: True if there is enough space, False otherwise.
        """
        print()
        print('####################')
        print('ANALYSING SIZE...')
        print('####################')

        # Threshold for available space (leave at least 2 GB free)
        threshold_bytes = 2 * 1024 * 1024 * 1024  # 2 GB

        # Get available space on the backup device
        total, used, free = shutil.disk_usage(backup_device_path)

        # Calculate total size of the files to be backed up
        total_size_to_backup = sum(size for _, _, size in backup_list)

        # Check if there is enough space on the backup device
        if free > (total_size_to_backup + threshold_bytes):
            print(f"\033[92m[✓]\033[0m Enough space for backup!")
            return True
        else:
            print(f"\033[91m[X]\033[0m Not enough space on the backup device. Required: {total_size_to_backup} bytes, Available: {free} bytes")
            return False

if __name__ == "__main__":
    pass
