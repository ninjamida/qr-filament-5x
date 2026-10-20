# QR-Filament
QR-Filament is a plugin for Z-Mod on the Flashforge AD5X, to automate color / material selection when loading spools via QR codes attached to your spools. 2D-printable QR codes are provided for all default color-material combinations, as is a Python script to generate your own custom combinations.

## Requirements
* Flashforge AD5X with Z-Mod. Native screen should be *mostly* supported, but is untested. Creator 5 is not supported at this time.
* A Python-capable host device (such as a PC, Mac, or Raspberry Pi) on the same LAN as the printer.
* A camera. This can either be the AD5X camera, or a webcam attached to the host device.
* A 2D printer, to print the labels. Color recommended but not required. Or you can try to 3D print them if you like.

# Compatibility
* Compatible with IFS Jacker.
* *Probably* compatible with Bambufy / LessWaste.
* Intended to be compatible with native screen, but this is untested.

## Setup
These instructions are for a straightforward setup - default configuration, no custom filament types or colors, and using the AD5X's standard camera. See configuration info below for advanced setups.
### 1. Installing and enabling the plugin
1. Add the following to `user.moonraker.conf` (in `mod_data`), then reboot the printer:
```
[update_manager qr_filament]
type: git_repo
channel: stable
path: /root/printer_data/config/mod_data/plugins/qr_filament
origin: https://github.com/ninjamida/qr-filament-5x.git
is_system_service: False
primary_branch: master
```
2. Via Fluidd or Mainsail's update manager, "Recover" and then fully update QR-Filament.
3. Enter the following command in the console: `ENABLE_PLUGIN NAME=qr_filament`
### 2. Setting up the host device
1. Copy the contents of the `host` folder to your PC, Mac or Raspberry Pi.
2. Via PIP or your system's package manager, install the `opencv-python` and `qrcode` packages.
3. Open `qr_filament.ini`, and replace the `127.0.0.1` placeholder with your printer's LAN IP address
4. If you have multiple AD5Xes, you can add additional fields `PRINTER_1_IP`, `PRINTER_2_IP`, etc. You do not need to run seperate instances of the script for each printer.
5. Run the "qr_filament.py" script. Optionally, configure it to automatically run in the background at all times.
### 3. Label your spools
1. Locate appropriate material/color labels for your spools in the `labels` folder.
2. 2D print these, and attach them to the side of your spools. Make sure to consider whether the glue you are using will withstand the heat of your filament dryer, if applicable.

## Usage
To load a filament:
1. Hold the filament in front of the camera so that the camera can see the QR code.
2. When the printer detects the QR code, your LED will briefly flash (if you have one) and a popup will appear in the web interface, and on-screen if you are not using the native screen.
3. If you are using the native screen, use the popup (via Fluidd / Mainsail) to select the channel it is being loaded into.
4. If you are *not* using the native screen, ignore the popup and simply insert the filament into the IFS. The channel will be automatically detected. You can use the popup as a fallback if this fails.

The COLOR menu, and any built-in color management features of your screen, can still be used. QR-Filament provides an additional option and does not interfere with the standard options.

## Generating Custom Labels
### QR Code Format
Custom filament labels can be created and used. Simply create a plain-text QR code following the pattern `QRF:[material]:[color]`. `material` should be all-caps and match the material name in Z-Mod; while `color` should be six hex digits without a leading #. For example, `QRF:PLA:FF0000` for red (R 255; G 0; B 0) PLA.

### Generator Script
A generator script is provided to generate labels in the same design as the provided ones and/or to mass-create them. This is the `generator.py` script in the "host" folder. This script is intended to be run on a PC, Mac or Raspberry Pi; not on the AD5X.

To use the generator, invoke the script with a list of filament labels as arguments:

`python generator.py PLA:000000 PLA:FFFFFF PLA:FF0000 ABS:FFFFFF TPU:808080`

You can also replace the material or color with an asterisk:

`python generator.py PLA:* ABS:* *:FFFFFF *:000000 *:808080`

The above will generate labels for both PLA and ABS, in all three colors specified. You can combine this to generate some combinations as well as some manual labels:

`python generator.py PLA:* ABS:* *:FFFFFF *:000000 ABS:808080`

The above will generate PLA and ABS labels for both FFFFFF and 000000, as well as an ABS label (but not a PLA label) for 808080.

If wildcard colors are specified, but no wildcard materials are specified, **and** the `qr_filament.ini` config file (explained later) specifies a list of valid materials, that list of valid materials will be used to determine the materials for which labels are generated.

