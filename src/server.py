import getpass
import os
import pathlib
import subprocess as sub
import configparser
import shutil
import time
import sys
import signal
import asyncio
import threading
from threading import Timer
import multiprocessing
import locale
import sqlite3
import logging
import traceback
import socket
import errno
import setproctitle
import csv
import random
import platform
import inspect
import gi
import json
import fnmatch
import hashlib
import stat

from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GdkPixbuf


# Ignore SIGPIPE signal, so that the app doesn't crash
signal.signal(signal.SIGPIPE, signal.SIG_IGN)


class SERVER:
	def __init__(self):
		self.failed_backup: list = []
		# Format the current date and time to get the day name
		self.DAY_NAME: str = datetime.now().strftime("%A").upper().strip()  # SUNDAY, MONDAY...

		# List of file extensions that can be used for generating thumbnails or previews
		self.thumbnails_extensions_list = [
			".png",  # PNG image files
			".jpg",  # JPEG image files
			".jpeg", # JPEG image files
			".gif",  # GIF image files
			".bmp",  # Bitmap image files
			".webp", # WebP image files
			".tiff", # TIFF image files
			".svg",  # SVG image files (note: may require additional handling)
			".ico",  # Icon files
			".mp4",  # Video files (previews)
			".avi",  # AVI video files
			".mov",  # MOV video files
			".pdf",  # PDF documents (may require special handling like Poppler to render)
			".docx", # Word documents (requires a library to render previews)
			".txt",  # Text files
			".xlsx", # Excel files (requires libraries like OpenPyXL to render)
			".pptx", # PowerPoint files (requires libraries like python-pptx to render)
		]

		################################################################################
		# APP SETTINGS
		################################################################################
		self.ID: str = "com.gnome.dataguardian"
		self.APP_NAME: str = "Data Guardian"
		self.APP_NAME_CLOSE_LOWER: str = "dataguardian"
		self.APP_VERSION: str = "v0.1 dev"
		self.BACKUPS_LOCATION_DIR_NAME: str = "backups"  # Where backups will be saved
		self.APPLICATIONS_LOCATION_DIR_NAME: str = "applications"

		################################################################################
		# DRIVER LOCATION
		################################################################################
		self.MEDIA: str = "/media"
		self.RUN: str = "/run/media"
		self.MAIN_BACKUP_LOCATION: str = '.main_backup'

		################################################################################
		# SYSTEM
		################################################################################
		self.GET_USERS_DE: str = "XDG_CURRENT_DESKTOP"
		self.GET_USERS_PACKAGE_MANAGER: str = "cat /etc/os-release"
		self.USER_HOME: str = os.path.expanduser("~")  # Get user's home directory

		################################################################################
		# HOME SYSTEM LOCATIONS
		################################################################################
		self.HOME_USER: str = Path.home()
		self.USERNAME = getpass.getuser()
		self.GET_HOME_FOLDERS: str = os.listdir(self.HOME_USER)
		self.GET_CURRENT_LOCATION = pathlib.Path().resolve()

		################################################################################
		# FLATPAK
		################################################################################
		# self.GET_FLATPAKS_APPLICATIONS_NAME: str = 'flatpak list --app --columns=application'
		self.GET_FLATPAKS_APPLICATIONS_NAME = 'flatpak-spawn --host flatpak list --app --columns=application'
		self.FLATPAK_SH_DST: str = f'~/.var/app/{self.ID}/config/list_flatpaks.sh'

		################################################################################
		# LOCATIONS
		################################################################################
		self.CONF = configparser.ConfigParser()
		self.CONF_LOCATION: str = os.path.join(Path.home(), '.var', 'app', self.ID, 'config', 'config.conf')
		self.autostart_file: str = os.path.expanduser(f"~/.config/autostart/{self.APP_NAME.lower()}_autostart.desktop")

		if not os.path.exists(self.CONF_LOCATION):
			self.create_and_move_files_to_users_home()

		if os.path.exists(self.CONF_LOCATION):
			self.CONF.read(self.CONF_LOCATION)
		else:
			print(f"Config file {self.CONF_LOCATION} not found!")

		# DRIVER Section
		self.DRIVER_NAME = self.get_database_value(
			section='DRIVER',
			option='driver_name')

		self.DRIVER_LOCATION = self.get_database_value(
			section='DRIVER',
			option='driver_location')

		self.AUTOMATICALLY_BACKUP = self.get_database_value(
			section='BACKUP',
			option='automatically_backup')

		self.BACKING_UP = self.get_database_value(
			section='BACKUP',
			option='backing_up')

		# LOG FILE
		# self.LOG_LOCATION: str = os.path.join(self.create_base_folder(), f'{self.APP_NAME_CLOSE_LOWER}.log')
		self.LOG_LOCATION: str = os.path.join(Path.home(), '.var', 'app', self.ID, 'config', f'{self.APP_NAME_CLOSE_LOWER}.log')
		# self.REMAINING_FILES_LOCATION: str = os.path.join(self.create_base_folder(), 'remaining_files.json')
		self.INTERRUPTED_MAIN: str = os.path.join(Path.home(), '.var', 'app', self.ID, 'config', '.interrupted_main')
		self.INTERRUPTED_UPDATE: str = os.path.join(Path.home(), '.var', 'app', self.ID, 'config', '.interrupted_update')

		# DAEMON PID
		# self.DAEMON_PY_LOCATION: str = 'src/daemon.py'
		# self.DAEMON_PID_LOCATION: str = os.path.join(self.create_base_folder(), 'daemon.pid')
		# Flatpak
		# self.DAEMON_PY_LOCATION: str = os.path.join(Path.home(), '.var', 'app', self.ID, 'src', 'daemon.py')
		self.DAEMON_PY_LOCATION: str = os.path.join('/app/share/dataguardian/src', 'daemon.py')
		self.DAEMON_PID_LOCATION: str = os.path.join(Path.home(), '.var', 'app', self.ID, 'config', 'daemon.pid')

	def create_and_move_files_to_users_home(self):
		# Create the directory if it doesn't exist
		config_dir = os.path.dirname(self.CONF_LOCATION)
		os.makedirs(config_dir, exist_ok=True)

		# Write default config values
		self.CONF['BACKUP'] = {
			'automatically_backup': 'false',
			'backing_up': 'false',
			'first_startup': 'false'
		}

		self.CONF['DRIVER'] = {
			'driver_location': '',
			'driver_name': ''
		}

		self.CONF['EXCLUDE'] = {
			'exclude_hidden_itens': 'true',
		}

		self.CONF['EXCLUDE_FOLDER'] = {
			'folders': '',
		}

		self.CONF['RECENT'] = {
			'recent_backup_file_path': '',
		}

		# Save the config to the file
		with open(self.CONF_LOCATION, 'w') as config_file:
			self.CONF.write(config_file)

		# ######################################################################
		# # Create the directory if it doesn't exist
		# flatpak_list_dir = os.path.dirname(self.FLATPAK_SH_DST)
		# os.makedirs(flatpak_list_dir, exist_ok=True)

		# # Create the shell script content
		# script_content = """#!/bin/bash\nflatpak list --app --columns=application
		# """

		# # Write the content to the file
		# with open(os.path.expanduser(self.FLATPAK_SH_DST), 'w') as script_file:
		# 	script_file.write(script_content)

		# # Make the script executable
		# try:
		# 	os.chmod(self.FLATPAK_SH_DST, stat.S_IREAD)
		# 	os.chmod(self.FLATPAK_SH_DST, stat.S_IROTH)
		# 	os.chmod(self.FLATPAK_SH_DST, stat.S_IWRITE)

		# 	print(f"Script created and made executable at: {self.FLATPAK_SH_DST}")
		# except PermissionError as e:
		# 	print(f"Permission error while changing file permissions: {e}")

		# print(f"Script created at: {os.path.expanduser(self.FLATPAK_SH_DST)}")

	def is_daemon_running(self):
		"""Check if the daemon is already running by checking the PID in the Flatpak sandbox."""
		if os.path.exists(self.DAEMON_PID_LOCATION):
			try:
				with open(self.DAEMON_PID_LOCATION, 'r') as f:
					pid = int(f.read().strip())

				# Check if the process exists in the Flatpak sandbox
				try:
					os.kill(pid, 0)  # Sending signal 0 does not kill the process; it checks if it exists
					# logging.info(f"Daemon is running with PID: {pid}")
					return True
				except OSError:
					# logging.warning(f"Process with PID {pid} is not running.")
					os.remove(self.DAEMON_PID_LOCATION)
					# logging.info(f"Removed stale PID file: {self.DAEMON_PID_LOCATION}")
					return False

			except (ValueError, FileNotFoundError) as e:
				# logging.error(f"Error reading PID file: {e}")
				return False
		else:
			# logging.info(f"PID file {server.DAEMON_PID_LOCATION} does not exist.")
			return False
		
	def is_first_backup(self) -> bool:
		try:
			if not os.path.exists(self.main_backup_folder()):
				return True
			return False
			# else:
			# 	# Make sure that backup to main was not interrupted
			# 	if os.path.exists(self.INTERRUPTED_MAIN):
			# 		return True
			# 	return False
		except FileNotFoundError:
			return True
		except Exception as e:
			logging.error('Error while trying to find if is the first backup.')

	async def delete_oldest_backup_folder(self):
		"""Deletes the oldest backup folder from the updates directory."""
		updates_backup_dir = self.backup_folder_name()

		try:
			# List all the subfolders (dates) in the updates directory, excluding hidden folders
			backup_folders = [
				d for d in os.listdir(updates_backup_dir)
				if os.path.isdir(os.path.join(updates_backup_dir, d)) and not d.startswith('.')
			]

			if not backup_folders:
				logging.warning("No backup folders available to delete.")
				return  # Exit early if there are no folders to delete

			# Sort folders by date (assuming DD-MM-YYYY format)
			backup_dates: list = self.has_backup_dates_to_compare()

			# Delete the oldest folder (first in the sorted list)
			oldest_folder = backup_dates[0]
			oldest_folder_path = os.path.join(updates_backup_dir, oldest_folder)

			# Delete the folder and log the action
			shutil.rmtree(oldest_folder_path)
			logging.info(f"Deleted the oldest backup folder: {oldest_folder_path}")

		except Exception as e:
			logging.error(f"Error deleting the oldest backup folder: {e}")
			raise  # Re-raise the exception to propagate the error

	# BACKUP DESTINATION
	def backup_to_dst(self, src_path: str, dst_path: str) -> None:
		try:
			dst_path_dir: str = os.path.dirname(dst_path)
			os.makedirs(dst_path_dir, exist_ok=True)

			# Copies files
			shutil.copy2(src_path, dst_path)
		except Exception as e:
			logging.error(f"Backing up from {src_path} to {dst_path}.")

	def convert_result_to_python_type(self, value):
		try:
			if value == 'True' or value == 'true' or value == 'Yes':
				return True
			elif value == 'False' or value == 'false' or value == 'No':
				return False
			elif value == 'None' or value == ' ' or value is None:
				return None
			else:
				return value
		except TypeError:
			return None

	# def save_timeframe_to_db(self, timeframe: list, where: str, current_day:bool):
	# 	if current_day:
	# 		day = self.DAY_NAME
	# 	else:
	# 		day = self.get_next_day_name()

	# 	print(f'Generating {day} timeframe...')

	# 	# Convert list to string
	# 	timeframe_str = ','.join(map(str, timeframe))

	# 	# Assuming day_name is defined somewhere
	# 	self.set_database_value(
	# 		section=day,  # Current day name in upper case
	# 		option=where,
	# 		value=timeframe_str,
	# 		func=self.save_timeframe_to_db)

	def get_item_size(self, item_path: str, human_readable: bool = False) -> str:
		try:
			size_bytes = os.path.getsize(item_path)
		except Exception as e:
			return str(e)

		if not human_readable:
			return size_bytes
		else:
			# Convert to human-readable format (KB, MB, GB, TB)
			suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
			index = 0
			size = size_bytes
			while size >= 1024 and index < len(suffixes) - 1:
				size /= 1024.0
				index += 1
			return f"{size:.2f} {suffixes[index]}"

	# def count_total_files(self, path: str) -> int:
	# 	total_files: int = 0
	# 	# Load ignored folders from config
	# 	ignored_folders = self.load_ignored_folders_from_config()

	# 	for root, dirs, files in os.walk(path):
	# 		for file in files:
	# 			src_path: str = os.path.join(root, file)
	# 			only_dirname: str =  src_path.split('/')[3]

	# 			# Exclude directories that match the ignored folders
	# 			if any(os.path.commonpath([root, ignored_folder]) == ignored_folder for ignored_folder in ignored_folders):
	# 				continue

	# 			total_files += 1
	# 	return total_files
	
	def has_backup_device_enough_space(
			self, 
			file_path: str=None, 
			backup_list: list=None) -> bool:
		"""
		Checks if the backup device has enough space to back up the files.

		Args:
			backup_device_path (str): Path to the backup device/directory.
			backup_list (list): List of files or directories to be backed up (each item is a tuple: (src_path, rel_path, size)).

		Returns:
			bool: True if there is enough space, False otherwise.
		"""
		# Threshold for available space (leave at least 2 GB free)
		threshold_bytes = 2 * 1024 * 1024 * 1024  # 2 GB

		# Get available space on the backup device
		total, used, device_free_size = shutil.disk_usage(self.DRIVER_LOCATION)

		if backup_list:
			# Calculate total size of the files to be backed up
			try:
				# Ensure backup_list contains tuples of (src_path, rel_path, size)
				file_size = sum(size for _, _, size in backup_list)
			except ValueError as e:
				print(f"Error while calculating total size to backup: {e}")
				return False
		else:
			# Get file size
			file_size = self.get_item_size(file_path)

		if device_free_size > (file_size + threshold_bytes):
			return True
		return

		# # Check if there is enough space on the backup device
		# if free > (total_size_to_backup + threshold_bytes):
		# 	# print(f"\033[92m[✓]\033[0m Enough space for backup!")
		# 	return True

		# print(f"\033[91m[X]\033[0m Not enough space on the backup device. Required: {total_size_to_backup} bytes, Available: {free} bytes")
		# return False

	####################################################################
	# Packages managers
	####################################################################
	def rpm_main_folder(self):
		return f"{self.DRIVER_LOCATION}/{self.APP_NAME_CLOSE_LOWER}/packages/rpm"

	def deb_main_folder(self):
		return f"{self.DRIVER_LOCATION}/{self.APP_NAME_CLOSE_LOWER}/packages/deb"

	################################################################################
	# LOCATION
	# Base backup folder location
	def main_backup_folder(self) -> str:
		return f"{self.DRIVER_LOCATION}/{self.APP_NAME_CLOSE_LOWER}/{self.BACKUPS_LOCATION_DIR_NAME}/{self.MAIN_BACKUP_LOCATION}"

	def backup_folder_name(self) -> str:
		return f"{self.DRIVER_LOCATION}/{self.APP_NAME_CLOSE_LOWER}/{self.BACKUPS_LOCATION_DIR_NAME}"

	def create_base_folder(self) -> str:
		return f"{self.DRIVER_LOCATION}/{self.APP_NAME_CLOSE_LOWER}"

	def has_backup_dates_to_compare(self) -> list:
		# Get all date folder names, parse them as dates, then sort from newest to oldest
		return sorted(
			[
				date for date in os.listdir(self.backup_folder_name())
				if '-' in date
			],
			key=lambda d: datetime.strptime(d, '%d-%m-%Y'),
			reverse=True  # Sort dates from newest to oldest
		)
	
	################################################################################
	# FLATPAK
	def flatpak_txt_location(self) -> str:
		return f"{self.DRIVER_LOCATION}/{self.APP_NAME_CLOSE_LOWER}/flatpak/flatpak.txt"

	def flatpak_var_folder(self) -> str:
		return f"{self.DRIVER_LOCATION}/{self.APP_NAME_CLOSE_LOWER}/flatpak/var"

	def flatpak_local_folder(self) -> str:
		return f"{self.DRIVER_LOCATION}/{self.APP_NAME_CLOSE_LOWER}/flatpak/share"

	################################################################################
	# SHEDULE
	def get_closest_timeframe(self, day_name: str) -> list:
		closest_timeframe_hours: list = []

		timeframe_list: list = self.get_current_temp_timeframe(
			day_name=day_name)

		for _, hour in enumerate(timeframe_list):
			target_time = datetime(
					year = datetime.now().year,
					month = datetime.now().month,
					day = datetime.now().day,
					hour = hour,
					minute = 0)
			# Positive values mean timers after current time
			time_diff: int = target_time.hour - datetime.now().hour
			if time_diff > 0 :
				closest_timeframe_hours.append(hour)

		closest_timeframe_hours.sort()
		if closest_timeframe_hours:  # Still can backup for today
			return closest_timeframe_hours
		else:
			print('Can not backup for today anymore.')
			return None

	def get_next_day_name(self) -> str:
		today = datetime.now()
		next_day = today + timedelta(days=1)
		next_day_name = next_day.strftime("%A").upper()
		return next_day_name

	# def get_next_day_timemframe(self):
	# 	# Get next day array timeframe
	# 	next_day_name_timeframe: str = self.get_database_value(
	# 		section=self.get_next_day_name(),  # Next day string
	# 		option='new_array')
	# 	return next_day_name_timeframe

	def get_current_temp_timeframe(self, day_name: str) -> list:
		try:
			new_array = self.get_database_value(
				section=day_name,
				option='new_array'
			)

			# Check if new_array is valid
			if new_array is None or not isinstance(new_array, str):
				print(f'Invalid data for {day_name}')
				return None

			# Split the string and convert to integers, ignoring invalid values
			new_array = [int(num) for num in new_array.split(',') if num.isdigit()]

			return new_array
		except (TypeError, AttributeError):
			return None
		except ValueError as e:
			current_function_name = inspect.currentframe().f_code.co_name

			print(e)
			print(f'Function: {current_function_name}')
			raise  # Raise the error instead of exiting

	def get_database_value(self, section: str, option: str) -> str:
		try:
			# Check if config file exists and is loaded
			if not os.path.exists(self.CONF_LOCATION):
				raise FileNotFoundError(f"Config file '{self.CONF_LOCATION}' does not exist")

			if not self.CONF.has_section(section):
				print(f"Section '{section}' not found in configuration.")
				return None  # Or return a default value if needed

			if not self.CONF.has_option(section, option):
				print(f"Option '{option}' not found in section '{section}'.")
				return None  # Or return a default value if needed

			# Retrieve and convert the value
			value = self.CONF.get(section, option)
			return self.convert_result_to_python_type(value=value)

		except BrokenPipeError:
			# Handle broken pipe without crashing
			print("Broken pipe occurred, but the app continues running.")
			return None

		except FileNotFoundError as e:
			print(f"No connection to config file: {e}")
			return None

		except Exception as e:
			current_function_name = inspect.currentframe().f_code.co_name
			print(f"Error in function {current_function_name}: {e}")
			return None

	def set_database_value(self, section: str, option: str, value: str):
		try:
			# Ensure config file exists
			if os.path.exists(self.CONF_LOCATION):
				# Check if the section exists, if not, add it
				if not self.CONF.has_section(section):
					self.CONF.add_section(section)

				# Set the option value
				self.CONF.set(section, option, value)

				# Save the changes to the file
				with open(self.CONF_LOCATION, 'w') as configfile:
					self.CONF.write(configfile)
			else:
				raise FileNotFoundError(f"Config file '{self.CONF_LOCATION}' not found")

		except BrokenPipeError:
			# Handle broken pipe without crashing
			print("Broken pipe occurred, but the app continues running.")
		except FileNotFoundError as e:
			print(f"No connection to config file: {e}")
			exit()
		except Exception as e:
			current_function_name = inspect.currentframe().f_code.co_name
			print(f"Error in function {current_function_name}: {e}")
			exit()

	def print_progress_bar(self, progress: int, total: int, start_time: float) -> str:
		bar_length: int = 50
		percent: float = float(progress / total)
		filled_length: int = int(round(bar_length * percent))
		bar = f'|' + '#' * filled_length + '-' * (bar_length - filled_length) + '|'

		# Calculate elapsed time
		elapsed_time = time.time() - start_time
		velocity = progress / elapsed_time if elapsed_time > 0 else 0

		if velocity > 0:
			estimated_time_left = (total - progress) / velocity
			hours, remainder = divmod(estimated_time_left, 3600)
			minutes, seconds = divmod(remainder, 60)
		# 	estimated_time_str = f'Estimated Time Left: {int(hours)}h {int(minutes)}m {int(seconds)}s'
		# else:
		# 	estimated_time_str = 'Estimated Time Left: N/A'  # If velocity is 0, show N/A

		# Show progress and estimated time
		if progress >= (total / 2):  # Only show estimated time at min. 50%
			estimated_time_str = f'Estimated Time Left: {int(hours)}h {int(minutes)}m {int(seconds)}s'
		else:
			estimated_time_str = 'Estimated Time Left: Calculating...'

		print(f'Progress: {progress}/{total} ({percent:.0%}) - {bar} | '
			f'Time Elapsed: {int(elapsed_time)}s | '
			f'Velocity: {velocity:.2f} files/s | '
			f'{estimated_time_str}', end='\r')
		print()

	def copytree_with_progress(self, src: str, dst: str) -> None:
		num_files = sum([len(files) for r, d, files in os.walk(src)])
		progress: int = 0

		try:
			# Handle source as a file or directory
			if os.path.isfile(src):
				dst_without_filename = '/'.join(dst.split('/')[:-1])

				os.makedirs(dst_without_filename, exist_ok=True)
				shutil.copy2(src, dst)

				print(f"\033[92m[✓]\033[0m {src} -> {dst}")
			elif os.path.isdir(src):
				for root, dirs, files in os.walk(src):
					for dir in dirs:
						source_folder: str = os.path.join(root, dir)
						destination_dir: str = source_folder.replace(src, dst, 1)

						os.makedirs(destination_dir, exist_ok=True)

					for file in files:
						src_file: str = os.path.join(root, file)
						dst_file: str = src_file.replace(src, dst, 1)

						os.makedirs(dst_file, exist_ok=True)
						shutil.copy2(src_file, dst_file)

						progress += 1

						print(f"\033[92m[✓]\033[0m {src_file} -> {dst_file}")
						self.print_progress_bar(progress, num_files)
		except Exception as e:
			logging.error(f"copytree_with_progress: {e}")

	def setup_logging(self):
		"""Sets up logging for file changes."""
		MAX_LOG_SIZE: int = 50 * 1024 * 1024  # Example: 50 MB

		# Check if the directory for the log file exists; if not, create it
		log_dir = os.path.dirname(self.LOG_LOCATION)
		os.makedirs(log_dir, exist_ok=True)  # Create the directory for the log file

		"""Check log file size and delete if it exceeds the limit."""
		if os.path.exists(self.LOG_LOCATION):
			log_size = os.path.getsize(self.LOG_LOCATION)
			if log_size > MAX_LOG_SIZE:
				# Delete the log file if it exceeds the max size
				os.remove(self.LOG_LOCATION)
		else:
			# Create a new empty log file
			with open(self.LOG_LOCATION, 'w'):
				pass
	
		logging.basicConfig(
							filename=self.LOG_LOCATION,
							level=logging.INFO,
							format='%(asctime)s - %(message)s')
		console_handler = logging.StreamHandler()
		console_handler.setLevel(logging.INFO)
		formatter = logging.Formatter('%(asctime)s - %(message)s')
		console_handler.setFormatter(formatter)
		logging.getLogger().addHandler(console_handler)
