import healpy as hp

rot = hp.Rotator(coord=['G', 'C'])  # transform galactic to equatorial coordinates

mapRADec = rot.rotate_map_pixel(mapGalactic) # rotate the map
