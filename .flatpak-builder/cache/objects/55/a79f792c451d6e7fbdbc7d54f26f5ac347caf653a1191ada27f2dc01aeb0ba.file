from server import *

server = SERVER()

def has_driver_connection():
    try:
        # INI
        driver_location: str = server.get_database_value(
            section='DRIVER', 
            option='driver_location')
    except Exception as e:
        logging.error(f"Error reading: {e}")
        return False

    # Check conenction to the backup driver
    if os.path.exists(driver_location):
        # print(f"\033[92m[✓]\033[0m Connection to: {driver_location}")
        return True  # Has connection
    else:
        # print(f"\033[91m[X]\033[0m Connection to: {driver_location}")
        return False  # Has no connection