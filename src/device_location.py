from server import *

server = SERVER()

def device_location():
    media_path = f'{server.MEDIA}/{server.USERNAME}'
    run_path = f'{server.RUN}/{server.USERNAME}'

    try:
        # Check for devices in MEDIA
        if os.path.exists(media_path) and os.listdir(media_path):
            return '/media'
    except FileNotFoundError:
        pass  # MEDIA path does not exist or no devices found

    try:
        # Check for devices in RUN if MEDIA is empty or not available
        if os.path.exists(run_path) and os.listdir(run_path):
            return '/run'
        
    except FileNotFoundError:
        pass  # RUN path does not exist or no devices found

    print("No devices found.")
    return None  # No devices found in either MEDIA or RUN


if __name__ == '__main__':
     pass
