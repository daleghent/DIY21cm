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


#####################################################
# Constants

# 21cm line rest-frame frequency
nu21cm = 1420405751.768 # [Hz]


#####################################################
# User parameters

def getDefaultParams():
   '''INDI parameters,
   exposure parameters,
   frequency-shifted exposure parameters.
   '''
   param = {}

   # INDI parameters
   # Note: the device name may not be called 'Telescope',
   # the ptoperty may not be called 'EQUATORIAL_EOD_COORD'
   #mountDeviceName = "Telescope Simulator"
   param['mountDeviceName'] = "AZ-GTi Alt-Az WiFi"
   param['raDecPropertyName'] = "EQUATORIAL_EOD_COORD"
   param['latLonPropertyName'] = "GEOGRAPHIC_COORD"

   # Exposure parameters
   param['nSample'] = 8192 # samples per call to the SDR, to avoid loading too much in RAM
   param['nBin'] = 512   #1024   #2048   # number of freq bins for  power spectrum 
   param['gain'] = 49.6 # [dB] of RtlSdr gain
   param['sampleRate'] = 2.32e6   #3.2e6  # [Hz] sample rate of the SDR, which determines bandwidth of spectrum
   param['centerFrequency'] = nu21cm # [GHz] center frequency
   param['integrationTime'] = 30  #5 * 60  # [sec] integration time

   # Frequency shifting parameters
   #throwFrequency = nu21cm + 1.e6 # [Hz] alternate frequency. The freq diff has to be less than achieved bandwidth
   frequencyShift = 2.5e6   # freq offset between fiducial and shifted frequencies [Hz]
   param['throwFrequency'] = nu21cm + frequencyShift # [Hz] alternate frequency. The freq diff has to be less than achieved bandwidth
   # Too bad, I would like a shift of 3.e6 Hz for my 21cm line...
   param['alternatingFrequency'] = 1.   # [Hz] frequency at which we switch between fiducial and shifted freqs

   return param

def setDate(param):
   '''get today's date as yyyymmdd
   '''
   param['dateCapture'] = datetime.today().strftime("%Y%m%d")

def setTime(param):
   '''Get current time as hh:mm:ss
   '''
   param['timeCapture'] = datetime.now().strftime("%Hh%Mm%Ss")

def setExpType(param, expType):
   ''' expType='fOn', 'fOff', 'fSwitch'
   '''
   param['expType'] = expType





#################################################################
# INDI: acquire current ra, dec from go-to mount

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


def listINDIDevices():
   '''List all devices and properties
   connected to INDI server.
   Useful for debugging.
   '''
   # Print all INDI messages
   logging.basicConfig(format = '%(asctime)s %(message)s', level = logging.INFO)

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

   # Print list of devices. The list is obtained from the wrapper function getDevices as indiClient is an instance
   # of PyIndi.BaseClient and the original C++ array is mapped to a Python List. Each device in this list is an
   # instance of PyIndi.BaseDevice, so we use getDeviceName to print its actual name.
   print("List of devices")
   deviceList = indiClient.getDevices()
   for device in deviceList:
       print(f"   > {device.getDeviceName()}")

   # Print all properties and their associated values.
   print("List of Device Properties")
   for device in deviceList:

       print(f"-- {device.getDeviceName()}")
       genericPropertyList = device.getProperties()

       for genericProperty in genericPropertyList:
           print(f"   > {genericProperty.getName()} {genericProperty.getTypeAsString()}")

           if genericProperty.getType() == PyIndi.INDI_TEXT:
               for widget in PyIndi.PropertyText(genericProperty):
                   print(f"       {widget.getName()}({widget.getLabel()}) = {widget.getText()}")

           if genericProperty.getType() == PyIndi.INDI_NUMBER:
               for widget in PyIndi.PropertyNumber(genericProperty):
                   print(f"       {widget.getName()}({widget.getLabel()}) = {widget.getValue()}")

           if genericProperty.getType() == PyIndi.INDI_SWITCH:
               for widget in PyIndi.PropertySwitch(genericProperty):
                   print(f"       {widget.getName()}({widget.getLabel()}) = {widget.getStateAsString()}")

           if genericProperty.getType() == PyIndi.INDI_LIGHT:
               for widget in PyIndi.PropertyLight(genericProperty):
                   print(f"       {widget.getLabel()}({widget.getLabel()}) = {widget.getStateAsString()}")
           
           if genericProperty.getType() == PyIndi.INDI_BLOB:
               for widget in PyIndi.PropertyBlob(genericProperty):
                   print(f"       {widget.getName()}({widget.getLabel()}) = <blob {widget.getSize()} bytes>")

   # Disconnect from the indiserver
   print("Disconnecting")
   indiClient.disconnectServer()


