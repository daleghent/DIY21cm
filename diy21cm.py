#!/home/stellarmate/anaconda3/bin/python3
# Before running this python script,
# start an INDI server, either in ekos gui, or with the command line:
# indiserver indi_simulator_telescope
# I want to add another comment here as well

import numpy as np, matplotlib.pyplot as plt
# for colormaps in plots
from matplotlib import cm
from matplotlib.colors import Normalize
# to format the labels of tick marks
from matplotlib.ticker import FuncFormatter

# for logging
import time, logging, os
from datetime import datetime
import json_io as json
import subprocess # to run shell commands

# To communicate with mount and get ra, dec
import PyIndi

# To communicate with RTL SDR
# If running outside of the rtlobs github repo,
# add path
import sys
sys.path.append('/home/stellarmate/rtlobs')
from rtlobs import collect as col, post_process as post, utils as ut


#####################################################
# Constants

c = 299792458  # speed of light [m/s]

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
   '''Set current date as yyyymmdd
   '''
   param['dateCapture'] = datetime.today().strftime("%Y%m%d")


def setTime(param):
   '''Set current time as hh:mm:ss
   '''
   param['timeCapture'] = datetime.now().strftime("%Hh%Mm%Ss")


def setTimeSameDate(param, paramStart):
   '''Set same date as start date,
   and set current time as hh:mm:ss,
   where hh adds 24 for every day that elapsed
   since the start date.
   '''
   # start by setting the date to the start date
   param['dateCapture'] = paramStart['dateCapture']
   # set the time to the current time
   setTime(param)

   # Add 24 to the hours for each day elapsed
   # compute number of days elapsed since start
   nDays = (datetime.today() - datetime.strptime(paramStart['dateCapture'], "%Y%m%d")).days
   # Find the position of 'h' in time string
   h_index = param['timeCapture'].index('h')
   m_index = param['timeCapture'].index('m')
   s_index = param['timeCapture'].index('s')
   # extract the hours, minutes and seconds
   hours = int(param['timeCapture'][:h_index])
   minutes = int(param['timeCapture'][h_index + 1:m_index])
   seconds = int(param['timeCapture'][m_index + 1:s_index])
   # Add 24 hours to the extracted hours
   hours += 24 * nDays
   # Format the new time string
   param['timeCapture'] = f'{hours}h{minutes}m{seconds}s'



