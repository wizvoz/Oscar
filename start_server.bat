@echo off
title Brian's Video Downloader Server

echo ==================================================
echo  Starting Brian's Video Downloader Server
echo ==================================================
echo.

REM --- This command assumes your virtual environment folder is named ".venv"
echo Activating the Python virtual environment...
call .\.venv\Scripts\activate.bat

REM --- This command starts the Flask server
echo Launching the application...
echo (To stop the server, just close this window or press CTRL+C)
echo.
python app.py

echo.
echo Server has been stopped.
pause