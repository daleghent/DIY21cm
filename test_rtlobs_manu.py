
# If running outside of the rtlobs github repo,
# add path
import sys
sys.path.append('/home/stellarmate/rtlobs')

from rtlobs import collect as col
from rtlobs import post_process as post
from rtlobs import utils as ut


ut.biast(1, index=0) # turn on bias tee, to power LNA
#ut.biast(0, index=0) # turn off bias tee, to power LNA


nSample = 8192 # samples per call to the SDR
nBin =  2048   # bin resolution power spectrum 
gain = 49.6 # [dB] of RtlSdr gain
bandwidth = 2.32e6  # [Hz] sample rate/bandwidth
centerFrequency = 1.420e9 # [GHz] center frequency
integrationTime = 3  #20  # [sec] integration time
f, p = col.run_spectrum_int(nSample, nBin, gain, bandwidth, centerFrequency, integrationTime)

# print the power spectrum
#print(f)
#print(p)

# Show the figure containing the plotted spectrum
fig, ax = post.plot_spectrum(f, p, savefig='./figures/spectrum_'+str(integrationTime)+'sec.pdf')
#fig.show()
fig.clf()
