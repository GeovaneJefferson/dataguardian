from server import *

def check_package_manager():
    # Check if dpkg command exists
    dpkg_exists = sub.call(
		["which", "dpkg"],
		stdout=sub.DEVNULL, 
		stderr=sub.DEVNULL) == 0
    
    # Check if rpm command exists
    rpm_exists = sub.call(
		["which", "rpm"],
		stdout=sub.DEVNULL, 
		stderr=sub.DEVNULL) == 0

    if dpkg_exists:
        return "deb"
    elif rpm_exists:
        return "rpm"
    else:
        return None


if __name__ == '__main__':
	pass