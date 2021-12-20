# UKCOVID19
An application interfacing the Python UK-COVID19 SDK from the United Kingdom Health Security Agency into a Discord bot and 20✕4 Character LCD Display with 3 signal LEDs.

---
## Getting Started
### Required packages
The following packages are required from PyPI:
* `uk-covid19`
* `gpiozero`
* `iso3166`
* `asyncio`
* `discord.py`
* `emoji-country-flag`

Python 3.7 or greater will be required for this script to work.

Additional packages will be required to drive the Character LCD over the I2C protocol, these are included in the latest section.

### Required hardware
The folowing hardware is required:
* Raspberry Pi or of many clones that support GPIO outputs.
* A 20✕4 Character LCD with an I2C Display Adapter.
* One each of a Red, Yellow, and Green LED.
* 3✕82Ω resistors.
* Wire with Dupont connectors.

### Configuring the hardware
For information on how to configure the Pi for the I2C protocol and the Character LCD, see [this link](https://tutorials-raspberrypi.com/control-a-raspberry-pi-hd44780-lcd-display-via-i2c/).

Each LED connects to a GPIO Pin with one of the resistors. 82Ω is used to drop the 3.3V signal voltage from the GPIO pins to a more manageable voltage for the LEDs that doesn't cook them the femtosecond the script powers them. The LEDs connect to the GPIO pins specified in the following table:
|LED|GPIO Pin|
|---|--------|
|Red|GPIO14|
|Yellow|GPIO15|
|Green|GPIO18|

