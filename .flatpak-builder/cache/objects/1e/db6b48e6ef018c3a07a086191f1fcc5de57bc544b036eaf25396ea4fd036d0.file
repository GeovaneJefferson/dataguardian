from server import *

server = SERVER()
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def restore_backup_home() -> None:
    """Restores the Home folders using the base backup and incremental updates."""
    print("Restoring Home folders...")
    logging.info("Restoring Home folders...")

    # Step 1: Restore the base backup completely.
    base_backup_folder = server.main_backup_folder()
    if not os.path.exists(base_backup_folder):
        logging.error(f"Backup location {base_backup_folder} cannot be found.")
        return

    print("Step 1: Restoring base backup...")
    restore_folder(base_backup_folder, server.HOME_USER)

    # Step 2: Apply incremental updates (if any)
    updates_root = server.backup_folder_name()
    if os.path.exists(updates_root):
        # List update folders (exclude the base folder itself)
        incremental_folders: list = [folder for folder in os.listdir(updates_root)
                               if os.path.isdir(os.path.join(updates_root, folder))]
        
        # Remove the base backup folder name from the update folders list if present.
        base_folder_name = os.path.basename(base_backup_folder)
        if base_folder_name in incremental_folders:
            incremental_folders.remove(base_folder_name)
        
        # Sort the incremental folders by date (format assumed to be "dd-mm-yyyy")
        try:
            incremental_folders.sort(
                key=lambda folder: datetime.strptime(folder, "%d-%m-%Y"),
                reverse=True  # Latest update first
            )
        except Exception as e:
            print(f"Error parsing update folder names: {e}")
            return
        
        print("Step 2: Applying incremental updates...")
        apply_incremental_updates(updates_root, server.HOME_USER, incremental_folders)
    else:
        print("No incremental updates found.")

    print("\n✅ Restoration complete.")

def restore_folder(src_root: str, dest_root: str) -> None:
    """
    Copies all files from src_root to dest_root, preserving directory structure
    and overwriting existing files.
    """
    total_files = server.count_total_files(src_root)
    copied_files = 0
    start_time = time.time()

    for root, dirs, files in os.walk(src_root):
        for file in files:
            src_item = os.path.join(root, file)
            relative_path = os.path.relpath(src_item, src_root)
            dest_item = os.path.join(dest_root, relative_path)

            # Ensure the destination directory exists.
            #os.makedirs(os.path.dirname(dest_item), exist_ok=True)
            try:
                server.print_progress_bar(
                    progress=copied_files,
                    total=total_files,
                    start_time=start_time
                )
                copied_files += 1
                #shutil.copy2(src_item, dest_item)
                print(f"Updated:", src_item, dest_item)
            except (FileExistsError, FileNotFoundError) as e:
                print(f"Error copying {src_item} to {dest_item}: {e}")
                continue

def apply_incremental_updates(updates_root: str, dest_root: str, update_folders: list) -> None:
    """
    Applies incremental updates by copying, for each file, the latest updated version
    from the update folders (sorted in descending order) to dest_root.

    For each file in the update folders:
      - Compute the file's path relative to the update folder.
      - Remove the first path element if necessary (for example, if the update folder's name
        is part of the relative path and should not be).
      - If the file has already been updated by a later (newer) update, skip it.
      - Otherwise, copy the file to the destination, ensuring that the directory structure is preserved.
    """
    # Set to track which relative paths have already been updated
    updated_files = set()

    # Process each update folder; update_folders is expected to be sorted (latest first)
    for _, date in enumerate(update_folders):
        # Build the full path to the update folder
        update_path: str = os.path.join(updates_root, str(date))
       
        # Walk through the update folder recursively
        for root, dirs, files in os.walk(update_path):
            for file in files:
                # Compute the file's relative path with respect to the update folder
                rel_path: str = os.path.relpath(os.path.join(root, file), update_path)
                # Optionally remove the first element of the relative path if it is redundant.
                # (For example, if the folder name is included and not needed.)
                rel_path = "/".join(rel_path.split('/')[1:])  

                # If this file (by its relative path) was already updated from a later update, skip it.
                if rel_path in updated_files:
                    continue

                # Compute the destination path by joining the destination root with the relative path.
                dest_item = os.path.join(dest_root, rel_path)
                print("Source/Destination:", os.path.join(root, file), dest_item)

                # Ensure that the destination directory exists.
                os.makedirs(os.path.dirname(dest_item), exist_ok=True)
                try:
                    # Copy the file from the update folder to the destination
                    shutil.copy2(os.path.join(root, file), dest_item)
                    # Mark this file as updated so that older versions won't overwrite it.
                    updated_files.add(rel_path)
                    print(f"Updated: {os.path.join(root, file)}", dest_item)
                except Exception as e:
                    print(f"Error updating {rel_path}: {e}")
                    continue


if __name__ == '__main__':
    restore_backup_home()



    # """
    #     Fx: /home/Desktop/audio.mp3 will be override by the latest "audio.mp3" file backup.
    #     For this, search from the latest dated folder to the oldest.
    #     If the file exists in the latest dated folder, it will be copied to the destination.
    #     Else, keep searching until find the file. If found, restore and continue to the next file.
    #     If not found in all backup dates, it will be skipped.
    # """