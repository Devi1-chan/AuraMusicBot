@echo off
echo AuraMusicBot Launcher

:: Check if ffmpeg.exe exists
if not exist ffmpeg.exe (
    echo Downloading ffmpeg...
    powershell -Command "Invoke-WebRequest https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip -OutFile ffmpeg.zip"
    powershell -Command "Expand-Archive -Path ffmpeg.zip -DestinationPath . -Force"
    move /Y ffmpeg-*-essentials_build\bin\ffmpeg.exe ffmpeg.exe
    rmdir /S /Q ffmpeg-*-essentials_build
    del ffmpeg.zip
)

:: Install Python dependencies
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

:: Start bot
echo Starting AuraMusicBot...
py AuraMusicBot.py

pause