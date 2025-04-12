@echo off
setlocal enabledelayedexpansion

for %%f in (*.m4a) do (
    set filename=%%~nf
    ffmpeg -i "%%f" -q:a 2 "!filename!.mp3"
)

endlocal
