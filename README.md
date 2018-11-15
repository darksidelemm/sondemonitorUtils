Sondemonitor to APRS/Habitat/OziPlotter Bridge
================

## NOTE - With the release of [radiosonde_auto_rx](https://github.com/projecthorus/radiosonde_auto_rx) and [chasemapper](https://github.com/projecthorus/chasemapper), I will no longerbe supporting this software. If your local sonde launches are using either Vaisala RS92/RS41 or Graw DFM06/09 radiosondes, I strongly suggest using radiosonde_auto_rx.

I track Bureau of Meteorology Radiosondes occasionally, and I figured it'd be nice to be able to push their position into APRS, for mapping on aprs.fi.
Even more recently, I decided that it would be more useful to have the sonde data show up on the Habitat tracker (http://tracker.habitat.org)

Dependencies:
* sonde_to_aprs.py
 * pykml
* sonde_to_habitat.py
 * pywin32
 * crcmod

There are 2 utilities in here:

## sonde_to_aprs.py
This script uses the 'Live G-E Server' interface in SondeMonitor to collect data and push it into APRS.
Run this script with: 
`python sonde_to_aprs.py --callsign <YourCall> --passcode <YourAPRSISPasscode>`

## sonde_to_habitat.py
This script uses the COM/OLE interface to SondeMonitor to get more frequent position updates, and pushes them into the Habitat HAB tracking database, to be viewed on http://tracker.habhub.org/

### Habitat Uploads
The uploads to Habitat use the telemetry string format:
`$$<callsign>,<sequence number>,<time>,<lat>,<lon>,<alt>,<speed>,<temp>,<humidity>*<CRC16>`
Where the 'callsign' field is set using the --habitat command line option. You should try and make this callsign fairly unique, to avoid clashing with other users of the Habitat tracker. For sondes launched in Adelaide, I use the callsign 'YPADSONDE'.

You will need to create a suitable 'Payload Document' for the payload to show up on the tracker. You can create such a payload document at http://habitat.habhub.org/genpayload/ . The existing 'YPADSONDE' payload document (Use 'Start from Existing' to find it) is a good starting point, you will just need to change the callsign.

### Running as Administrator
As this script uses the COM/OLE interface to SondeMonitor, it will only work on Windows, and only when running as an Administrator. Because Windows 'run as administrator' options don't respect shortcuts 'Start In' settings, you need to do a few annoying hacks to be able to run this script easily:
* Copy this directory to C:\HAB\ or somewhere else
* Modify the Sonde_To_Habitat.bat batch script as appropriate (change directory change line, callsigns, etc)
* Create a shortcut to the batch script.
* In the shortcut properties, go to the 'Shortcut' tab, click 'Advanced' and enable 'Run as Administrator'.
You should now be able to run the shortcut to start the script.

## Disclaimer
I wrote this to work with Vaisala RS92SGP sondes. I'm not sure if Sondemonitor's KML output changes with different sondes (i.e. RS41s). If it does, this code will likely break horribly. Once the start launching RS41's near me I'll be able to test and update this script.

Some of my blog posts on tracking radiosondes:
http://rfhead.net/?p=42
http://rfhead.net/?p=550
