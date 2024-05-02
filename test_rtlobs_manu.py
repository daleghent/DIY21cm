import numpy as np
import matplotlib.pyplot as plt

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
nSample = 8192 # samples per call to the SDR
nBin =  2048   # bin resolution power spectrum 
gain = 49.6 # [dB] of RtlSdr gain
#bandwidth = 2.32e6  # [Hz] sample rate/bandwidth
bandwidth = 3.2e6  # [Hz] sample rate/bandwidth. Try to max it out, limited by the hardware
centerFrequency = nu21cm # [Hz] center frequency
integrationTime = 5  #20  # [sec] integration time

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

# get f [Hz], p [V^2/Hz]
f, p = col.run_spectrum_int(nSample, 
                            nBin, 
                            gain, 
                            bandwidth, 
                            centerFrequency, 
                            integrationTime)


############################################################
# Measure power spectrum with frequency switching

# this time, the integration time is split between the fiducial and shifted freqs,
# so the integration time on the fiducial freq is half of this number.
# get f [Hz], p [V^2/Hz]
fOn, pOn, fOff, pOff = col.run_fswitch_int(nSample, 
                           nBin, 
                           gain, 
                           bandwidth, 
                           centerFrequency, 
                           throwFrequency, 
                           integrationTime, 
                           fswitch=alternatingFrequency)


############################################################
# The LNA needs to be powered, to amplify around 1.42GHz

#ut.biast(1, index=0) # turn on bias tee, to power LNA
ut.biast(0, index=0) # turn off bias tee, to power off LNA


############################################################
# Plot

pDiff = pOn - pOff
factor = np.mean(pOn)/np.mean(pOff)
pDiffSmart = pOn -  factor * pOff

# Show the figure containing the plotted spectrum
fig=plt.figure(0)
ax=fig.add_subplot(111)
ax.semilogy(f, p, label=r'Fiducial')
ax.semilogy(fOn, pOn, label=r'On')
ax.semilogy(fOff, pOff, label=r'Off')
ax.semilogy(fOn, np.abs(pDiff), label=r'Diff')
ax.semilogy(fOn, np.abs(pDiffSmart), label=r'DiffSmart')
ax.legend(loc=1)
ax.set_xlabel(r'freq [Hz]')
ax.set_ylabel(r'P [V^2/Hz]')
fig.savefig('./figures/sandbox/spectrum_fswitch_'+str(integrationTime)+'sec.pdf', bbox_inches='tight')
#fig.show()
fig.clf()

