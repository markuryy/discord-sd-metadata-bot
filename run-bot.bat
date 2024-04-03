@echo off
:restart
echo Starting metadatabot...

:: Activate the virtual environment
call metadatabot\Scripts\activate

:: Run the bot
python discord_bot.py

echo Bot crashed or was stopped. Restarting...
goto restart

:: Optional: Add a delay before restarting to prevent spamming in case of immediate crash
:: timeout /t 5 >nul
