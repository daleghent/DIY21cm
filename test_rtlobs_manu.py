import numpy as np
import matplotlib.pyplot as plt
from time import time

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
nSample = 8192 # samples per call to the SDR, to avoid loading too much in RAM
nBin =  512 #1024   #2048   # number of freq bins for  power spectrum 
gain = 49.6 # [dB] of RtlSdr gain
sampleRate = 2.32e6  #3.2e6  # [Hz] sample rate of the SDR, which determines bandwidth of spectrum
centerFrequency = nu21cm # [Hz] center frequency
integrationTime = 5  #5 * 60  # [sec] integration time

# Frequency shifting parameters
#throwFrequency = nu21cm + 1.e6 # [Hz] alternate frequency. The freq diff has to be less than achieved bandwidth
frequencyShift = 2.5e6   # freq offset between fiducial and shifted frequencies [Hz]
throwFrequency = nu21cm + frequencyShift # [Hz] alternate frequency. The freq diff has to be less than achieved bandwidth
# Too bad, I would like a shift of 3.e6 Hz for my 21cm line...
alternatingFrequency = 1.   # [Hz] frequency at which we switch between fiducial and shifted freqs


############################################################
# The LNA needs to be powered, to amplify around 1.42GHz

ut.biast(1, index=0) # turn on bias tee, to power LNA
#ut.biast(0, index=0) # turn off bias tee, to power off LNA


############################################################
# Measure power spectrum around 21cm frequency

tStart = time()

# get f [Hz], p [V^2/Hz]
f, p = col.run_spectrum_int(nSample, 
                            nBin, 
                            gain, 
                            sampleRate, 
                            centerFrequency, 
                            integrationTime)

tStop = time()
print("Single exposure of "+str(integrationTime)+" sec took "+str(round(tStop-tStart))+" sec")
print("Time overhead is "+str(round( ((tStop-tStart)/integrationTime -1)*100. ))+"%")

print("Achieved bandwidth is "+str(round( (np.max(f) - np.min(f)) / 1.e6, 1))+" MHz")
print("Achieved bandwidth corresponds to +/-"+str(round( (np.max(f)/nu21cm - 1.) * 299792.458, 1))+" km/s")
print("Sufficient bandwidth for Galactic 21cm is +/-150 km/s, or if possible +/-200 km/s")


############################################################
# Measure power spectrum with frequency switching

tStart = time()

# this time, the integration time is split between the fiducial and shifted freqs,
# so the integration time on the fiducial freq is half of this number.
# get f [Hz], p [V^2/Hz]
fOn, pOn, fOff, pOff = col.run_fswitch_int(nSample, 
                           nBin, 
                           gain, 
                           sampleRate, 
                           centerFrequency, 
                           throwFrequency, 
                           integrationTime, 
                           fswitch=alternatingFrequency)

tStop = time()
print("Freq switched exposure of "+str(integrationTime)+" sec took "+str(round(tStop-tStart))+" sec")
print("Time overhead is "+str(round( ((tStop-tStart)/integrationTime -1)*100. ))+"%")


############################################################
# Measure power spectrum above and below 21cm frequency

tStart = time()

# get f [Hz], p [V^2/Hz]
fHigh, pHigh = col.run_spectrum_int(nSample, 
                            nBin, 
                            gain, 
                            sampleRate, 
                            centerFrequency + frequencyShift, 
                            integrationTime)

# get f [Hz], p [V^2/Hz]
fLow, pLow = col.run_spectrum_int(nSample, 
                            nBin, 
                            gain, 
                            sampleRate, 
                            centerFrequency - frequencyShift, 
                            integrationTime)


############################################################
# The LNA needs to be powered, to amplify around 1.42GHz

#ut.biast(1, index=0) # turn on bias tee, to power LNA
ut.biast(0, index=0) # turn off bias tee, to power off LNA


############################################################
# Plot

pDiff = pOn - pOff
factor = np.mean(pOn)/np.mean(pOff)
pDiffSmart = pOn -  factor * pOff

pBase = (pHigh + pLow) / 2.
pDiffBase = p - pBase
factorBase = np.mean(p)/np.mean(pBase)
pDiffBaseSmart = p - pBase * factorBase

# Show the figure containing the plotted spectrum
fig=plt.figure(0)
ax=fig.add_subplot(111)
ax.semilogy(f, p, 'k', lw=3, label=r'Fiducial')
ax.semilogy(fOn, pOn, '--', label=r'On')
ax.semilogy(fOff, pOff, label=r'Off')
ax.semilogy(fLow, pLow, label=r'Low')
ax.semilogy(fHigh, pHigh, '--', label=r'High')
ax.semilogy(f, pBase, label=r'Base')
#ax.semilogy(fOn, np.abs(pDiff), label=r'On-Off')
ax.semilogy(fOn, np.abs(pDiffSmart), label=r'On-Off_rescaled')
#ax.semilogy(f, np.abs(pDiffBase), label=r'On - (Low+High)/2')
ax.semilogy(f, np.abs(pDiffBaseSmart), label=r'On - (Low+High)/2_rescaled')
#
ax.legend(loc=4, fontsize='x-small', labelspacing=0.2)
ax.set_ylim((1.e-11, 2.*np.max(p)))
ax.set_xlabel(r'freq [Hz]')
ax.set_ylabel(r'P [V^2/Hz]')
fig.savefig('./figures/sandbox/spectrum_fswitch_'+str(integrationTime)+'sec.pdf', bbox_inches='tight')
#fig.show()
fig.clf()

