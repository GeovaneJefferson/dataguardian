from server import *
from check_package_manager import check_package_manager

serverMain = SERVER()

def restore_packages_applications():
	print("Installing applications packages...")
	
	if check_package_manager() == 'deb':
		restore_deb_applications()
	elif check_package_manager() == 'rpm':
		restore_rpm_applications()

def restore_deb_applications():
	for package in os.listdir(serverMain.deb_main_folder()):
		package_location = os.path.join(serverMain.deb_main_folder(), package)

		print(f"Installing package: {package_location}")
		process = sub.run(
			['dpkg', '-i', package_location],
				stdout=sub.PIPE,
				stderr=sub.PIPE,
				text=True)

		if process.returncode == 0:
			print(f"Package {package} installed successfully.")
		else:
			print(f"Error installing package {package}: {process.stderr}")

		# Fix packages installation using pkexec
		sub.run(
			['apt', '--fix-broken', 'install'],
			stdout=sub.PIPE,
			stderr=sub.PIPE,
			text=True)

def restore_rpm_applications():
	for package in os.listdir(serverMain.rpm_main_folder()):
		package_location = os.path.join(serverMain.rpm_main_folder(), package)

		print(f"Installing package: {package_location}")
		process = sub.run(
			['yes', '|', 'rpm', '-ivh', '--replacepkgs', package_location],
				stdout=sub.PIPE,
				stderr=sub.PIPE,
				text=True)

		if process.returncode == 0:
			print(f"Package {package} installed successfully.")
		else:
			print(f"Error installing package {package}: {process.stderr}")


if __name__ == '__main__':
	pass