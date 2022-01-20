# Changelog
## Version 7.0
Changes in major version 7.0:
1. Complete rewrite
2. API Messages & File Paths: Replaced hard-coded dates in URLs and file paths with a `%DATE%` placeholder.
3. Changelog: Text changed to monospace format.
4. Configuration:
    1. Replaced discord.txt and hard-coded variable values for one config.json file.
    2. Added a function that would allow the replacement of some configuration values without the need for a restart.
5. COVID Pi: Moved display building to new function.
6. Discord Commands:
    1. Split each command into its own function.
    2. Replaced help output string with list.
    3. GetData:
        1. Removed references to the "latest" parameter in one of the error messages.
        2. Corrected error message that stated the command takes exactly one argument and included the type of parameter.
        3. Using the command will force a verification of the data store.
    4. RAVGPeaks:
        1. Moved building output message to new function and utilised recursion.
        2. Added message in help clarifying that one parameter must be included when another is used.
        3. Amended the wording of the error messages to be more descriptive.
    5. Version: Added a flag that would prevent the script from crashing due to this changelog being too fucking big.
7. Logs: Removed runtime logs where text is "Done.".
8. Mass Data:
    1. Added the ability for the script to verify the mass data and to refresh the data at regular intervals or when invalid.
    2. Added a check that would prevent rilling averages, corrections, and daily change from being calculated if the data was invalid.
    3. Working on cutting back code duplication.
9. Primary: Fixed a bug that would cause the script to crash if the corrections number could not be calculated.
10. Primary & Secondary Data Outputs:
    1. Removed the datestamp.
    2. Removed code duplication.
11. Rolling Average Peaks:
    1. Moved peak checking into new function and slimmed down function.
    2. Removed link between global and local rolling average peaks. A global peak no longer implicitly creates a local peak.
    3. Replaced the Rolling Average placeholder text to be more descriptive.
    4. Removed code duplication.
12. Secondary: Added dictionary for total doses tha adds the numbers doing the existing loop.
13. Sending of Discord Messages: Unified sending of messages around one method.
14. Status Messages:
    1. Fixed a bug that would cause a message already sent to be sent multiple times when using the `$messages` command.
    2. Moved reading of the Messages.json file into new function.
    3. Aded text in the sent message that indicates the origin of the message.
    4. Fixed a bug that would cause the script to enter an infinite loop if the contents of Messages.json was invalid upon a check.
15. Supplementary Files: Removed all functions of LastOutput.txt and Discord.txt
16. Time Check:
    1. Fixed a bug that would prevent the timeout message from sending if one set of data was obtained, but not the other.
    2. Fixed a bug that would prevent the script from preparing for a new day if that day was excluded.
17. Variants:
    1. Removed the number field and selection by number.
    2. Added more checks to ensure the script cannot crash due to exceeding the Discord character limit.
    3. Associations:
        1. Renamed the References data type with "Reference".
        2. Replaced the Substring data type for `list` from `string`.
        3. Replaced the Reference data type for `string` from `list`.