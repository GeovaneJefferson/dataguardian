# Data Guardian 🛡️

**Your personal, vigilant backup assistant for Linux desktops.**

Data Guardian is a powerful Python-based backup solution designed to keep your important files, settings, and applications safe with minimal effort. It combines an intelligent daemon, a modern GTK4-based GUI, and advanced backup strategies to deliver a seamless, reliable data protection experience.

---

⚠️ **Under Development:** Please note that Data Guardian is currently under active development. While it offers many features, it may still contain bugs or undergo significant changes. Use with caution, especially for critical data!

---

## ✨ Key Features
- **Automatic & Incremental Backups: Effortless, Continuous Protection**
  - **Set-and-Forget Automation:** A vigilant daemon continuously monitors your home directory and connected external drives, automatically backing up your precious data according to your schedule. No manual intervention required!
  - **Efficient Versioning & Storage:** After an initial comprehensive backup (to `.main_backup`), Data Guardian intelligently saves only the changes as incremental backups in clearly organized, date- and time-stamped folders. This optimizes storage space and makes restoring specific versions a breeze.

- **Smart & Selective Backup: You're in Control**
  - **Tailored to Your Needs:** Easily configure exclusions for specific directories, file types, or even hidden files, ensuring Data Guardian protects exactly what matters most to you.
  - **Lightning-Fast Change Detection:** Say goodbye to lengthy scans! Data Guardian uses smart metadata caching (`.backup_meta.json` per folder) to instantly identify changes, drastically reducing scanning overhead.
  - **Optimized Performance:** Unchanged folders are intelligently skipped, making your backup process faster and more efficient.

- **External Drive Integration**
  - Detects and backs up to your selected external storage device.
  - Checks for sufficient disk space before every copy operation.

- **Robust Backup Integrity: Data You Can Trust**
  - **Unyielding Data Accuracy:** Your data's integrity is paramount. Data Guardian employs SHA-256 file hashing along with file size and modification time checks to precisely identify every new or modified file, ensuring your backups are always accurate.
  - **Resilient to Interruptions:** Life happens. Data Guardian is designed to handle backup interruptions gracefully, capable of resuming without any data loss, ensuring your backup process is robust and reliable.
  - **High-Speed Transfers & Seamless Performance:** Leveraging `ProcessPoolExecutor` for concurrent file copying achieves high throughput. Its non-blocking asynchronous design means Data Guardian works quietly in the background, ensuring your system's performance remains smooth and responsive, even during backup operations.

- **Comprehensive Application Backup: Restore Your Full Environment**
  - **Beyond Just Files:** Data Guardian regularly saves a list of your installed Flatpak applications, simplifying the process of getting your system back up and running.
  - *(Work in Progress)* Plans to backup `.deb` and `.rpm` packages for full environment restoration.

- **Modern, User-Friendly GUI: Intuitive Control Center**
  - **Polished Native Experience:** Enjoy a sleek interface built with GTK4 and Libadwaita, offering a polished, native Linux experience.
  - **Effortless File Recovery:** Easily browse through your `.main_backup` and all incremental snapshots. Restore individual files or entire folders with just a few clicks.
  - **Powerful System Restore:** Facing an OS reinstall? Data Guardian's System Restore feature helps you quickly recover your applications (including Flatpaks), and your entire home directory data, minimizing downtime.
  - **Preview Before Restoring:** Quickly preview common file formats like PDF and text directly within the application, ensuring you restore the correct version every time.
  - **Complete Configuration:** Easily manage all your backup preferences: select your backup device, toggle auto-backup, define ignored folders, and fine-tune other settings to match your workflow.

- **Resilient & Configurable Daemon: Advanced Control**
  - Signal handling for pause, resume, and graceful shutdown.
  - Responsive to device connection changes.
  - Configurable concurrency and wait intervals.
  - Detailed logging to file and console.

---
## ⚙️ How Data Guardian Works (Simplified)

1. **Effortless Initial Setup**
   - Simply launch the GUI and select your preferred external drive for backups.
   - Customize your backup strategy: enable automatic backups, specify any folders or file types to ignore, and adjust other settings to your liking.

2. **The Guardian Daemon: Your Automated Protector**
   - **Initial Safeguard:** When first activated (or after setup), the daemon performs a comprehensive full scan of your home directory and creates the initial complete backup in the `.main_backup` folder on your chosen drive.
   - **Constant Vigilance, Minimal Impact:** The daemon then runs quietly in the background, periodically rescanning your home directory. It cleverly uses cached metadata to rapidly detect any new or modified files without bogging down your system.
   - **Keeping Your Main Backup Current:** Any brand-new files are efficiently copied to your `.main_backup`.
   - **Smart Incremental Updates for Version History:** When files are modified, Data Guardian doesn't overwrite your main backup. Instead, it saves these updated versions into separate, clearly timestamped incremental folders. This approach saves significant disk space and gives you a powerful version history, allowing you to roll back to previous states of your files.
   - **Application Blueprint:** It also diligently keeps an up-to-date list of your installed Flatpak applications, making it much easier to restore your software environment.

3. **Restoring Your Data: Simple, Flexible, and Fast**
   - **Navigate Your Backup History:** The user-friendly GUI provides a clear view of all your backup snapshots – both the main backup and all incremental versions. Finding what you need is straightforward.
   - **Pinpoint Recovery or Full System Rollback:** Whether you need to recover a single accidentally deleted file or perform a comprehensive system-wide restore (including applications and home directory data after an OS reinstall), Data Guardian offers the flexibility you need.
   - **Confirm Before You Commit:** For added confidence, you can preview common file types directly within the GUI before initiating a restore, ensuring you're recovering exactly what you intend.

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

Data Guardian is intended to be installed as a Flatpak for the best user experience.

**1. Via Flatpak (Recommended)**

   *(Note: Flatpak manifest and build instructions are under development. Once available, you will typically build and install it locally as follows. For official releases, it might be available on Flathub or another repository.)*

   First, ensure you have `flatpak` and `flatpak-builder` installed on your system.

   Clone the repository (if you haven't already):
   ```bash
   git clone https://github.com/yourusername/dataguardian.git
   cd dataguardian
   ```

   Then, navigate to the directory containing the Flatpak manifest (e.g., `build-aux/` or the project root if the manifest is there) and run:
   ```bash
   flatpak-builder --force-clean --user --install builddir <your-app-id>.yaml
   # Replace <your-app-id>.yaml with the actual manifest file name, e.g., com.github.yourusername.dataguardian.yaml
   ```

**2. Manual Installation (for development or testing)**

   Clone the repository:
   ```bash
   git clone https://github.com/yourusername/dataguardian.git
   cd dataguardian
   ```
   Install Python dependencies (preferably in a virtual environment):
   ```bash
   # python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
   Ensure system dependencies listed in "Prerequisites" are met.

### Running the GUI

After manual installation (if it includes desktop integration steps), the app may appear in your system's main application menu.
