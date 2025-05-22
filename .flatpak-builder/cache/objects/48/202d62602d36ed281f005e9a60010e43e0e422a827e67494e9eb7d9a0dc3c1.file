from server import *
import os
import shutil
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

serverMain = SERVER()

class PREPAREBACKUP:
    def pre_backup_process(self) -> None:
        """
        Prepares the backup process by creating necessary directories.
        """
        logging.info("####################")
        logging.info("PREPARING BACKUP...")
        logging.info("####################")

        # List of directories to create
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
            try:
                # Ensure the destination directory exists
                os.makedirs(folder, exist_ok=True)
                logging.info(f"Created directory: {folder}")
            except OSError as e:
                logging.error(f"Error creating directory {folder}: {e}")
       
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

    def get_available_space(self, path: str) -> int:
        """
        Gets the available space on the specified path.

        Args:
            path (str): The path to check available space for.

        Returns:
            int: Available space in bytes.
        """
        try:
            fs_stat = os.statvfs(path)
            return fs_stat.f_frsize * fs_stat.f_bavail  # Available space in bytes
        except Exception as e:
            logging.error(f"Error getting available space for {path}: {e}")
            return 0

    def has_backup_device_enough_space(self, backup_device_path: str, backup_list: list) -> bool:
        """
        Checks if the backup device has enough space to back up the files.

        Args:
            backup_device_path (str): Path to the backup device/directory.
            backup_list (list): List of files or directories to be backed up 
                                (each item is a tuple: (src_path, rel_path, size)).

        Returns:
            bool: True if there is enough space, False otherwise.
        """
        logging.info("####################")
        logging.info("ANALYSING SIZE...")
        logging.info("####################")

        # Threshold for available space (leave at least 2 GB free)
        threshold_bytes = 2 * 1024 * 1024 * 1024  # 2 GB

        try:
            # Get available space on the backup device
            total, used, free = shutil.disk_usage(backup_device_path)

            # Calculate total size of the files to be backed up
            total_size_to_backup = sum(size for _, _, size in backup_list)

            # Check if there is enough space on the backup device
            if free > (total_size_to_backup + threshold_bytes):
                logging.info(f"Enough space for backup! Required: {total_size_to_backup} bytes, Available: {free} bytes")
                return True
            else:
                logging.error(f"Not enough space on the backup device. Required: {total_size_to_backup} bytes, Available: {free} bytes")
                return False
        except Exception as e:
            logging.error(f"Error checking backup device space: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    prepare_backup = PREPAREBACKUP()
    prepare_backup.pre_backup_process()

    # # Example backup list (src_path, rel_path, size)
    # backup_list = [
    #     ("/path/to/file1", "file1", 1024),
    #     ("/path/to/file2", "file2", 2048),
    # ]

    # # Check if there is enough space on the backup device
    # backup_device_path = "/path/to/backup/device"
    # if prepare_backup.has_backup_device_enough_space(backup_device_path, backup_list):
    #     logging.info("Backup can proceed.")
    # else:
    #     logging.error("Backup cannot proceed due to insufficient space.")

