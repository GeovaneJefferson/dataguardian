from server import *

server = SERVER()

def restore_backup_home() -> None:
    """Restores the Home folders from the latest backup."""
    print("Restoring Home folders...")

    # Get the main backup folder location
    home_backup_dir: str = server.main_backup_folder()

    # Backup home dir can not be found
    if not os.path.exists(home_backup_dir):
        print(f"Backup location {home_backup_dir} can not be found.")
        return

    for folder in os.listdir(home_backup_dir):
        src_path: str = os.path.join(home_backup_dir, folder)
        dst_path: str = os.path.join(server.HOME_USER, folder)

        # # Create the directory if it doesn't exist
        # if os.path.isdir(dst_path):
        #     os.makedirs(dst_path, exist_ok=True)
        
        total_files: int = server.count_total_files(home_backup_dir)
        copied_files: int = 0
        start_time = time.time()  # Start timing

        # Copy everything inside current dir
        for root, dirs, files in os.walk(src_path):
            for file in files:
                src_item: str = os.path.join(root, file)
                filtered_src_item: str = src_item.replace(home_backup_dir, '')[1:]  # Remove '/' from the start 
                dest_dir: str = os.path.join(
                    server.HOME_USER, filtered_src_item.replace(
                        home_backup_dir, ''))
                dst_dirname: str = os.path.dirname(dest_dir)

                # Create the directory if it doesn't exist
                os.makedirs(dst_dirname, exist_ok=True)

                # Copy 
                try:
                    server.print_progress_bar(
                        progress=copied_files, 
                        total=total_files, 
                        start_time=start_time)

                    copied_files += 1

                    shutil.copy2(src_item, dest_dir)
                except (FileExistsError, FileNotFoundError) as e:
                    pass

            print(f"\033[92m[✓]\033[0m Successfully restored: {dst_path}")

    print("\nRestoration complete.")


if __name__ == '__main__':
   restore_backup_home()