Instead of including these as command line parameters, you can instead put the wildcard entries into a file. Create a file called `materials.txt` or `colors.txt` then include one material or color per line. Then, use the following command line arguments (the two can be used independently of each other) - this is equivalent to specifying every material/color from the file as a `[material]:*` or `*:[color]` entry.

`python generator.py -file-materials -file-colors`

The above can be combined with command-line specified materials and/or colors.

Any color specified, whether on the command line or in `colors.txt`, can be followed with a # and a human-readable name. This name will be written on the generated label instead of the hex code.

`python generator.py PLA:FFFFFF#White`

The above will generate a label for PLA with color FFFFFF, and the text label will say "White" rather than "FFFFFF".

If you wish to re-generate labels for the stock materials / colors, use the following.

`python generator.py -stock`

### Generator Script - Advanced Parameters
The prefix (QRF) is read from qr_filament.ini. If you change (or omit) it there, the generator script will follow suit.

The following additional command line parameters are available to customize the code generation:

* `boxsize=5` - Box size for the QR code. Default is 5.
* `bordersize=4` - Border side for the QR code. Default is 4.
* `fontsize=20` - Font size for the QR code. Auto-determined if omitted.
* `version=1` - QR code version to use. Auto-determined if omitted.
* `error_correction=M` - QR code error correction level. L, M, Q or H. Default is M.

## Advanced Configuration / Parameters
QR-Filament has some advanced parameters / configuration values available if you wish to use them. These are in particular necessary if you want to use a webcam rather than the printer's camera.

### Command-line parameters
The `qr_filament.py` host script can be invoked with the following parameters:
* `output=2` - Level of output to console (or log file) to write. 0 = ideally nothing, 1 = exceptions only, 2 = basic output, 3 = full output, 4 = full output including loop iteration behavior.
* `auto_restart=false` - Whether the script should restart itself if terminated due to an uncaught exception. It will not auto-restart if killed via process manager or similar.

### qr_filament.ini parameters (global)
* `PREFIX=QRF` - Sets the prefix expected at the start of the QR codes. This is a safety check to weed out any irrelevant (or false-detection) QR codes that may be picked up. Changing the default is generally unnecessary, but may be desirable for some custom setups.
* `VALID_MATERIALS=` - Specify a list of materials (comma-seperated) and QR-Filament will only respond to tags that mark the materials on this list. If left blank, all materials are accepted.
* `COOLDOWN_TIME=5` - Specifies how long after detecting a QR code and sending it to a printer, before a QR code can be sent to that printer again.
* `LOOP_DELAY=0.05` - Rest time between loop iterations. Increasing this reduces system load, but at the cost of laggier response times when QR codes are scanned.
* `ERROR_TIME=10` - Time without a successful feed update after which it is assumed the feed is in an error state.
* `PRINTING_CHECK_DELAY=10` - If using the "suspend when printing" option, the printer's status will be checked with this frequency.
* `SUSPEND_WHEN_PRINTING=true` - If enabled, and only a single printer is configured, the video feed will not be processed at all while the printer is printing. Regardless of this setting, QR code scans will not be forwarded to printers that are currently printing; this is just about reducing resource usage on the host. Note that multiple copies of the same printer (ie: identical Moonraker URL) still count as "only a single printer" for the purpose of this setting, in case you need to configure multiple cameras for one printer.

### qr_filament.ini parameters (per-printer)
Multiple printers can be configured with a single instance of the `qr_filament.py` host script. The examples below begin with `PRINTER_0`, but you can add additional printers by using `PRINTER_1`, `PRINTER_2`, etc. There is no hardcoded limit - it's just a matter of what your host hardware will support.

The standard setup for a printer is to use the printer's camera (via `http://[printer IP]:8080/?action=stream`), with Moonraker on port 7125. For this setup, only a single line is needed to configure the printer:

* `PRINTER_0_IP=127.0.0.1`

However, if your setup deviates from this (eg. scanning with a webcam instead of the AD5X's camera), you can customize it as follows:

* `PRINTER_0_CAMERA=http://127.0.0.1:8080/?action=stream`
* `PRINTER_0_MOONRAKER=http://127.0.0.1:7125/`

The `PRINTER_0_CAMERA` field can either be a URL to an MJPEG stream, or an index number of a local webcam (most likely zero) - or any other string or int parameter accepted by cv2.VideoCapture() in Python.