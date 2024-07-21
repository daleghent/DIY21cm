#!/home/stellarmate/miniforge3/bin/python3
import numpy as np
import matplotlib.pyplot as plt

# for logging
from time import time
import logging

# to save output data and parameters
from datetime import datetime
import yaml
import os

# If running outside of the rtlobs github repo,
# add path
import sys
sys.path.append('/home/stellarmate/rtlobs')
from rtlobs import collect as col
from rtlobs import post_process as post
from rtlobs import utils as ut


############################################################
# 21cm rest-frame frequency
nu21cm = 1420405751.768 # [Hz]

# Exposure parameters
param = {}
param['nSample'] = 8192 # samples per call to the SDR, to avoid loading too much in RAM
param['nBin'] = 512   #1024   #2048   # number of freq bins for  power spectrum 
param['gain'] = 49.6 # [dB] of RtlSdr gain
param['sampleRate'] = 2.32e6   #3.2e6  # [Hz] sample rate of the SDR, which determines bandwidth of spectrum
param['centerFrequency'] = nu21cm # [GHz] center frequency
param['integrationTime'] = 5*60  #5 * 60  # [sec] integration time

# Frequency shifting parameters
#throwFrequency = nu21cm + 1.e6 # [Hz] alternate frequency. The freq diff has to be less than achieved bandwidth
frequencyShift = 2.5e6   # freq offset between fiducial and shifted frequencies [Hz]
param['throwFrequency'] = nu21cm + frequencyShift # [Hz] alternate frequency. The freq diff has to be less than achieved bandwidth
# Too bad, I would like a shift of 3.e6 Hz for my 21cm line...
param['alternatingFrequency'] = 1.   # [Hz] frequency at which we switch between fiducial and shifted freqs


# create header for output file to log these parameters
headerOutputFile =  "Exposure settings:\n"
headerOutputFile += "nSample = "+str(param['nSample'])+" # samples per call to the SDR\n"
headerOutputFile += "nBin = "+str(param['nBin'])+" # bin resolution power spectrum \n"
headerOutputFile += "gain = "+str(param['gain'])+" # [dB] of RtlSdr gain\n"
headerOutputFile += "sample rate = "+str(param['sampleRate'])+" # [Hz] controls bandwidth\n"
headerOutputFile += "centerFrequency = "+str(param['centerFrequency'])+" # [Hz] center frequency\n"
headerOutputFile += "integrationTime = "+str(param['integrationTime'])+" # [sec] integration time\n"
headerOutputFile += "alternateFrequency = "+str(param['throwFrequency'])+" # [Hz] alternate frequency\n"
headerOutputFile += "alternatingFrequency = "+str(param['alternatingFrequency'])+" # [Hz] alternating frequency\n"


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

############################################################
# The LNA needs to be powered, to amplify around 1.42GHz

ut.biast(1, index=0) # turn on bias tee, to power LNA
#ut.biast(0, index=0) # turn off bias tee, to power off LNA


############################################################
# Take repeated exposures


# Cycle of switched frequencies
Freqs = param['centerFrequency'] + np.array([-1., 0., 1., 0.]) * frequencyShift
FreqLabels = np.array(['low', 'on', 'high', 'on'])

# frequency and power spectrum dictionaries
f = {}
p = {}

