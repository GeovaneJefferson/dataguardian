# Data Guardian 🛡️

**Your personal, vigilant backup assistant for Linux desktops.**

Data Guardian is a powerful Python-based backup solution designed to keep your important files, settings, and applications safe with minimal effort. It combines an intelligent daemon, a modern GTK4-based GUI, and advanced backup strategies to deliver a seamless, reliable data protection experience.

---

⚠️ **Under Development:** Please note that Data Guardian is currently under active development. While it offers many features, it may still contain bugs or undergo significant changes. Use with caution, especially for critical data!

---

## ✨ Key Features

*   **Automatic & Incremental Backups:** Set-and-forget automation with efficient versioning.
*   **Smart & Selective Backup:** Tailor backups with exclusions, fast change detection using metadata and hashing.
*   **External Drive Integration:** Detects and backs up to your chosen external storage, checking for disk space.
*   **Robust Backup Integrity:** Ensures data accuracy with SHA-256 hashing and atomic file operations.
*   **Comprehensive Application Backup:** Saves lists of installed Flatpaks and backs up downloaded `.deb`/`.rpm` packages.
*   **Modern, User-Friendly GUI:** Intuitive control with GTK4 & Libadwaita for browsing, restoring, and configuring.
*   **Resilient & Configurable Daemon:** Handles system signals, device changes, and provides detailed logging.

---

## ⚙️ How Data Guardian Works: The Daemon Explained

The heart of Data Guardian is its **daemon**, a smart background process that works tirelessly to keep your data safe. Here's a breakdown of its key features and how they benefit you:

*   **Automatic & Scheduled Backups:**
    *   Once enabled, the daemon automatically wakes up at regular intervals (defaulting to every 5 minutes) to check for new or changed files. You don't need to remember to run backups; Data Guardian handles it for you.

*   **Intelligent File Scanning & Comparison:**
    *   **Efficient Folder Checks:** For top-level folders in your home directory, the daemon uses a local metadata cache (`.backup_meta.json` stored within the backup of that folder). This cache stores information like total size, file count, and the latest modification time. If this metadata hasn't changed, the daemon knows the folder's contents are likely the same and can skip a deep scan, saving time and resources.
    *   **Precise File Change Detection:** When a file needs checking, the daemon compares its current size and modification time against the backed-up version. If those differ, or if it's a new file, it performs a **SHA-256 hash comparison**. This cryptographic hash ensures that even the smallest change is detected, guaranteeing that your backups are accurate. This check is performed against both the main backup and existing incremental backups to determine if a new version is truly needed.

*   **Incremental and Main Backups:**
    *   **Full Initial Backup:** The first time Data Guardian backs up your files, it creates a complete copy in a `.main_backup` directory on your backup drive.
    *   **Space-Saving Incremental Updates:** For subsequent backups, only new files or files that have actually changed are copied. These changes are stored in timestamped folders (e.g., `DD-MM-YYYY/HH-MM`), creating a version history without duplicating unchanged data. This saves significant disk space and makes backups faster.

*   **Efficient and Resilient File Copying:**
    *   **CPU-Aware Concurrency:** The daemon intelligently adjusts how many files it copies simultaneously. It monitors your system's CPU load (`psutil.cpu_percent`) and reduces concurrency if the CPU is busy, preventing backups from slowing down your computer. When your system is less busy, it can use more resources to speed up the backup. This is managed using a `ThreadPoolExecutor` and an `asyncio.Semaphore`.
    *   **Atomic File Operations:** When copying a file, the daemon first writes it to a temporary (`.tmp`) file in the destination. Only after the copy is fully complete and verified (including an `os.fsync` to ensure data is written to disk) is the temporary file atomically renamed (`os.replace`) to its final backup name. This crucial step ensures that if an interruption occurs (like a power outage or drive disconnection) during a file copy, you won't be left with a corrupted or incomplete file in your backup.
    *   **Progress Reporting:** During file transfers, the daemon sends detailed progress messages (including filename, size, ETA, and percentage) to the UI via a socket, allowing you to monitor the backup in real-time.
    *   **Metadata Preservation:** File permissions and modification times are preserved from the source to the backup (`shutil.copystat`).

*   **Interruption Resilience:**
    *   If a backup cycle is interrupted, the daemon creates a special marker file (`.interrupted_main`). When it next runs and finds this file, it knows the previous backup might be incomplete and will initiate a full scan and backup process to ensure data integrity and resume operations.

*   **Disk Space Management:**
    *   Before copying any file, the daemon checks if there's enough free space on your backup drive, including a safety buffer (default 2GB). This helps prevent the backup process from failing due to a full disk.

*   **Automatic Backup of Downloaded Packages:**
    *   The daemon scans your `~/Downloads` folder for new `.deb` and `.rpm` package files. If new ones are found (i.e., not already present in the dedicated package backup location), they are automatically backed up, making it easier to restore your software setup.

*   **Backup Drive Monitoring & Permissions:**
    *   The daemon continuously checks if your designated backup drive is connected (`has_driver_connection()`) and writable (`is_backup_location_writable()`). Backups will only proceed if the drive is accessible, preventing errors and ensuring data is written correctly. If the location is not writable, a critical error is logged.

*   **Responsive System Signal Handling:**
    *   The daemon is designed to respond gracefully to system signals:
        *   `SIGTERM` / `SIGINT` (e.g., when you stop the service or press Ctrl+C): Initiates a clean shutdown, setting an exit flag.
        *   `SIGTSTP` (e.g., Ctrl+Z): Pauses the daemon's operations. A "daemon_suspended" message is sent to the UI.
        *   `SIGCONT`: Resumes operations after being paused. A "daemon_resumed" message is sent to the UI.

