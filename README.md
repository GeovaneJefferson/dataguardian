# Data Guardian 🛡️

**Your personal, vigilant backup assistant for Linux desktops.**

Data Guardian is a powerful Python-based backup solution designed to keep your important files, settings, and applications safe with minimal effort. It combines an intelligent daemon, a modern GTK4-based GUI, and advanced backup strategies to deliver a seamless, reliable data protection experience.

---

## ✨ Key Features

- **Automatic & Incremental Backups**
  - Persistent daemon monitors your home directory and external drives, backing up data automatically on your schedule.
  - Initial full backup stored in `.main_backup`.
  - Subsequent changes saved as incremental backups in date- and time-stamped folders, optimizing storage and recovery.

- **Smart & Selective Backup**
  - Configurable exclusions for directories, file types, and hidden files.
  - Uses metadata caching per folder (`.backup_meta.json`) to detect changes efficiently and minimize scanning overhead.
  - Skips unchanged folders automatically to speed up backups.

- **External Drive Integration**
  - Detects and backs up to your selected external storage device.
  - Checks for sufficient disk space before every copy operation.

- **Robust Backup Integrity**
  - Uses SHA-256 file hashing and file size/modification time checks to accurately identify updated files.
  - Handles backup interruptions gracefully and resumes without data loss.
  - Concurrent file copying with `ProcessPoolExecutor` for high throughput.
  - Non-blocking async design ensures smooth system performance.

- **Comprehensive Application Backup**
  - Saves a list of installed Flatpak applications regularly.
  - *(Work in Progress)* Plans to backup `.deb` and `.rpm` packages for full environment restoration.

- **Modern, User-Friendly GUI**
  - Built with GTK4 and Adwaita for a polished, native Linux experience.
  - Browse and restore individual files from `.main_backup` and incremental snapshots.
  - System Restore feature to recover applications, Flatpaks, and home directory data post-OS reinstall.
  - File preview support for common formats, including PDF and text.
  - Manage backup settings: device selection, auto-backup toggle, ignored folders, and more.

- **Resilient & Configurable Daemon**
  - Signal handling for pause, resume, and graceful shutdown.
  - Responsive to device connection changes.
  - Configurable concurrency and wait intervals.
  - Detailed logging to file and console.

---

## ⚙️ How Data Guardian Works (Simplified)

1. **Setup via GUI**
   - Select backup drive.
   - Configure auto-backup, ignored folders, and other preferences.

2. **Daemon Operation**
   - On start, performs a full scan and backup to `.main_backup`.
   - Periodically rescans home directory using cached metadata to detect changes.
   - Copies new files to `.main_backup`.
   - Stores updated files in timestamped incremental folders for versioning.
   - Saves installed Flatpak app list for easy restoration.

3. **File Restoration**
   - GUI allows browsing backup snapshots.
   - Restore individual files or run a system-wide restore.
   - Preview files before restoring.

---

## 🛠️ Tech Stack

- **Python 3**
- **GTK4 & Libadwaita:** Native Linux desktop UI.
- **Asyncio & Concurrent Futures:** Efficient, non-blocking operations and parallel file copying.
- **Standard Libraries:** `os`, `shutil`, `hashlib`, `json`, `logging`, `signal`, `tempfile`
- **Third-party:** `setproctitle` for process naming.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- GTK4 & Libadwaita (e.g., `gir1.2-gtk-4.0`, `libadwaita-1-0`)
- Python GObject bindings (`python3-gi`, `python3-gi-cairo`)
- `setproctitle` (install with `pip install setproctitle`)
- Optional for PDF preview: Poppler and its introspection bindings (`gir1.2-poppler-0.18`)

### Installation

Clone or download the repository, then install dependencies as needed.

### Running the GUI

```bash
cd /path/to/dataguardian/src
python3 main.py

