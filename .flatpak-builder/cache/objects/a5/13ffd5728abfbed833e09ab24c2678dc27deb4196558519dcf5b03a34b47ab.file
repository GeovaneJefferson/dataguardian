from server import *
from check_package_manager import check_package_manager

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

serverMain = SERVER()

def restore_packages_applications():
    """Restores applications based on the detected package manager."""
    logging.info("Installing application packages...")

    package_manager = check_package_manager()
    if package_manager == 'deb':
        restore_deb_applications()
    elif package_manager == 'rpm':
        restore_rpm_applications()
    else:
        logging.error("Unsupported package manager detected.")
        return

def restore_deb_applications():
    """Restores .deb packages."""
    deb_folder = serverMain.deb_main_folder()

    # Check if the folder exists
    if not os.path.exists(deb_folder):
        logging.error(f"Debian package folder not found: {deb_folder}")
        return

    for package in os.listdir(deb_folder):
        package_location = os.path.join(deb_folder, package)

        logging.info(f"Installing package: {package_location}")
        process = run_command(['dpkg', '-i', package_location])

        if process.returncode == 0:
            logging.info(f"Package {package} installed successfully.")
        else:
            logging.error(f"Error installing package {package}: {process.stderr}")

        # Fix broken dependencies
        logging.info("Fixing broken dependencies...")
        run_command(['apt', '--fix-broken', 'install'])

def restore_rpm_applications():
    """Restores .rpm packages."""
    rpm_folder = serverMain.rpm_main_folder()

    # Check if the folder exists
    if not os.path.exists(rpm_folder):
        logging.error(f"RPM package folder not found: {rpm_folder}")
        return

    for package in os.listdir(rpm_folder):
        package_location = os.path.join(rpm_folder, package)

        logging.info(f"Installing package: {package_location}")
        process = run_command(['rpm', '-ivh', '--replacepkgs', package_location])

        if process.returncode == 0:
            logging.info(f"Package {package} installed successfully.")
        else:
            logging.error(f"Error installing package {package}: {process.stderr}")

def run_command(command):
    """
    Runs a shell command and returns the completed process.

    Args:
        command (list): The command to run as a list of arguments.

    Returns:
        subprocess.CompletedProcess: The result of the command execution.
    """
    try:
        return sub.run(command, stdout=sub.PIPE, stderr=sub.PIPE, text=True)
    except Exception as e:
        logging.error(f"Error running command {command}: {e}")
        return sub.CompletedProcess(args=command, returncode=1, stdout='', stderr=str(e))

if __name__ == '__main__':
    restore_packages_applications()