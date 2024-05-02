#import healpy as hp
#rot = hp.Rotator(coord=['G', 'C'])  # transform galactic to equatorial coordinates
#mapRADec = rot.rotate_map_pixel(mapGalactic) # rotate the map

import numpy as np
import matplotlib.pyplot as plt

import astropy.units as u
from astropy.coordinates import SkyCoord


pathOut = "./output/radec_target_lists/"

# Values of Galactic longitudes to observe
Lon = np.arange(-180., 180., 5.)
Lat = np.zeros_like(Lon)

# Galactic coordinates
galCoord = SkyCoord(l=Lon * u.degree, b = Lat * u.degree, frame='galactic', unit='degree')

# Convert to equatorial coordinates
equaCoord = galCoord.icrs

# save coordinates
data = np.column_stack((galCoord.l, galCoord.b, equaCoord.ra, equaCoord.dec))
data = np.round(np.array(data), 4)
header = "Galactic coordinates and corresponding Equatorial coordinates\n"
header += "longitude l [deg], latitude b [deg], RA [deg], Dec [deg]"
np.savetxt(pathOut+"lb_radec_list_1.txt", data, fmt='%1.4f', header=header)
