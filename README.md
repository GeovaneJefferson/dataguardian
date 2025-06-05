# Data Guardian 🛡️

**Your personal, vigilant backup assistant for Linux desktops.**

Data Guardian is a Python-based application designed to provide a robust and user-friendly backup solution. It helps you safeguard your important files, application settings, and even system packages, ensuring you can recover your data and environment when needed.

## ✨ Features

*   **Automatic Backups:** A persistent daemon monitors your files and backs them up automatically based on your schedule and configuration.
*   **Selective Backup:**
    *   Backup your home directory, with options to exclude specific folders and hidden files.
    *   Intelligent folder scanning: Uses metadata to quickly identify changes in large directories, minimizing scan times.
*   **External Drive Support:** Easily configure backups to your preferred external storage device.
*   **Incremental Backups:**
    *   Initial full backup to a `.main_backup` directory.
    *   Subsequent changes are stored in date and time-stamped incremental backup folders, saving space and time.
*   **Application & Package Backup:**
    *   Saves a list of installed Flatpak applications.
    *   (Planned/WIP) Backs up `.deb` and `.rpm` packages.
*   **User-Friendly GUI:**
    *   Built with GTK4 and Adwaita for a modern Linux desktop experience.
    *   Browse backup versions and restore individual files.
    *   "System Restore" feature to restore applications, Flatpaks, and home directory files (useful after a fresh OS install).
    *   Manage backup settings, including device selection, automatic backup toggle, and ignored folders.
    *   File preview for common file types directly in the UI.
*   **Resilient:**
    *   Handles backup interruptions and aims to resume gracefully.
    *   Checks for sufficient disk space before copying.
*   **Efficient:**
    *   Uses `asyncio` for non-blocking operations in the daemon.
    *   Concurrent file copying using `ProcessPoolExecutor`.
    *   File hashing (SHA-256) to accurately detect updated files.

## ⚙️ How It Works (Simplified)

1.  **Configuration:** You select a backup drive and configure settings through the GUI (e.g., enable automatic backups, specify folders to ignore).
2.  **Daemon (`daemon_new.py`):** If automatic backup is enabled, a background daemon starts.
   *   **Initial Scan & Backup:** Performs a full backup of your home directory (respecting exclusions) to a special `.main_backup` folder on your backup device. It also stores metadata (`.backup_meta.json`) for each top-level folder to optimize future scans.
   *   **Monitoring & Incremental Backups:** Periodically, the daemon rescans your home directory.
        *   It first checks folder metadata (total files, total size, latest modification time) against the cached metadata. If a folder's metadata hasn't changed, it skips a deep scan of that folder.
        *   For changed folders or new files:
            *   New files are copied to the `.main_backup` directory.
            *   Updated files are copied to a new, timestamped directory (e.g., `DD-MM-YYYY/HH-MM/`) within your backup location. This preserves the `.main_backup` as a clean base and stores versions of changed files.
    *   **Flatpaks:** The names of installed Flatpak applications are regularly saved.
3.  **GUI (`ui.py`):**
    *   Allows you to browse files in your `.main_backup` and any incremental backup folders.
    *   You can restore individual files to their original locations.
    *   The "System Restore" feature helps in restoring applications and your home directory data.

## 🛠️ Tech Stack

*   **Python 3**
*   **GTK4 & Adwaita:** For the graphical user interface.
*   **SQLite (implicitly via `configparser` for now, but good to note if DB is planned):** For storing application settings.
*   Standard Python libraries: `os`, `shutil`, `subprocess`, `asyncio`, `concurrent.futures`, `hashlib`, `json`, `logging`.

## 🚀 Getting Started

(This section would typically include installation and setup instructions. As it's a local project, you might want to detail how to run it.)

1.  **Prerequisites:**
    *   Python 3.x
    *   GTK4 and Adwaita libraries (e.g., `gir1.2-gtk-4.0`, `libadwaita-1-0` on Debian/Ubuntu).
    *   `python3-gi`, `python3-gi-cairo`
    *   `setproctitle` (Python package: `pip install setproctitle`)
    *   (Optional, for PDF previews) Poppler and its GObject introspection bindings (e.g., `gir1.2-poppler-0.18`).

2.  **Running the Application:**
    ```bash
    cd /path/to/dataguardian/src
    python3 main.py
    ```

3.  **Running the Daemon (for automatic backups):**
    The GUI can start the daemon when "Enable Automatic Backups" is turned on in settings.
    Alternatively, you can run it manually (primarily for development):
    ```bash
    cd /path/to/dataguardian/src
    python3 daemon.py
    ```
    *Note: The application is designed to manage the daemon's lifecycle via `at_boot.py` and the settings UI.*

## 🔮 Future Ideas

*   Encryption for backups.
*   Cloud storage integration.
*   More detailed progress reporting during backup/restore.
*   Snapshot management within the UI.
*   Support for backing up system configuration files (e.g., `/etc`).
*   Packaging for easier distribution (e.g., Flatpak, Snap, .deb/.rpm).

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Please feel free to check the issues page (replace with your actual repo link).

## 📜 License

This project is licensed under the **GPLv3 License** - see the `LICENSE` file for details.

