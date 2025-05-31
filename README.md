# Data Guardian

**Data Guardian** is a powerful, user-friendly backup tool for **Linux**. It keeps your data safe by monitoring your files for changes and performing automatic, versioned backups. With easy restoration and robust version management, Data Guardian gives you peace of mind for your important files.

---

## Features

- **Versioned Backups:** Maintain multiple versions of your files for easy restoration.
- **Continuous Monitoring:** Detects new or updated files automatically.
- **Automatic Backup Resumption:** Resumes interrupted backups after shutdown, restart, or sleep.
- **Customizable Exclusions:** Exclude specific folders or hidden files from backups.
- **Cross-Platform Support:** Works with both `.deb` and `.rpm` package managers.
- **Flatpak Integration:** Backs up and restores Flatpak applications.
- **User-Friendly Interface:** Restore files or previous versions with a simple UI.

---

## How It Works

1. **Monitoring:** Scans your files for changes (timestamps, sizes, etc.) to identify new or updated files.
2. **Version Management:** Tracks file versions, allowing you to restore previous states.
3. **Backup State Management:** Saves backup state in a database for reliable history.
4. **Restore:** Restore files or applications from backups using the graphical interface.

---

## Installation

### Flatpak

```sh
flatpak-builder --force-clean --user --install repo com.gnome.dataguardian.yaml
```

### From Source

```sh
git clone https://github.com/youruser/dataguardian.git
cd dataguardian
pip install -r requirements.txt
python3 src/main.py
```

---

## Usage

- Launch Data Guardian from your applications menu or with `python3 src/main.py`.
- Configure backup locations and exclusions in the settings.
- Use the UI to restore files or previous versions.

---

## Troubleshooting

- **Device not detected:** Ensure your backup device is mounted and accessible.
- **Permission errors:** Run with appropriate permissions or adjust device access.
- **Logs:** Check the log file (see settings) for detailed error messages.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Contributing

Pull requests and issues are welcome!