def setExpType(param, expType):
   ''' expType='on', 'foff', 'fswitch', 'hot', 'cold'
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
                     if widget.getName()=="LAT":
                        param['lat'] = widget.getValue() # [deg]
                     # read longitude
                     elif widget.getName()=="LONG":
                        param['lon'] = widget.getValue() # [deg]

   except:
      print("Could not read ra, dec from mount")

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
   '''Set base name for output/pdf files.
   '''
   # File name
   fileName = param['dateCapture']+"_"+param['timeCapture']
   fileName += "_exposure_"+param['expType']
   fileName += "_"+str(param['integrationTime'])+"sec"
   fileName += "_ra"+str(param['ra'])+"_dec"+str(param['dec'])
   param['fileName'] = fileName


def getLatestName(param, expType=None):
   '''Set base name for "latests" output/pdf files.
   '''
   # File name
   fileName = "latest"
   if expType is None:
      fileName += "_exposure_"+param['expType']
   else:
      fileName += "_exposure_"+expType
   fileName += "_"+str(param['integrationTime'])+"sec"
   return fileName


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
      if param['expType']=='on' or param['expType']=='hot' or param['expType']=='cold':
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
      elif param['expType']=='foff':
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
      elif param['expType']=='fswitch':
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



def calibrateHotCold(p, pH, pC, tH, tC):
   '''compute calibrated temperature spectum t [K]
   from power spectra p, pH, pC [any unit]
   measured at temperatures t, tH, tC [K].
   Assumes
   p = factor * (t + tOffset)
   '''
   # Solve for affine parameters
   factor = (pH - pC) / (tH - tC)  # [dimless]
   tOffset = (tH * pC - tC * pH) / (pH - pC) # [K]
   # invert the power to temperature relation
   t = p / factor - tOffset   # [K]
   return t


def calibratePartial(p, pRef, tRef):
   '''compute partially-calibrated temperature spectrum t [K]
   from power spectrum p [au],
   based on a reference power spectrum pRef [au]
   measured at temperature tRef [K].
   Assumes
   p = factor * t
   '''
   t = tRef * p / pRef  # [K]
   return t


def attemptCalibration(param):
   '''Check if a latest hot and/or cold exposure
   exists in the output folder.
   If so, use them/it for complete/partial calibration.
   '''
   # flag to indicate if calibrations are possible
   partialCalib = False
   fullCalib = True

   # check if cold exposure exists
   pathCold = param['pathOut']+'/'+getLatestName(param, expType='cold')+'.json'
   if os.path.exists(pathCold):
      paramCold = json.loadJson(pathCold)
      param['pCold'] = paramCold['pOn']
      partialCalib = True
   else:
      fullCalib = False

   # check if hot exposure exists
   pathHot = param['pathOut']+'/'+getLatestName(param, expType='hot')+'.json'
   if os.path.exists(pathHot):
      paramHot = json.loadJson(pathHot)
      param['pHot'] = paramHot['pOn']
      partialCalib = True
   else:
      fullCalib = False

   # perform full calibration if possible
   if fullCalib:
      param['tCalibratedHotCold'] = calibrateHotCold(param['pOn'], 
            param['pHot'], 
            param['pCold'], 
            300., # tHot [K] 
            20.)  # tCold [K]
   # else perform partial calibration if possible
   elif partialCalib:
      if 'pCold' in param:
         pRef = param['pCold']
         param['tCalibratedCold'] = calibratePartial(param['pOn'], 
               pRef, 
               20.)  # tCold [K]
      elif 'pHot' in param:
         pRef = param['pHot']
         param['tCalibratedHot'] = calibratePartial(param['pOn'], 
               pRef, 
               300.)  # tCold [K]



def saveJson(param):
   # save all parameters and data
   path = param['pathOut']+"/"+param['fileName']+".json"
   json.saveJson(param, path)

   # also save to/overwrite the "latest"
   path = param['pathOut']+"/"+getLatestName(param)+".json"
   json.saveJson(param, path)


def plot(f, p, label=None, yLabel=r'Uncalibrated intensity [au]'):
    fig=plt.figure(0)
    ax=fig.add_subplot(111)
    #
    ax.axvline(0., c='k', label=r'$\nu^0_\text{21cm}$')

    # Plot the data, or the list of data
    # Color map for the curves
    cmap = cm.viridis  # You can choose other colormaps like 'plasma', 'inferno', etc.
    norm = Normalize(vmin=0, vmax=max(len(f), len(p)) - 1)  # Normalize based on number of datasets

    # Handle different types of f and p
    if isinstance(f, list):  # f is a list of 1D arrays
        if len(f) != len(p):
            raise ValueError("f and p must have the same length if they are lists.")
        for i, (f_arr, p_arr) in enumerate(zip(f, p)):
            color = cmap(norm(i))  # Get color based on index
            x = (f_arr - nu21cm) / 1.e6  # Convert to MHz
            ax.plot(x, p_arr, label=label, color=color)

    elif isinstance(f, np.ndarray):  # f is a 1D or 2D numpy array
        if f.ndim == 1:  # f is a 1D array
            x = (f - nu21cm) / 1.e6  # Convert to MHz
            ax.plot(x, p, label=label)
        elif f.ndim == 2:  # f is a 2D array (list of 1D arrays)
            if f.shape[0] != p.shape[0]:
                raise ValueError("f and p must have the same number of rows if they are 2D arrays.")
            for i, (f_arr, p_arr) in enumerate(zip(f, p)):
                color = cmap(norm(i))  # Get color based on index
                x = (f_arr - nu21cm) / 1.e6  # Convert to MHz
                ax.plot(x, p_arr, label=label, color=color)
    else:
        raise TypeError("f must be either a list, 1D numpy array, or 2D numpy array.")

    ax.legend(loc=2)
    ax.set_xlabel(r'$\nu - \nu^0_\text{21cm}$ [MHz]')
    ax.set_ylabel(yLabel)
    #
    # Add alternate x axis showing velocities
    x_to_vel = lambda x: (x * 1.e6 / nu21cm) * c * 1.e-3  # Convert frequency to velocity (km/s)
    vel_to_x = lambda v: v / 1.e6 * nu21cm / c / 1.e-3
    #
    ax2 = ax.secondary_xaxis('top', functions=(x_to_vel, vel_to_x))
    ax2.set_xlabel(r'$v_\text{LOS}$ [km/s]')
    # Optional: Customize tick labels using FuncFormatter
    ax2.xaxis.set_major_formatter(FuncFormatter(lambda val, pos: f'{val:.1f}'))  # Optional rounding


    return fig, ax, ax2






def savePlot(param):
   # Generate plots only if the exposure was successfully acquired
   if param['expStatus']:
      if param['expType']=='on' or param['expType']=='hot' or param['expType']=='cold':
         fig, ax, ax2 = plot(param['fOn'], param['pOn'], label=param['expType'], yLabel=r'P [V$^2$/Hz]')
      elif param['expType']=='foff':
         fig, ax, ax2 = plot(param['fOff'], param['pOff'], label=r'fOff', yLabel=r'P [V$^2$/Hz]')
      elif param['expType']=='fswitch':
         fig, ax, ax2 = plot(param['fOn'], param['pOn'], label=r'on', yLabel=r'P [V$^2$/Hz]')
         ax.plot(param['fOff'], param['pOff'], label=r'fOff')
      
      # if the exposure is on, and hot and/or cold exposures are available,
      # then overplot them.
      if param['expType']=='on':
         for key in set(param.keys()) & {'pCold', 'pHot'}:
            ax.plot((param['fOn'] - nu21cm) / 1.e6, param[key], '--', label=key)
            ax.legend(loc=2)

      # save to unique file name
      fig.savefig(param['pathFig']+"/"+param['fileName']+".pdf", bbox_inches='tight')
      # also save to/overwrite the "latest"
      fig.savefig(param['pathFig']+"/"+getLatestName(param)+".pdf", bbox_inches='tight')
      #
      fig.clf()


      # If calibrated or partially calibrated temperature spectra are avilable,
      # plot them
      for key in set(param.keys()) & {'tCalibratedHotCold', 'tCalibratedHot', 'tCalibratedCold'}:
         fig, ax, ax2 = plot(param['fOn'], param[key], label=key, yLabel=r'Antenna temperature [K]')
      
         # save to unique file name
         fig.savefig(param['pathFig']+"/"+param['fileName']+"_"+key+".pdf", bbox_inches='tight')
         # also save to/overwrite the "latest"
         fig.savefig(param['pathFig']+"/"+getLatestName(param)+"_"+key+".pdf", bbox_inches='tight')
         #
         fig.clf()

def saveScreenshot(param):
   '''Save a screenshot to the figures folder.
   Useful in transiting mode, to generate a timelapse.
   '''
   # Save screenshot in figures folder
   screenshotPath = param['pathFig']+"/"+param['fileName']+"_"+"scrot.png"

   try:
      result = subprocess.run(['scrot', screenshotPath], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      print(f"Screenshot saved to {screenshotPath}")
   except subprocess.CalledProcessError as e:
      print(f"Error occurred: {e.stderr.decode()}")
   except FileNotFoundError:
      print("scrot command not found. Make sure scrot is installed and in your PATH.")




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

   setExpType(param, 'on')
   #setExpType(param, 'foff')
   #setExpType(param, 'fswitch')
   #d21.setExpType(param, 'cold')
   #d21.setExpType(param, 'hot')


   setDate(param)
   setTime(param)
   setMountInfo(param)

   setOutputFigDir(param)
   setFileName(param)
   
   takeExposure(param)
   attemptCalibration(param)

   saveJson(param)
   savePlot(param)

   # Turn off bias T to power off LNA
   biasTOff()
