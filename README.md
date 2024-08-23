Module to turn a RTL-SDR software-defined radio into a 21cm receiver,
and observe the neutral hydrogen signal from the Milky Way!
Not only can you detect the Milky Way signal, but you can identify the various spiral arms,
and measure the rotation profile via the Doppler effect.

## Installing the dependencies on Kubuntu:

### rtl-sdr package

I did not use the standard
```
sudo apt install rtl-sdr
```
though it might have worked. 
I read that I needed to compile from source with some specific compile options, to enable the "detached kernel driver".
So I followed the instructions scattered at the top and bottom of this page:
https://m3php.com/2012/10/10/remote-sdr-using-raspberry-pi-rtl_tcp/
and on this forum:
https://forums.raspberrypi.com/viewtopic.php?t=81731 .
Specifically, I ran:
```
sudo apt install pkg-config, libusb-1.0-0
sudo apt install cmake
sudo apt install git
git clone git://git.osmocom.org/rtl-sdr.git
cd rtl-sdr/
mkdir build
cd build
cmake ../ -DINSTALL_UDEV_RULES=ON -DDETACH_KERNEL_DRIVER=ON
make
sudo make install
sudo ldconfig
```
Then the commands
```
rtl_test
rtl_power
```
both worked.

However, when using python, through rtlobs, which calls pyrtlsdr,
I get an error about kernel driver already claiming the device.
This was fixed by blacklisting the kernel driver:
```
cd /etc/modprobe.d/
sudo gedit ban-rtl.conf
and add the following to the file:
blacklist dvb_usb_rtl28xxu
reboot
```

If debugging is needed, try
```
rtl_test
rtl_power
```

The LNA needs to be powered via bias T on the RTL SDR.
To activate the bias T:
```
rtl_biast -b 1
```
To deactivate it:
```
rtl_biast -b 0
```

### pyrtlsdr python package

```
pip install pyrtlsdr[lib]
```
(got a warning that this version of pyrtlsdr does not provide [lib])

### rtlobs python package

This github repo is perfect for this:
https://github.com/evanmayer/rtlobs .
I forked it to tweak it,
and cloned it from my github:
https://github.com/EmmanuelSchaan/rtlobs.git .
I haven't installed it: I just give its path to my python codes that use it...
