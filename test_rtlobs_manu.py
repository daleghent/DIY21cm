import numpy as np

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


############################################################
# The LNA needs to be powered, to amplify around 1.42GHz

ut.biast(1, index=0) # turn on bias tee, to power LNA
#ut.biast(0, index=0) # turn off bias tee, to power off LNA


############################################################
# Measure power spectrum around 21cm frequency
'''
nSample = 8192 # samples per call to the SDR
nBin =  2048   # bin resolution power spectrum 
gain = 49.6 # [dB] of RtlSdr gain
bandwidth = 2.32e6  # [Hz] sample rate/bandwidth
centerFrequency = nu21cm # [Hz] center frequency
integrationTime = 3  #20  # [sec] integration time
# get f [Hz], p [dB/Hz]
f, p = col.run_spectrum_int(nSample, 
                            nBin, 
                            gain, 
                            bandwidth, 
                            centerFrequency, 
                            integrationTime)

# print the power spectrum
#print(f)
#print(p)

# Show the figure containing the plotted spectrum
fig, ax = post.plot_spectrum(f, p, savefig='./figures/sandbox/spectrum_'+str(integrationTime)+'sec.pdf')
#fig.show()
fig.clf()
'''

############################################################
# Measure power spectrum with frequency switching

# This produces the "folded" spectrum, ie where both 
# the fiducial spectrum and the shifted one have been combined/subtracted
nSample = 8192 # samples per call to the SDR
#nSample = 2**18 # samples per call to the SDR
nBin =  2048   # bin resolution power spectrum 
gain = 49.6 # [dB] of RtlSdr gain
#bandwidth = 2.32e6  # [Hz] sample rate/bandwidth
bandwidth = 3.2e6  # [Hz] sample rate/bandwidth. Try to max it out, limited by the hardware
centerFrequency = nu21cm # [Hz] center frequency
#throwFrequency = nu21cm + 1.e6 # [Hz] alternate frequency. The freq diff has to be less than achieved bandwidth
throwFrequency = nu21cm + 1.5e6 # [Hz] alternate frequency. The freq diff has to be less than achieved bandwidth
# Too bad, I would like a shift of 3.e6 Hz for my 21cm line...
alternatingFrequency = 1.   # [Hz] frequency at which we switch between fiducial and shifted freqs
integrationTime = 10 # [sec] integration time
# this time, the integration time is split between the fiducial and shifted freqs,
# so the integration time on the fiducial freq is half of this number.
# get f [Hz], p [V^2/Hz]
f, p = col.run_fswitch_int(nSample, 
                           nBin, 
                           gain, 
                           bandwidth, 
                           centerFrequency, 
                           throwFrequency, 
                           integrationTime, 
                           fswitch=alternatingFrequency)

# this command for freq switching seems to work, but is not the parameters I want...
#f, p = col.run_fswitch_int(262144, 2048, 49.6, 2.048e6, 399.75e6, 400.25e6, 30., fswitch=1)
#f, p = col.run_fswitch_int(nSample, nBin, gain, bandwidth, centerFrequency, throwFrequency, integrationTime, fswitch=1)

print(np.max(np.abs(p)))
print(p)

# convert p to [dB/Hz]
p = 10. * np.log10(np.abs(p))

# Show the figure containing the plotted spectrum
fig, ax = post.plot_spectrum(f, p, savefig='./figures/sandbox/spectrum_fswitch_'+str(integrationTime)+'sec.pdf')
#fig.show()
fig.clf()


############################################################
# The LNA needs to be powered, to amplify around 1.42GHz

#ut.biast(1, index=0) # turn on bias tee, to power LNA
ut.biast(0, index=0) # turn off bias tee, to power off LNA

