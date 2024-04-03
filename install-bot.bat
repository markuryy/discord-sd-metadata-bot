@echo off
echo Setting up the metadatabot environment...

:: Check for Python & pip
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python and make sure it's in PATH.
    exit /b 1
)

:: Create a virtual environment
python -m venv metadatabot

:: Activate the virtual environment
call metadatabot\Scripts\activate

:: Install dependencies
echo Installing dependencies...
pip install discord sd_prompt_reader
pip install -r requirements.txt

echo Setup complete. You can now run your bot using run_bot.bat.
pause