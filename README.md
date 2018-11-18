# soapytcp

A SDR receiver written in Python using the Soapy API. Writes the cf32 stream to a file or stdout or to a TCP socket using the RTLTCP protocol.

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



