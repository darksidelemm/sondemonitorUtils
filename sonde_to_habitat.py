#!/usr/bin/env python
# Oh wait, you'll usually be running this on Windows :-)
#
# Sondemonitor to Habitat Bridge
# Copyright (C) 2017 Mark Jessop <vk5qi@rfhead.net>
#
# NOTE: This particular script uses Sondemonitor's COM/OLE interface,
# and as such has to be run on windows, and as an Administrator.
#
# Dependencies:
#	- pywin32 (probably need to grab the binary package of this)
#	- crcmod (get this from pip)


import time, datetime, sys, crcmod, httplib, argparse, json
from base64 import b64encode
from hashlib import sha256
from socket import *

ozi_udp_host = "127.0.0.1"
ozi_udp_port = 8942


parser = argparse.ArgumentParser()
parser.add_argument("--habitat", type=str, help="Upload Sonde telemetry to Habitat using the given callsign.", default="None")
parser.add_argument("--habitat_user_call", type=str, help="Source Callsign for Habitat Uploads.", default="SONDEMONITOR")
parser.add_argument("--oziplotter", action="store_true", help="Push Sonde telemetry into OziPlotter via UDP.", default=False)
parser.add_argument("--summary", action="store_true", help="Push Summary of Sonde telemetry into network via UDP broadcast (compatible with HorusGroundStation utilities).", default=False)
parser.add_argument("-r", "--rate", type=int, help="Time between uploads (seconds).", default=10)
args = parser.parse_args()

# Attempt to connect to SondeMonitor.
try:
	import win32com.client
	sm = win32com.client.Dispatch("SondeMonitor.Document")
except:
	print("Could not connect to SondeMonitor. Is it running? Also, this script must be run as administrator.")
	input("")
	sys.exit(1)


def poll_sondemonitor():
	global sm
	
	# Poll ALL The things.
	sonde_data = {}
	sonde_data['id'] = sm.GetSondeData(0)
	sonde_data['lat'] = sm.GetSondeData(1)
	sonde_data['lon'] = sm.GetSondeData(2)
	sonde_data['alt'] = sm.GetSondeData(3)
	sonde_data['course'] = sm.GetSondeData(4)
	sonde_data['speed'] = sm.GetSondeData(5)
	sonde_data['time_str'] = sm.GetSondeData(6)
	sonde_data['freq'] = sm.GetSondeData(7)
	sonde_data['pressure'] = sm.GetSondeData(8)
	sonde_data['temp'] = sm.GetSondeData(9)
	sonde_data['humidity'] = sm.GetSondeData(10)
	sonde_data['frame'] = sm.GetSondeData(13)
	
	# Parse time string into a datetime object.
	sonde_data['datetime'] = datetime.datetime.strptime(sonde_data['time_str'],"%Y-%m-%d %H:%M:%SUTC")
	sonde_data['short_time'] = sonde_data['datetime'].strftime("%H:%M:%S")
	
	return sonde_data

# CRC16 function
def crc16_ccitt(data):
    """
    Calculate the CRC16 CCITT checksum of *data*.
    (CRC16 CCITT: start 0xFFFF, poly 0x1021)
    """
    crc16 = crcmod.predefined.mkCrcFun('crc-ccitt-false')
    return hex(crc16(data))[2:].upper().zfill(4)

def telemetry_to_sentence(sonde_data, payload_callsign="YPADSONDE"):
    sentence = "$$%s,%d,%s,%.5f,%.5f,%d,%.1f,%.1f,%.1f" % (payload_callsign,sonde_data['frame'],sonde_data['short_time'],sonde_data['lat'],
    	sonde_data['lon'],int(sonde_data['alt']),sonde_data['speed'], sonde_data['temp'], sonde_data['humidity'])

    checksum = crc16_ccitt(sentence[2:])
    output = sentence + "*" + checksum + "\n"
    print(output)
    return output

