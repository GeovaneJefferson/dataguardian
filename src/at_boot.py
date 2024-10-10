from server import *
import subprocess as sub
import time
import logging

server = SERVER()

def at_boot():
    try:
        # Get the driver location from the database
        driver_name: str = server.get_database_value(
            section='DRIVER', 
            option='Driver_Location'
        )
        
        if driver_name is not None:
            # Check if automatic backup is enabled
            automatically_backup: str = server.get_database_value(
                section='BACKUP', 
                option='automatically_backup'
            )
            
            if automatically_backup:
                # Check if daemon is already running
                if not server.is_daemon_running():
                    # Set the correct path to the daemon script
                    daemon_script_path = server.DAEMON_PY_LOCATION
                    # logging.info(f"Daemon script path: {daemon_script_path}")

                    # Start the backup checker
                    process = sub.Popen(
                        ['python3', daemon_script_path],
                        stdout=sub.PIPE,
                        stderr=sub.PIPE
                    )

                    # Store the new PID in the file
                    with open(server.DAEMON_PID_LOCATION, 'w') as f:
                        f.write(str(process.pid))
                        
                    # Log the process ID of the started daemon
                    logging.info(f"Daemon started with PID: {process.pid}")
                else:
                    logging.info("Daemon is already running, not starting again.")
    except Exception as e:
        logging.error(f"Error in at_boot: {e}")


if __name__ == "__main__":
    time.sleep(1)  # Delay startup for 1 second
    at_boot()