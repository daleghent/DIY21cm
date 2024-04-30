#!/home/stellarmate/miniforge3/bin/python3
# Before running this python script,
# start an INDI server, either in ekos gui, or with the command line:
# indiserver indi_simulator_telescope


# for logging
import sys
import time
import logging
# import the PyIndi module
import PyIndi

# The IndiClient class which inherits from the module PyIndi.BaseClient class
# Note that all INDI constants are accessible from the module as PyIndi.CONSTANTNAME
class IndiClient(PyIndi.BaseClient):
    def __init__(self):
        super(IndiClient, self).__init__()
        self.logger = logging.getLogger('IndiClient')
        self.logger.info('creating an instance of IndiClient')

    def newDevice(self, d):
        '''Emmited when a new device is created from INDI server.'''
        self.logger.info(f"new device {d.getDeviceName()}")

    def removeDevice(self, d):
        '''Emmited when a device is deleted from INDI server.'''
        self.logger.info(f"remove device {d.getDeviceName()}")

    def newProperty(self, p):
        '''Emmited when a new property is created for an INDI driver.'''
        self.logger.info(f"new property {p.getName()} as {p.getTypeAsString()} for device {p.getDeviceName()}")

    def updateProperty(self, p):
        '''Emmited when a new property value arrives from INDI server.'''
        self.logger.info(f"update property {p.getName()} as {p.getTypeAsString()} for device {p.getDeviceName()}")

    def removeProperty(self, p):
        '''Emmited when a property is deleted for an INDI driver.'''
        self.logger.info(f"remove property {p.getName()} as {p.getTypeAsString()} for device {p.getDeviceName()}")

    def newMessage(self, d, m):
        '''Emmited when a new message arrives from INDI server.'''
        self.logger.info(f"new Message {d.messageQueue(m)}")

    def serverConnected(self):
        '''Emmited when the server is connected.'''
        self.logger.info(f"Server connected ({self.getHost()}:{self.getPort()})")

    def serverDisconnected(self, code):
        '''Emmited when the server gets disconnected.'''
        self.logger.info(f"Server disconnected (exit code = {code},{self.getHost()}:{self.getPort()})")

#logging.basicConfig(format = '%(asctime)s %(message)s', level = logging.INFO)

# Create an instance of the IndiClient class and initialize its host/port members
indiClient=IndiClient()
indiClient.setServer("localhost", 7624)

# Connect to server
print("Connecting and waiting 1 sec")
if not indiClient.connectServer():
     print(f"No indiserver running on {indiClient.getHost()}:{indiClient.getPort()} - Try to run")
     print("  indiserver indi_simulator_telescope indi_simulator_ccd")
     sys.exit(1)

# Waiting for discover devices
time.sleep(1)


# Extract RA and dec from the mount
# Note: the device name may not be called 'Telescope',
# the ptoperty may not be called 'EQUATORIAL_EOD_COORD'
mountDeviceName = "Telescope Simulator"
coordinatesPropertyName = "EQUATORIAL_EOD_COORD"

# Select the device corresponding to the telescope mount
deviceList = indiClient.getDevices()
for device in deviceList:
	if device.getDeviceName()==mountDeviceName:		
		# Get list of properties for this device
		genericPropertyList = device.getProperties()
		# Select the equatorial coordinates property
		for genericProperty in genericPropertyList:			
			if genericProperty.getName()==coordinatesPropertyName:
				# Read ra and dec
				for widget in PyIndi.PropertyNumber(genericProperty):
					# read ra
					if widget.getName()=="RA":
						ra = widget.getValue()
					# read dec
					elif widget.getName()=="DEC":
						dec = widget.getValue()

print("Equatorial coordinates read:")
print("RA="+str(ra))
print("Dec="+str(dec))

# Disconnect from the indiserver
print("Disconnecting")
indiClient.disconnectServer()