def setMountInfo(param):
   '''Get mount info from INDI server:
   ra, dec, lat, lon.
   '''
   # Parameters to be read from INDI server
   param['ra'] = np.nan
   param['dec'] = np.nan
   param['lat'] = np.nan
   param['lon'] = np.nan
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
         if device.getDeviceName()==param['mountDeviceName']:		
            # Get list of properties for this device
            genericPropertyList = device.getProperties()
            for genericProperty in genericPropertyList:			

               # Select the equatorial coordinates property
               if genericProperty.getName()==param['raDecPropertyName']:
                  for widget in PyIndi.PropertyNumber(genericProperty):
                     # read ra
                     if widget.getName()=="RA":
                        param['ra'] = widget.getValue()
                     # read dec
                     elif widget.getName()=="DEC":
                        param['dec'] = widget.getValue()


               # Select the geographic coordinates property
               if genericProperty.getName()==param['latLonPropertyName']:
                  for widget in PyIndi.PropertyNumber(genericProperty):
                     # read latitude
                     elif widget.getName()=="LAT":
                        param['lat'] = widget.getValue() # [deg]
                     # read longitude
                     if widget.getName()=="LONG":
                        param['lon'] = widget.getValue() # [deg]

   print("Mount info from INDI server:")
   print("RA = "+str(param['ra'])+" deg")
   print("Dec="+str(param['dec'])+" deg")
   print("Lat="+str(param['lat'])+" deg")
   print("Lon="+str(param['lon'])+" deg")


#####################################################
# Set output and figure file names, complete header


def setOutputFigDir(param):
   '''Create output and figure folders
   if they don't already exist.
   Add to param dictionary.
   '''
   # Output path
   pathOut = "./output/"+param['dateCapture']
   if not os.path.exists(pathOut):
      os.makedirs(pathOut)
   param['pathOut'] = pathOut

   # Figures path
   pathFig = "./figures/"+param['dateCapture']
   if not os.path.exists(pathFig):
      os.makedirs(pathFig)
   param['pathFig'] = pathFig


def setFileName(param):
   '''Set base name for output/pdf/yaml files.
   '''
   # File name
   fileName = "exposure_ra"+str(param['ra'])+"_dec"+str(param['dec'])
   fileName += "_"+str(param['integrationTime'])+"sec"
   fileName += "_"+param['dateCapture']+"_"+param['timeCapture']
   fileName += "_"+param['expType']
   param['fileName'] = fileName




def setHeaderOutputFile(param):
   '''create header for output file
   to log the requested parameters.
   '''

   headerOutputFile =  "Capture date = "+param['dateCapture']+"\n"
   headerOutputFile += "Capture time = "+param['timeCapture']+"\n"

   headerOutputFile += "Geographic coordinates:\n"
   headerOutputFile += "lat = "+str(param['lat'])+" # [deg]\n"
   headerOutputFile += "lon = "+str(param['lon'])+" # [deg]\n"

   headerOutputFile += "Equatorial coordinates:\n"
   headerOutputFile += "ra = "+str(param['ra'])+" # [deg]\n"
   headerOutputFile += "dec = "+str(param['dec'])+" # [deg]\n"

   headerOutputFile += "Exposure settings:\n"
   headerOutputFile += "exposure type = "+str(param['expType'])+"\n"
   headerOutputFile += "nSample = "+str(param['nSample'])+" # samples per call to the SDR\n"
   headerOutputFile += "nBin = "+str(param['nBin'])+" # bin resolution power spectrum \n"
   headerOutputFile += "gain = "+str(param['gain'])+" # [dB] of RtlSdr gain\n"
   headerOutputFile += "sample rate = "+str(param['sampleRate'])+" # [Hz] controls bandwidth\n"
   headerOutputFile += "centerFrequency = "+str(param['centerFrequency'])+" # [Hz] center frequency\n"
   headerOutputFile += "integrationTime = "+str(param['integrationTime'])+" # [sec] integration time\n"
   headerOutputFile += "alternateFrequency = "+str(param['throwFrequency'])+" # [Hz] alternate frequency\n"
   headerOutputFile += "alternatingFrequency = "+str(param['alternatingFrequency'])+" # [Hz] alternating frequency\n"
   headerOutputFile += "freq [Hz], power On [V^2/Hz], power Off [V^2/Hz]\n"

   param['headerOutputFile'] = headerOutputFile


#################################################################
# RTL SDR

def biasTOn():
   '''Turn on the bias T,
   to power the LNA.
   '''
   try:
      ut.biast(1, index=0) # turn on bias tee, to power LNA
   except:
      print('Failed to turn on bias T')

