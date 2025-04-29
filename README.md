# **Data Guardian**

**Data Guardian** is a powerful and user-friendly backup tool designed specifically for **Linux users**. It ensures your data is always protected by continuously monitoring your files for changes and performing real-time backups. With version management and easy restoration, **Data Guardian** provides peace of mind for your important files.

---

## **Features**

- **Version Backup:** Maintain multiple versions of your files, enabling easy restoration of previous states.
- **Continuous File Monitoring:** Automatically detects new or updated files and performs immediate backups.
- **Real-Time Backup:** Ensures your data is always up to date by backing up files as they are modified or added.
- **Backup Resumption:** Automatically resumes interrupted backups after shutdown, restart, or sleep.
- **Version Management:** Tracks file versions, allowing users to restore previous versions effortlessly.
- **Customizable Exclusions:** Exclude specific folders or hidden files from backups.
- **Cross-Platform Support:** Works seamlessly with both `.deb` and `.rpm` package managers.
- **Flatpak Integration:** Supports Flatpak applications for backup and restoration.

---

## **How It Works**

1. **Data Processing:** Continuously monitors file changes (e.g., timestamps, folder access, file sizes) to identify new or updated files.
2. **Version Management:** Automatically tracks file versions, ensuring easy restoration of previous states.
3. **Backup State Management:** Saves the backup state in the database, ensuring all changes are reflected in the backup history.
4. **Restore Functionality:** Allows users to restore files or applications from backups with a user-friendly interface.

---

## **Installation**

To install **Data Guardian**, use the following command:
Terminal:
$ flatpak-builder --force-clean --user --install repo com.gnome.dataguardian.yaml 

