#!/home/stellarmate/miniforge3/bin/python3
# Before running this python script,
# start an INDI server, either in ekos gui, or with the command line:
# indiserver indi_simulator_telescope

import numpy as np
import matplotlib.pyplot as plt

# for logging
import time
import logging

# to save output data and parameters
from datetime import datetime
import yaml
import os

# To communicate with mount and get ra, dec
import PyIndi

# To communicate with RTL SDR
# If running outside of the rtlobs github repo,
# add path
import sys
sys.path.append('/home/stellarmate/rtlobs')
from rtlobs import collect as col
from rtlobs import post_process as post
from rtlobs import utils as ut


#################################################################
# User parameters

# INDI parameters
# Note: the device name may not be called 'Telescope',
# the ptoperty may not be called 'EQUATORIAL_EOD_COORD'
#mountDeviceName = "Telescope Simulator"
mountDeviceName = "AZ-GTi Equatorial WiFi"
coordinatesPropertyName = "EQUATORIAL_EOD_COORD"

# exposure parameters
param = {}
param['nSample'] = 8192 # samples per call to the SDR
param['nBin'] = 2048   # bin resolution power spectrum 
param['gain'] = 49.6 # [dB] of RtlSdr gain
param['bandwidth'] = 2.32e6  # [Hz] sample rate/bandwidth
param['centerFrequency'] = 1.420e9 # [GHz] center frequency
param['integrationTime'] = 3  #20  # [sec] integration time

# create header for output file to log these parameters
headerOutputFile =  "Exposure settings:\n"
headerOutputFile += "nSample = "+str(param['nSample'])+" # samples per call to the SDR\n"
headerOutputFile += "nBin = "+str(param['nBin'])+" # bin resolution power spectrum \n"
headerOutputFile += "gain = "+str(param['gain'])+" # [dB] of RtlSdr gain\n"
headerOutputFile += "bandwidth = "+str(param['bandwidth'])+" # [Hz] sample rate/bandwidth\n"
headerOutputFile += "centerFrequency = "+str(param['centerFrequency'])+" # [GHz] center frequency\n"
headerOutputFile += "integrationTime = "+str(param['integrationTime'])+" # [sec] integration time\n"


#################################################################
# Create output and figure folders

# get today's date as yyyymmdd
param['dateCapture'] = datetime.today().strftime("%Y%m%d")

# Output path
pathOut = "./output/"+param['dateCapture']
if not os.path.exists(pathOut):
   os.makedirs(pathOut)

# Figures path
pathFig = "./figures/"+param['dateCapture']
if not os.path.exists(pathFig):
   os.makedirs(pathFig)


#################################################################
# INDI: acquire current ra, dec from mount

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

# Print all INDI messages
#logging.basicConfig(format = '%(asctime)s %(message)s', level = logging.INFO)


# Try reading ra, dec from mount
try:
   # Create an instance of the IndiClient class and initialize its host/port members
   indiClient=IndiClient()
   indiClient.setServer("localhost", 7624)

   # Connect to server
   print("Connecting and waiting 1 sec")
   if not indiClient.connectServer():
        print(f"No indiserver running on {indiClient.getHost()}:{indiClient.getPort()} - Try to run")
        print("  indiserver indi_simulator_telescope indi_simulator_ccd")
        sys.exit(1)

   # Waiting to discover devices
   time.sleep(1)

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
                     param['ra'] = widget.getValue()
                  # read dec
                  elif widget.getName()=="DEC":
                     param['dec'] = widget.getValue()
   print("Successfully acquired coordinates")

   # Disconnect from the indiserver
   print("Disconnecting")
   indiClient.disconnectServer()

# If this did not work, set ra, dec to nan
except:
   param['ra'] = np.nan
   param['dec'] = np.nan
   print("Failed to acquire coordinates")
   print("Check INDI server is running?")
   print("Check device name, coordinate property name?")

print("RA="+str(param['ra']))
print("Dec="+str(param['dec']))


#################################################################
# Set output and figure file names, complete header

# get current time as hh:mm:ss
param['timeCapture'] = datetime.now().strftime("%Hh%Mm%Ss")

# File name
fileName = "exposure_ra"+str(param['ra'])+"_dec"+str(param['dec'])
fileName += "_"+str(param['integrationTime'])+"sec"
fileName += param['dateCapture']+"_"+param['timeCapture']

# header
headerOutputFile += "Equatorial coordinates:\n"
headerOutputFile += "ra = "+str(param['ra'])+" # [hours]\n"
headerOutputFile += "dec = "+str(param['dec'])+" # [deg]\n"
headerOutputFile += "Capture date = "+param['dateCapture']+"\n"
headerOutputFile += "Capture time = "+param['timeCapture']+"\n"
headerOutputFile += "freq [Hz], power [dB/Hz]\n"


#################################################################
# Take an exposure with the RTL SDR

try:
   ut.biast(1, index=0) # turn on bias tee, to power LNA
   #ut.biast(0, index=0) # turn off bias tee, to power LNA

   # Take exposure: measure power spectrum
   f, p = col.run_spectrum_int(param['nSample'], param['nBin'], param['gain'], param['bandwidth'], param['centerFrequency'], param['integrationTime'])

   # print the power spectrum
   #print(f)
   #print(p)

   # save the exposure parameters
   with open(pathOut+"/"+fileName+".yaml", 'w') as file:
      yaml.dump(param, file, sort_keys=False)

   # save the power spectrum
   data = np.zeros((len(f), 2))
   data[:,0] = f
   data[:,1] = p
   np.savetxt(pathOut+"/"+fileName+".txt", data, header=headerOutputFile)

   # Save power spectrum plot
   fig, ax = post.plot_spectrum(f, p, savefig=pathFig+"/"+fileName+".pdf")
   #fig.show()
   fig.clf()

except:
   print("Failed to either turn on bias T or take exposure")
   print("Is RTL SDR properly connected?")

