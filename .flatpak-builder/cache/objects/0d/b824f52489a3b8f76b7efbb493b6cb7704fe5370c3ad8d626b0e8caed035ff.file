from server import *

def restore_backup_flatpaks_applications():
    """Restore Flatpak applications from a backup file."""
    try:
        flatpak_file_path = SERVER().flatpak_txt_location()
        
        with open(flatpak_file_path, "r") as read_flatpak_file:
            flatpaks = [flatpak.strip() for flatpak in read_flatpak_file.readlines()]
    except FileNotFoundError as e:
        print(f'{flatpak_file_path} file not found!')
        exit()

    for flatpak in flatpaks:
        # if flatpak in read_exclude:
        #     continue
        try:
            print(f'Installing: {flatpak}...')

            # Install the flatpak
            result = sub.run(
                [
                "flatpak",
                "install",
                "--system",
                "--noninteractive",
                "--assumeyes",
                "--or-update", flatpak],
                stdout=sub.PIPE, stderr=sub.PIPE)

            if result.returncode != 0:
                print(f"Failed to install {flatpak}: {result.stderr.decode()}")
            else:
                print(f'Successfully installed {flatpak}')

        except Exception as e:
            print(f"Error while installing {flatpak}: {e}")


if __name__ == '__main__':
    restore_backup_flatpaks_applications()