def biasTOff():
   '''Turn off the bias T,
   to power off the LNA.
   '''
   try:
      ut.biast(0, index=0) # turn on bias tee, to power LNA
   except:
      print('Failed to turn off bias T')




def takeExposure(param):

   try:
      # get f [Hz], p [V^2/Hz]
      tStart = time.time()
      #
      if param['expType']=='fOn':
         f, p = col.run_spectrum_int(param['nSample'], 
                                     param['nBin'], 
                                     param['gain'], 
                                     param['sampleRate'], 
                                     param['centerFrequency'], 
                                     param['integrationTime'])
         param['fOn'] = f
         param['pOn'] = p
         param['expStatus'] = True
      #
      elif param['expType']=='fOff':
         f, p = col.run_spectrum_int(param['nSample'], 
                                     param['nBin'], 
                                     param['gain'], 
                                     param['sampleRate'], 
                                     param['throwFrequency'], 
                                     param['integrationTime'])
         param['fOff'] = f
         param['pOff'] = p
         param['expStatus'] = True
      #
      elif param['expType']=='fSwitch':
         fOn, pOn, fOff, pOff = col.run_fswitch_int(param['nSample'], 
                                    param['nBin'], 
                                    param['gain'], 
                                    param['sampleRate'], 
                                    param['centerFrequency'], 
                                    param['throwFrequency'], 
                                    param['integrationTime'], 
                                    fswitch=param['alternatingFrequency'])
         param['fOn'] = fOn
         param['pOn'] = pOn
         param['fOff'] = fOff
         param['pOff'] = pOff
         param['expStatus'] = True
      #
      else:
         param['expStatus'] = False
      #
      tStop = time.time()
      print("Single exposure of "+str(param['integrationTime'])+" sec took "+str(round(tStop-tStart))+" sec")
      print("Time overhead is "+str(round( ((tStop-tStart)/param['integrationTime'] -1)*100. ))+"%")

   except:
      print('Exposure failed')
      param['expStatus'] = False



def saveYaml(param):
   # save the exposure parameters
   with open(param['pathOut']+"/"+param['fileName']+".yaml", 'w') as file:
      yaml.dump(param, file, sort_keys=False)
      print('Saved yaml file')


def saveData(param):
   # Check if the exposure was successfully acquired
   if param['expStatus']:
      # save the power spectrum
      if param['expType']=='fOn':
         data = np.column_stack((param['fOn'], 
                                 param['pOn']))
      elif param['expType']=='fOff':
         data = np.column_stack((param['fOff'], 
                                 param['pOff']))
      elif param['expType']=='fSwitch':
         data = np.column_stack((param['fOn'], 
                                 param['pOn'],
                                 param['fOff'],
                                 param['pOff']))
      np.savetxt(param['pathOut']+"/"+param['fileName']+".txt", 
                 data, 
                 header=param['headerOutputFile'])

def savePlot(param):
   # Check if the exposure was successfully acquired
   if param['expStatus']:
      fig=plt.figure(0)
      ax=fig.add_subplot(111)
      #
      if param['expType']=='fOn':
         ax.semilogy(param['fOn'], param['pOn'], label=r'On')
      elif param['expType']=='fOff':
         ax.semilogy(param['fOff'], param['pOff'], label=r'Off')
      elif param['expType']=='fSwitch':
         ax.semilogy(param['fOn'], param['pOn'], label=r'On')
         ax.semilogy(param['fOff'], param['pOff'], label=r'Off')
      #
      ax.legend(loc=1)
      ax.set_xlabel(r'freq [Hz]')
      ax.set_ylabel(r'P [V^2/Hz]')
      fig.savefig(param['pathFig']+"/"+param['fileName']+".pdf", bbox_inches='tight')
      #fig.show()
      fig.clf()


#####################################################
#####################################################
#####################################################

if __name__=="__main__":
   
   # List all INDI devices and properties
   # for debugging
   #listINDIDevices():

   # Turn on bias T to power LNA
   biasTOn()

   # For each exposure
   param = getDefaultParams()
   
   # Change exposure time if desired
   param['integrationTime'] = 5 #5*60  # [sec]

   # Choose center frequency: 'fOn', 'fOff', 'fSwitch'
   setExpType(param, 'fOn')
   #setExpType(param, 'fOff')
   #setExpType(param, 'fSwitch')

   setDate(param)
   setTime(param)
   setMountInfo(param)

   setOutputFigDir(param)
   setFileName(param)
   setHeaderOutputFile(param)
   
   takeExposure(param)

   saveYaml(param)
   saveData(param)
   savePlot(param)

   # Turn off bias T to power off LNA
   biasTOff()
