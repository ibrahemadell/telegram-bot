@echo off

set PGPASSWORD=6vOjz3mBLDfh1QVU
set BACKUP_DIR=C:\Users\UIS\Desktop\ibrahem\telegram-bot\telegram-bot\backup

pg_dump -h db.egwrylltkkvljceesiza.supabase.co -U postgres -d postgres -F c -f "%BACKUP_DIR%\backup_%date:~10,4%-%date:~4,2%-%date:~7,2%.dump"

echo =========================
echo Backup saved to %BACKUP_DIR%
echo =========================
pause