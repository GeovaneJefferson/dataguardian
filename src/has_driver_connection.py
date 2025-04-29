from server import *

# Initialize the server instance
server = SERVER()

def has_driver_connection() -> bool:
    """
    Checks if there is a connection to the backup driver.

    Returns:
        bool: True if the backup driver is connected, False otherwise.
    """
    try:
        # Retrieve the driver location from the database
        driver_location: str = server.get_database_value(
            section='DRIVER', 
            option='driver_location'
        )
        logging.info(f"Driver location retrieved: {driver_location}")
    except Exception as e:
        # Log an error if the driver location cannot be retrieved
        logging.error(f"Error reading driver location from database: {e}")
        return False

    # Check connection to the backup driver
    if os.path.exists(driver_location):
        logging.info(f"Connection to backup driver established: {driver_location}")
        return True  # Connection exists
    else:
        logging.warning(f"No connection to backup driver: {driver_location}")
        return False  # No connection


if __name__ == '__main__':
    # Example usage
    if has_driver_connection():
        logging.info("Backup driver is connected.")
    else:
        logging.error("Backup driver is not connected.")