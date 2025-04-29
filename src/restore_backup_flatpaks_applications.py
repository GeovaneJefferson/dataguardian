from server import *

def restore_backup_flatpaks_applications():
    """Restore Flatpak applications from a backup file."""
    try:
        flatpak_file_path = SERVER().flatpak_txt_location()
        if not flatpak_file_path or not os.path.isfile(flatpak_file_path):
            print(f"Invalid or missing flatpak file path: {flatpak_file_path}")
            exit()
        
        raise FileNotFoundError(f'{flatpak_file_path} file not found!')
    except FileNotFoundError as e:
        print(e)
        exit()

    flatpaks = []  # Replace with logic to retrieve flatpak list, e.g., reading from the file
    for flatpak in flatpaks:
        # if flatpak in read_exclude:
        #     continue
        try:
            print(f'Installing: {flatpak}...')

            # Install the flatpak
            result = sub.run(
                ["flatpak", "install", "--system", "--noninteractive", "--assumeyes", flatpak],
                stdout=sub.PIPE, stderr=sub.PIPE)

            if result.returncode != 0:
                print(f"Failed to install '{flatpak}': {result.stderr.decode()}")
            else:
                print(f'Successfully installed {flatpak}')

        except sub.SubprocessError as e:
            print(f"Subprocess error while installing {flatpak}: {e}")
        except Exception as e:
            import traceback
            print(f"Unexpected error while installing {flatpak}: {e}")


if __name__ == '__main__':
    restore_backup_flatpaks_applications()