def habitat_upload_payload_telemetry(telemetry, payload_callsign = "YPADSONDE", callsign="N0CALL"):

    sentence = telemetry_to_sentence(telemetry, payload_callsign = payload_callsign)

    sentence_b64 = b64encode(sentence)

    date = datetime.datetime.utcnow().isoformat("T") + "Z"

    data = {
        "type": "payload_telemetry",
        "data": {
            "_raw": sentence_b64
            },
        "receivers": {
            callsign: {
                "time_created": date,
                "time_uploaded": date,
                },
            },
    }
    try:
        c = httplib.HTTPConnection("habitat.habhub.org",timeout=4)
        c.request(
            "PUT",
            "/habitat/_design/payload_telemetry/_update/add_listener/%s" % sha256(sentence_b64).hexdigest(),
            json.dumps(data),  # BODY
            {"Content-Type": "application/json"}  # HEADERS
            )

        response = c.getresponse()
        return (True,"OK")
    except Exception as e:
        return (False,"Failed to upload to Habitat: %s" % (str(e)))
	
def printData(sonde_data):
	print("=====================================")
	print("  Fix Time: %s" % sonde_data['time_str'])
	print("Sonde Freq: %s" % sonde_data["freq"])
	print("  Sonde ID: %s" % sonde_data["id"])
	print("  Latitude: %.5f" % sonde_data["lat"])
	print(" Longitude: %.5f" % sonde_data["lon"])
	print("  Altitude: %d Metres" % sonde_data["alt"])
	print("      Temp: %.1f Celsius" % sonde_data["temp"])

def push_to_ozi(sonde_data):
	sentence = "TELEMETRY,%s,%.5f,%.5f,%d" % (sonde_data['short_time'],sonde_data['lat'],sonde_data['lon'],sonde_data['alt'])

	try:
		sock = socket(AF_INET,SOCK_DGRAM)
		sock.sendto(sentence,(ozi_udp_host,ozi_udp_port))
		sock.close()
	except Exception as uhoh:
		print(uhoh)

HORUS_UDP_PORT = 55672
# Push a 'Payload Summary' message into the local network via UDP broacast.
# This is used by the HorusGroundStation SummaryGUI utility, as well as other chase car widgets.
def push_payload_summary(sonde_data):
    packet = {
        'type' : 'PAYLOAD_SUMMARY',
        'callsign' : sonde_data['id'],
        'latitude' : sonde_data['lat'],
        'longitude' : sonde_data['lon'],
        'altitude' : sonde_data['alt'],
        'speed' : sonde_data['speed']*3.6,
        'heading': sonde_data['course']
    }

    # Set up our UDP socket
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.settimeout(1)
    # Set up socket for broadcast, and allow re-use of the address
    s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass
    s.bind(('',HORUS_UDP_PORT))
    try:
        s.sendto(json.dumps(packet), ('<broadcast>', HORUS_UDP_PORT))
    except socket.error:
        s.sendto(json.dumps(packet), ('127.0.0.1', HORUS_UDP_PORT))
		
if __name__ == "__main__":
	sonde_data_old = {'time_str':'blank'}

	# Now we start parsing data from SM and sending it through.
	while True:
		sonde_data_new = poll_sondemonitor()
		# Test if we have new data.
		if(sonde_data_new['time_str'] != sonde_data_old['time_str']):
			printData(sonde_data_new)
			# Sanity check data before we upload. 
			if( (sonde_data_new['lat']) != 0.0 and (sonde_data_new['lon'] != 0.0) and(sonde_data_new['alt'] > 10.0) ):
				if args.oziplotter == True:
					try:
						push_to_ozi(sonde_data_new)
						print("Data pushed to OziPlotter Successfully!")
					except:
						print("Failure when pushing data to OziPlotter")

				if args.summary == True:
					try:
						push_payload_summary(sonde_data)
						print("Pushed payload summary successfuly!")
					except:
						print("Faliure when pushing payload summary.")

				if args.habitat != "None":
					(success, message) = habitat_upload_payload_telemetry(telemetry=sonde_data_new, 
						payload_callsign = args.habitat,
						callsign = args.habitat_user_call)
					if success:
						print("Data pushed to Habitat.")
					else:
						print("Error pushing data to Habitat: %s" % message)

			sonde_data_old = sonde_data_new
			time.sleep(args.rate)
		else:
			print("Waiting for new data...")
			time.sleep(1)

	
