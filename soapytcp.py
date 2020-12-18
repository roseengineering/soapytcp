#!/usr/bin/python3

import sys, argparse, select, socket, struct
import numpy as np
import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32

tuner_number = 5 # R820T
tuner_gains = 29 # R820T
dongle_info = struct.pack('>4sII', b'RTL0', tuner_number, tuner_gains)

command_fmt = ">BI"
command_size = struct.calcsize(command_fmt)

class Server:

    def __init__(self, **kw):
        self.insocks = []
        self.outsocks = []
        self.readbuf = {}
        self.clients = {}
        self.samples = 0
        self.max = 0
        self.tick = 0
        for key, value in kw.items():
            setattr(self, key, value)

    def peak_meter(self, data):
        self.max = max(self.max, abs(data.min()), abs(data.max()))
        self.samples += data.size / 2
        if self.samples > self.rate * self.refresh:
            n = 20 * np.log10(self.max + 1e-99)
            buf = "%6.1f\n" if self.dumb else "\33[2K%6.1f dBFS\r" 
            print(buf % n, end="", file=sys.stderr)
            self.samples = 0
            self.max = 0

    def open_conn(self, sock, client_address):
        print('new connection from %s:%s' % 
              client_address, file=sys.stderr)
        sock.setblocking(0)
        self.insocks.append(sock)
        self.outsocks.append(sock)
        self.readbuf[sock] = b''
        self.clients[sock] = client_address

    def close_conn(self, sock):
        print('closing connection from %s:%s' % 
              self.clients[sock], file=sys.stderr)
        self.outsocks.remove(sock)
        self.insocks.remove(sock)
        del self.readbuf[sock]
        del self.clients[sock]
        sock.close()

    def cleanup_conn(self):
        for sock in self.insocks:
            sock.close()

    def handle_conn(self, sdr, data):
        if not self.float:
            data = (data * 128 + 128).astype('B')

        readable, writable, exceptional = select.select(
            self.insocks, self.outsocks, self.outsocks, 0)

        for sock in self.outsocks:
            if sock in exceptional:
                self.close_conn(sock)

        for sock in self.outsocks:
            if sock in writable:
                try:
                    sock.sendall(data)
                except OSError:
                    self.close_conn(sock)

        for sock in self.insocks:
            if sock in readable:
                if sock is self.server:
                    conn, client_address = sock.accept()
                    self.open_conn(conn, client_address)
                    conn.sendall(dongle_info)
                else:
                    try:
                        n = len(self.readbuf[sock])
                        buf = sock.recv(command_size - n)
                    except OSError:
                        self.close_conn(sock)
                    self.readbuf[sock] += buf
                    if len(self.readbuf[sock]) == command_size:
                        self.handle_command(sdr, self.readbuf[sock])
                        self.readbuf[sock] = b''

    def status(self, sdr):
        self.rate = sdr.getSampleRate(SOAPY_SDR_RX, 0)
        self.freq = sdr.getFrequency(SOAPY_SDR_RX, 0)
        self.gain = sdr.getGain(SOAPY_SDR_RX, 0)
        print('frequency is %.3f MHz' % 
              (self.freq / 1e6), file=sys.stderr)
        print('sampling rate is %.3f MHz' % 
              (self.rate / 1e6), file=sys.stderr)
        print('gain is %s dB' % 
              self.gain, file=sys.stderr)

    def handle_command(self, sdr, data):
        command, param = struct.unpack(command_fmt, data)
        if self.freeze:
            print('frozen settings, ignoring command: 0x%02x: %s' % 
                  (command, param), file=sys.stderr)
        elif command == 0x01:
            if self.direct_samp:
                param = np.abs(param - 100e6)
            print('0x%02x set_center_freq: %s Hz' % 
                  (command, param), file=sys.stderr)
            sdr.setFrequency(SOAPY_SDR_RX, 0, param)
        elif command == 0x02:
            print('0x%02x set_sample_rate: %s Hz' % 
                  (command, param), file=sys.stderr)
            sdr.setSampleRate(SOAPY_SDR_RX, 0, param)
        elif command == 0x03:
            print('0x%02x set_gain_mode: %s (1 for manual)' % 
                  (command, param), file=sys.stderr)
            sdr.setGainMode(SOAPY_SDR_RX, 0, not param);
        elif command == 0x04:
            param = param / 10
            print('0x%02x set_gain: %s' % 
                  (command, param), file=sys.stderr)
            sdr.setGainMode(SOAPY_SDR_RX, 0, False);
            sdr.setGain(SOAPY_SDR_RX, 0, param);
        else:
            print('0x%02x unimplemented: %s' % 
                  (command, param), file=sys.stderr)

    def init_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(0)
        server_address = (self.host, self.port)
        server.bind(server_address)
        server.listen()
        print('listening on %s port %s' % server_address, file=sys.stderr)
        self.insocks.append(server)
        self.server = server

    def start(self):
        driver = self.driver
        if not driver:
            for res in SoapySDR.Device.enumerate(): 
                driver = res['driver']

        sdr = SoapySDR.Device(driver)
        stream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
        size = 1024
        data = np.array([0] * size * 2, np.float32)
        sdr.activateStream(stream) 

        if self.freq is not None: 
            sdr.setFrequency(SOAPY_SDR_RX, 0, self.freq)
        if self.rate is not None: 
            sdr.setSampleRate(SOAPY_SDR_RX, 0, self.rate)
        if self.gain is not None: 
            sdr.setGainMode(SOAPY_SDR_RX, 0, False);
            sdr.setGain(SOAPY_SDR_RX, 0, self.gain)
        if self.auto: 
            sdr.setGainMode(SOAPY_SDR_RX, 0, True);

        if self.direct_samp:
            param = self.direct_samp
            if param.lower() == "i": param = "1"
            if param.lower() == "q": param = "2"
            sdr.writeSetting("direct_samp", param)
        if self.iq_swap:
            sdr.writeSetting("iq_swap", "true")
        if self.biastee:
            sdr.writeSetting("biastee", "true")
        if self.digital_agc:
            sdr.writeSetting("digital_agc", "true")
        if self.digital_agc:
            sdr.writeSetting("offset_tune", "true")

        self.status(sdr)
        if not self.noserver: 
            self.init_server()

        mode = "ab" if self.append else "wb"
        outfile = open(self.out, "wb") if self.out else None

        try:
            while True:
                sr = sdr.readStream(stream, [data], size)
                self.tick += 1
                if self.stdout: 
                    sys.stdout.buffer.write(data)
                if outfile: 
                    outfile.write(data)
                if not self.nometer: 
                    self.peak_meter(data)
                if not self.noserver and self.tick % (self.skip + 1) == 0: 
                    self.handle_conn(sdr, data)
        except KeyboardInterrupt:
            pass

        if outfile: 
            outfile.close()
        if not self.noserver: 
            self.cleanup_conn()

        sdr.deactivateStream(stream) 
        sdr.closeStream(stream)


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--out", 
                        help="write cf32 samples to output file")
    parser.add_argument("--driver", 
                        help="driver name")
    parser.add_argument("--host", default="127.0.0.1",
                        help="server host address")
    parser.add_argument("--port", type=int, default=1234,
                        help="server port address")
    parser.add_argument("--stdout", action="store_true",
                        help="write cf32 samples to standard output")
    parser.add_argument("--freq", type=float,
                        help="set center frequency (Hz)")
    parser.add_argument("--rate", type=float,
                        help="set sample rate (Hz)")
    parser.add_argument("--gain", type=float,
                        help="set gain (dB)")
    parser.add_argument("--auto", action="store_true",
                        help="turn on automatic gain")
    parser.add_argument("--skip", type=int, default=0,
                        help="Number of blocks to skip sending over TCP")
    parser.add_argument("--refresh", type=float, default=.5,
                        help="peak meter refresh interval (seconds)")
    parser.add_argument("--float", action="store_true",
                        help="RTLTCP server sends 32-bit complex samples")
    parser.add_argument("--noserver", action="store_true",
                        help="disable RTLTCP server")
    parser.add_argument("--nometer", action="store_true",
                        help="disable peak meter")
    parser.add_argument("--freeze", action="store_true",
                        help="freeze settings")
    parser.add_argument("--dumb", action="store_true",
                        help="assume running on a dumb terminal")
    parser.add_argument("--append", action="store_true",
                        help="append samples to output file")

    parser.add_argument("--direct-samp", help="1 or i=I, 2 or q=Q channel")
    parser.add_argument("--iq-swap", action="store_true", help="swap IQ signals")
    parser.add_argument("--biastee", action="store_true", help="enable bias tee")
    parser.add_argument("--digital-agc", action="store_true", help="enable digital AGC")
    parser.add_argument("--offset-tune", action="store_true", help="enable offset tune")

    args = parser.parse_args()
    server = Server(**vars(args))
    server.start()


if __name__ == "__main__":
    main()