*   **Detailed Logging:**
    *   All significant actions, warnings, and errors are logged to `~/.dataguardian.log`. This file is invaluable for understanding the daemon's activity and for troubleshooting any issues.

*   **UI Communication:**
    *   The daemon sends status updates (e.g., "scanning" with current folder, "copying", "idle", "suspended", "summary_updated") and progress information for file transfers to the Data Guardian user interface via a local socket.

*   **PID File Management & Single Instance Guarantee:**
    *   To ensure only one instance of the daemon runs, it creates a Process ID (PID) file (`daemon.pid`) upon startup.
    *   It checks for stale PID files from previous, potentially crashed, runs and handles them.
    *   The `server.is_daemon_running()` function (used by the UI and autostart script) verifies if a process with the stored PID is active and matches the expected daemon command line, preventing multiple instances.

*   **Flexible Exclusion Options:**
    *   You can configure the daemon to ignore specific folders (absolute paths), hidden files/folders (globally via a switch), and files with certain extensions (like `.crdownload`, `.part`, `.tmp`) to tailor the backup to your needs. These settings are reloaded at the start of each backup cycle.

*   **Automatic Cleanup:**
    *   If an incremental backup session results in no files being copied (e.g., no changes were detected), the empty timestamped incremental folders (both `HH-MM` and the parent `DD-MM-YYYY` if it also becomes empty) are automatically removed to keep your backup directory tidy.

*   **Backup Summary Generation:**
    *   After a successful backup session that involves copying files, the daemon invokes `generate_backup_summary.py`. This script creates/updates `.backup_summary.json` in the backup drive, containing statistics about file categories (images, videos, documents, others) and lists of most frequently backed-up files. The UI uses this summary for its overview cards and suggested files. A "summary_updated" message is sent to the UI upon completion.

---

## ⚙️ How Data Guardian Works (Simplified User Journey)

1.  **Effortless Initial Setup:**
    *   Launch the GUI and select your preferred external drive for backups.
    *   Customize your backup strategy: enable automatic backups, specify any folders or file types to ignore, and adjust other settings to your liking.

2.  **The Guardian Daemon: Your Automated Protector:**
    *   **Initial Safeguard:** When first activated (or after setup), the daemon performs a comprehensive full scan of your home directory and creates the initial complete backup in the `.main_backup` folder on your chosen drive.
    *   **Constant Vigilance, Minimal Impact:** The daemon then runs quietly in the background, periodically rescanning your home directory. It cleverly uses cached metadata to rapidly detect any new or modified files without bogging down your system.
    *   **Keeping Your Main Backup Current:** Any brand-new files are efficiently copied to your `.main_backup`.
    *   **Smart Incremental Updates for Version History:** When files are modified, Data Guardian doesn't overwrite your main backup. Instead, it saves these updated versions into separate, clearly timestamped incremental folders. This approach saves significant disk space and gives you a powerful version history, allowing you to roll back to previous states of your files.
    *   **Application Blueprint:** It also diligently keeps an up-to-date list of your installed Flatpak applications and backs up downloaded `.deb`/`.rpm` packages, making it much easier to restore your software environment.

3.  **Restoring Your Data: Simple, Flexible, and Fast:**
    *   **Navigate Your Backup History:** The user-friendly GUI provides a clear view of all your backup snapshots – both the main backup and all incremental versions. Finding what you need is straightforward.
    *   **Pinpoint Recovery or Full System Rollback:** Whether you need to recover a single accidentally deleted file or perform a comprehensive system-wide restore (including applications and home directory data after an OS reinstall), Data Guardian offers the flexibility you need.
    *   **Confirm Before You Commit:** For added confidence, you can preview common file types directly within the GUI before initiating a restore, ensuring you're recovering exactly what you intend.

---

## 🛠️ Tech Stack

*   **Python 3**
*   **GTK4 & Libadwaita:** Native Linux desktop UI.
*   **Asyncio & `concurrent.futures.ThreadPoolExecutor`:** Efficient, non-blocking operations and parallel file copying for the daemon.
*   **Standard Libraries:** `os`, `shutil`, `hashlib`, `json`, `logging`, `signal`, `tempfile`, `socket`, `configparser`, `datetime`, `subprocess`, `psutil`.
*   **Third-party:** `setproctitle` for daemon process naming.

---

## 🚀 Getting Started

### Prerequisites

*   Python 3.8+
*   GTK4 & Libadwaita (e.g., `gir1.2-gtk-4.0`, `libadwaita-1-0` on Debian/Ubuntu based systems)
*   Python GObject bindings (`python3-gi`, `python3-gi-cairo`)
*   `psutil` (install with `pip install psutil`)
*   `setproctitle` (install with `pip install setproctitle`)

### Installation

Data Guardian is intended to be installed as a Flatpak for the best user experience.

**1. Via Flatpak (Recommended)**

   *(Note: Flatpak manifest and build instructions are under development. Once available, you will typically build and install it locally as follows. For official releases, it might be available on Flathub or another repository.)*

   First, ensure you have `flatpak` and `flatpak-builder` installed on your system.

   Clone the repository (if you haven't already):
   ```bash
   git clone https://github.com/geovanejefferson/dataguardian.git 
   cd dataguardian
