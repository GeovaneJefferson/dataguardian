# Data Gardian
**Data Guardian** is a backup tool designed specifically for Linux users. It dynamically detects the busiest time on your PC each day and schedules backups at the optimal timeframe to minimize disruption. By analyzing system activity, Data Guardian ensures backups are scheduled intelligently, avoiding peak usage times. The tool saves one timeframe per day, continuously adjusting and optimizing based on PC activity and backup consistency.

## Features
**Busiest Time Detection:** Automatically detects the busiest times on your Linux PC each day based on folders accessed and file sizes.  
**Dynamic Backup Scheduling:** Creates a random backup schedule each day, ensuring that backups happen during off-peak hours.  
**Daily Timeframe Storage:** Stores the optimal timeframe for each day, learning from past activity to refine future schedules.  
**Consistency-Driven Adjustments:** Adjusts backup schedules based on how consistently backups are performed, either solidifying or resetting the schedule based on user performance.  
**Flexible Backup Limits:** Supports custom daily backup limits (e.g., 2, 4, or 6 backups per day), giving you control over the frequency of backups.  

## How It Works
**Data Processing:** The tool gathers PC activity data (hours, folders accessed, and file sizes) to identify the busiest periods each day.  
**Backup Scheduling:** Backups are scheduled during the most active times, ensuring that files being accessed or modified the most are backed up.  
**Timeframe Points System:** A points-based system tracks user behavior. Completing backups increases points, eventually locking in a fixed schedule. Missing backups reduces points, which resets the timeframe.  
**Saving and Adjusting:** The busiest time is saved daily in the database, ensuring the backup schedule becomes more optimized over time.  

## Customization
**Schedule Type:** Define how many backups per day you'd like (2, 4, or 6).  
