# Changelog
## Version 6.5
Changes in dot update 6.5:
1. API: Changed scan start time from 1540 to 1440 & timeout condition from 1500 to 1400.
2. Secondary: Added total doses delivered as sum of the existing First, Second, and Additional doses.
3. API: Fixed a bug that caused the bot to crash if a timeout condition was reached.
4. Messages: Fixed an error that caused the wrong ISO standard to be displayed in the `$help` prompt.
5. Variants: Fixed a bug that caused the script to crash when using the `number` command.
## Version 6.4
Changes in dot update 6.4:
1. Messages: fixed a bug that caused some messages to be sent on every check.
## Version 6.3
Changes in dot update 6.3:
1. Bot: fixed a bug that would cause the bot to crash on startup if no network connectivity was found.
2. Messages: fixed a bug that caused an unhandled exception if an image with no text was sent.
3. Secondary: added support for additional vaccinations.
4. Data aggregation: fixed a bug that caused the program to not save the latest data if the script crashed.
## Version 6.2
Changes in dot update 6.2:
1. Messages: fixed a bug that caused the script to enter an infinite loop if a defective messages file was passed.
2. Secondary: added provision for the announcement of additional vaccinations. This will be added in a future update when the appropriate data becomes available from the API.
3. Bot: fixed a bug that caused the script to wait 10 additional seconds when waiting for the bot to be ready.
## Version 6.1
Changes in dot update 6.1:
1. Variants: added a last updated record to the variants file.
2. COVID Pi: removed the marker for the corrections number.
3. Messages:
    1. Added command `$ravgpeaks` for returning the current rolling average peaks.
    2. Added a comment that explains when a local rolling average peak may be created or expired by the bot.
4. Bot: working on a bug that causes the script to crash on startup if a network connection is not found.
5. Rolling Averages: fixed a bug that caused the premature expiration of local rolling average peaks.
## Version 6.0
Changes in major update 6.0:
1. Complete rewrite.
2. Primary:
    1. Split API check function.
3. Secondary:
    1. Split API check function.
    2. UK Population count changed to 68306137.
4. Rolling Averages:
    1. Added a message to confirm no new rolling average peaks.
    2. Reorded the sequence of checks for rolling average peaks.
5. API Status Messages:
    1. Removed in-script storage of messages for current day.
6. Discord Input Messages:
    1. Added a message declaring an unhandled exception has occurred upon the occurance of an exception.
    2. Improved handling of the changelog.
7. Variants:
    1. Fixed a bug that caused an unhandled exception when searching by number.
    2. Added support for referenced PANGO lineages.
    3. Added a message declaring an unhandled exception has occurred upon the occurance of an exception.
    4. Added limited support for full country names. (N.B.: This is inconsistent between full national names [Russian Federation] and truncated names [Czechia] and handles names containing "Republic" strangely).
    5. Added message highlighting whether a variant is an exact match or a reference match.
8. Code:
    1. Improved categorisation of methods and global variables.
9. COVID Pi:
    1. Changed duty cycle of Error LED in a fatal exception from 50% to 10%.