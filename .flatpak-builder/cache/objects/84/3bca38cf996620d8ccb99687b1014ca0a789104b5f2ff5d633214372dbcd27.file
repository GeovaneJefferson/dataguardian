from old_server import *

# Specify the .conf file location
settings = QSettings("config.conf")

# DRIVER Section
settings.beginGroup("DRIVER")
settings.setValue("driver_name", "BACKUP")
settings.setValue("driver_location", "/media/geovane/BACKUP")
settings.endGroup()

# BACKUP Section
settings.beginGroup("BACKUP")
settings.setValue("schedule_type", 4)
settings.setValue("automatically_backup", True)
settings.setValue("backing_up", False)
settings.setValue("system_tray", True)
settings.setValue("resume_to_latest_date", False)
settings.setValue("first_startup", False)
settings.setValue("to_be_resume", False)
settings.endGroup()

# Days of the Week Sections
days_of_week = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
day_values = {
    "SUNDAY": "",
    "MONDAY": "",
    "TUESDAY": "5,11,16,17",
    "WEDNESDAY": "7,10,11,20",
    "THURSDAY": "6,10,13,18",
    "FRIDAY": "",
    "SATURDAY": ""
}

for day in days_of_week:
    settings.beginGroup(day)
    settings.setValue("timeframe_points", 0)
    settings.setValue("days_backup_count", 0)
    settings.setValue("busiest_times", "")
    settings.setValue("days_timeframe", "")
    settings.setValue("new_array", day_values[day])
    settings.endGroup()