# keep taking exposures
tStart = time()
exposureCount = 0
while True:
#while exposureCount<5:

   print('- Attempting exposure number '+str(exposureCount))
   # Add try catch so code won't crash if one exposure fails

   try:
      # center frequency for this exposure
      freq = Freqs[exposureCount % len(Freqs)]
      freqLabel = FreqLabels[exposureCount % len(Freqs)]
      print('Exposure type: '+freqLabel)
      print('Center frequency: '+str(freq/1.e9)+' GHz')


      # get current time as hh:mm:ss
      param['timeCapture'] = datetime.now().strftime("%Hh%Mm%Ss")


      # get f [Hz], p [V^2/Hz]
      tStart = time()
      #
      f[freqLabel], p[freqLabel] = col.run_spectrum_int(param['nSample'], 
                                  param['nBin'], 
                                  param['gain'], 
                                  param['sampleRate'], 
                                  freq, 
                                  param['integrationTime'])
      #
      tStop = time()
      print("Single exposure of "+str(param['integrationTime'])+" sec took "+str(round(tStop-tStart))+" sec")
      print("Time overhead is "+str(round( ((tStop-tStart)/param['integrationTime'] -1)*100. ))+"%")


      # File name
      fileName = "exposure_"+freqLabel
      fileName += "_"+str(param['integrationTime'])+"sec"
      fileName += "_"+param['dateCapture']+"_"+param['timeCapture']

      # header
      headerOutputFileFinal = headerOutputFile + "Capture date = "+param['dateCapture']+"\n"
      headerOutputFileFinal += "Capture time = "+param['timeCapture']+"\n"
      headerOutputFileFinal += "freq [Hz], power On [V^2/Hz], power Off [V^2/Hz]\n"

      # save the exposure parameters
      with open(pathOut+"/"+fileName+".yaml", 'w') as file:
         yaml.dump(param, file, sort_keys=False)

      # save the power spectrum
      data = np.column_stack((f[freqLabel], p[freqLabel]))
      #np.savetxt(pathOut+"/"+fileName+".txt", data, header=headerOutputFile)
      np.savetxt(pathOut+"/"+fileName+".txt", data, header=headerOutputFileFinal)


      # every time a new set of low, on, high is ready
      if freqLabel!='on' and exposureCount>0:

         # compute the reduced spectra
         print('Reducing spectra')
         pBase = (p['high'] + p['low']) / 2.
         pDiffBase = p['on'] - pBase
         factorBase = np.mean(p['on']) / np.mean(pBase)
         pDiffBaseSmart = p['on'] - pBase * factorBase

         # save the reduced power spectrum
         print('Saving reduced spectra')
         data = np.column_stack((f[FreqLabels[(exposureCount - 2) % len(Freqs)]], 
                                 p[FreqLabels[(exposureCount - 2) % len(Freqs)]],
                                 f[FreqLabels[(exposureCount - 1) % len(Freqs)]], 
                                 p[FreqLabels[(exposureCount - 1) % len(Freqs)]],
                                 f[FreqLabels[exposureCount % len(Freqs)]], 
                                 p[FreqLabels[exposureCount % len(Freqs)]],
                                 pBase,
                                 pDiffBase,
                                 pDiffBaseSmart))
         headerOutputFileFinal += 'foff, poff, fon, pon, foff, poff, pBase, pDiffBase, pDiffBaseSmart\n'
         np.savetxt(pathOut+"/"+fileName+"_reduced.txt", data, header=headerOutputFileFinal)

         # Show the figure containing the plotted spectrum
         print('Creating figure')
         fig=plt.figure(0)
         ax=fig.add_subplot(111)
         #
         ax.semilogy(f['on'], p['on'], label=r'On')
         ax.semilogy(f['low'], p['low'], label=r'Low')
         ax.semilogy(f['high'], p['high'], '--', label=r'High')
         ax.semilogy(f['on'], pBase, label=r'Base')
         ax.semilogy(f['on'], np.abs(pDiffBase), label=r'On - (Low+High)/2')
         ax.semilogy(f['on'], np.abs(pDiffBaseSmart), label=r'On - (Low+High)/2_rescaled')
         #
         ax.legend(loc=4, fontsize='x-small', labelspacing=0.2)
         #ax.set_ylim((1.e-11, 2.*np.max(p)))
         ax.set_xlabel(r'freq [Hz]')
         ax.set_ylabel(r'P [V^2/Hz]')
         #
         fig.savefig(pathFig+"/"+fileName+"_reduced.pdf", bbox_inches='tight')
         #fig.show()
         fig.clf()

   except:
      print('Exposure number '+str(exposureCount)+' failed')

   # increment exposure count
   exposureCount += 1


############################################################
# The LNA needs to be powered, to amplify around 1.42GHz

#ut.biast(1, index=0) # turn on bias tee, to power LNA
ut.biast(0, index=0) # turn off bias tee, to power off LNA
