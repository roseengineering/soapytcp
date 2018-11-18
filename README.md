# soapytcp

A SDR receiver written in Python 3 using the Soapy API. Writes the cf32 stream to a file or stdout or to a TCP socket using the RTLTCP protocol.

```
usage: soapytcp [-h] [--out OUT] [--driver DRIVER] [--host HOST] [--port PORT]
                [--stdout] [--freq FREQ] [--rate RATE] [--gain GAIN] [--auto]
                [--noserver] [--nopeak] [--freeze]


optional arguments:
  -h, --help       show this help message and exit
  --out OUT        write cf32 samples to output file
  --driver DRIVER  driver name
  --host HOST      server host address
  --port PORT      server port address
  --stdout         write cf32 samples to standard output
  --freq FREQ      set center frequency (Hz)
  --rate RATE      set sample rate (Hz)
  --gain GAIN      set gain (dB)
  --auto           turn on automatic gain
  --noserver       disable RTLTCP server
  --nopeak         disable peak meter
  --freeze         freeze settings
```

First install the Soapy API from https://github.com/pothosware/SoapySDR/wiki.  It installs
the python library automatically.

I install Soapy from source on Debian using the following commands:

```
sudo apt-get install libusb-dev cmake swig python3-dev
git clone https://github.com/pothosware/SoapySDR.git
cd SoapySDR/
mkdir build
cd build
cmake -DPYTHON3_INSTALL_DIR=/usr/local/lib/python3.5/dist-packages ..
make
sudo make install
sudo ldconfig
SoapySDRUtil --info
SoapySDRUtil --probe     
```

Also numpy must be installed.

```
sudo pip3 install numpy
```

If the --driver option is not given the receiver will pick the first 
Soapy device it finds and defaults the driver name to it.

By default a RTLTCP server is started.  A RTLSDR device is not a prerequisite
to run the server.  Soapytcp will stream any Soapy supported device.  The
server was tested with HDSDR and the ExtIO\_RTL\_TCP.dll from 
https://github.com/hayguen/extio_rtl_tcp/releases/ 
(as well as with my ExtIO\_RTLTCP.dll from https://github.com/roseengineering/ExtIO_RTLTCP).

To disable the RTLTCP server use the --noserver option.

Also by default a level meter is displayed measured in dBFS (0 dB is full scale).  This
can be disabled with --nopeak.

The --freeze option prevents the ExtIO from changing the frequency, sampling rate, and
gain settings of the device.  Note, since multiple users can connect to the server and change
settings, using freeze can prevent conflicts.

## with openwebrx

For example with openwebrx, to use soapytcp as the receiver I set the following
in config\_webrx.py then run "python openwebrx.py".

```
format_conversion=""
start_rtl_command="soapytcp --stdout --noserver --freq {center_freq} --rate {samp_rate}".format(
    rf_gain=rf_gain, center_freq=center_freq, samp_rate=samp_rate)
```

## as a rtlsdr server and to a file

$ soapytcp --freq 99e6 --rate 2.048e3 --gain 30 --out stream.cf32

# why?

Basically I created soapytcp so that SDR receivers can be shared over a network - LAN party
style.  My osmotcp receiver was also created for this purpose, but it relies on having
GNURadio installed which is complex to install.  Soapy is much easier to install.
The RTLTCP protcol uses about 40 megabits per second, which barely fits over
a 100 Mb LAN, however it is streamable over a 1Gb LAN.  And while the RTLTCP protocol 
only uses 8 bits per sample it can be used to monitor and change the frequency and gain of
a live stream.  The file output feature of soapytcp will let you save the full cf32 stream 
to a file for later review.







