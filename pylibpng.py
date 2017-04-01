#!/usr/bin/python

import sys
import struct
import datetime
import binascii
import zlib
import math

def unpack(s):
    """ Unpack bytes from string s """
    if len(s) == 1: return struct.unpack('!B', s)[0]
    if len(s) == 2: return struct.unpack('!H', s)[0]
    if len(s) == 4: return struct.unpack('!I', s)[0]
    if len(s) == 8: return struct.unpack('!Q', s)[0]
    else: return -1

def array_to_2d(a, x):
    n = []
    for s in xrange(0, len(a), x):
        n.append(a[s:s+x])
    return n

def is_png(f):
    """ Checks that the first 8 bytes of the opened file is a valid PNG signature """
    return "0x89504e470d0a1a0a" == hex(unpack(f.read(8)))[:-1] # Cut the trailing 'L'

class PNG:
    def __init__(self, filename):
        self.IDATS = []
        with open(filename, 'rb') as f:
            if not is_png(f):
                print("File is not a PNG")
                return
            self.get_chunk(f)

    def get_chunk(self, f):
        size = unpack(f.read(4))
        chunk_id = f.read(4)
        chunk_data = f.read(size)
        crc = unpack(f.read(4))
        self.check_crc(chunk_id, chunk_data, crc)
        print("Chunk ID: %s, size: %i" % (chunk_id, size))

        # Process current chunk
        if chunk_id == "IHDR": self.get_IHDR(chunk_data)
        elif chunk_id == "pHYs": self.get_pHYs(chunk_data)
        elif chunk_id == "tIME": self.get_tIME(chunk_data)
        elif chunk_id == "iTXt": self.get_iTXt(chunk_data)
        elif chunk_id == "IDAT":
            f.seek(f.tell()+4) # Skip size of next chunk
            next_chunk_id = f.read(4)
            self.get_IDAT(chunk_data, next_chunk_id != 'IDAT')
            f.seek(f.tell()-8)
        elif chunk_id == "IEND":
            return

        # TODO: check for other type of chunks like PLTE, sRGB, gAMA, zTXT, tRNS

        # Process next chunk
        self.get_chunk(f)

    def check_crc(self, chunk_id, chunk_data, crc):
        calc_crc = binascii.crc32(chunk_id + chunk_data) & 0xffffffff
        if (crc != calc_crc):
            print("CRC mismatch, file corrupted")
            return

    def get_IHDR(self, data):
        """ IHDR Chunk """
        self.width = unpack(data[0:4])
        self.height = unpack(data[4:8])
        self.bit_depth = unpack(data[8])
        self.color_type = unpack(data[9])
        self.comp_method = unpack(data[10])
        self.filter_method = unpack(data[11])
        self.interlace_method = unpack(data[12])
        print("""width: %i, height: %i, bit_depth: %i, color_type: %i, comp_method: %i,
                 filter_method: %i, interlace_method: %i""" % (self.width, self.height, self.bit_depth,
               self.color_type, self.comp_method, self.filter_method, self.interlace_method))

    def get_pHYs(self, data):
        """ pHYs Chunk """
        pass # Not that important

    def get_tIME(self, data):
        """ tIME Chunk. Timestamp in UTC """
        year, month, day, hour, minute, second = struct.unpack('!hBBBBB', data)
        self.timestamp = datetime.datetime(year, month, day, hour, minute, second)
        #print("Timestamp: " + str(self.timestamp))

    def get_iTXt(self, data):
        """ iTXt Chunk """
        def get_until_null(s, start=0):
            end = s.find('\0')
            return end+1, s[start:end]
        pos, self.kw = get_until_null(data)
        comp_flag = unpack(data[pos]); pos += 1
        comp_method = unpack(data[pos]); pos += 1
        pos, lang_tag = get_until_null(data, pos)
        pos, translated_kw = get_until_null(data, pos)
        self.text = data[pos:]

    def get_IDAT(self, data, last_IDAT):
        """ IDAT Chunk """
        # TODO: Check check_value
        comp_method = unpack(data[0])
        check_bits = unpack(data[1])
        comp_data = data[2:-4]
        check_value = unpack(data[-4:])
        self.IDATS.append((comp_method, check_bits, comp_data, check_value))

        if last_IDAT:
           self.process_IDATs()
        #print("IDAT: comp_method: %i, check_bits: %i, check_value: %s" %
        #      (comp_method, check_bits, hex(check_value)))
        #print("IDAT: comp_data: " + str(comp_bytes))

    def process_IDATs(self):
        comp_data = ""
        for idat in self.IDATS:
            comp_data += idat[2]

        decomp_data = zlib.decompress(comp_data, -zlib.MAX_WBITS)
        decomp_bytes = struct.unpack('!' + 'B'*len(decomp_data), decomp_data)
        self.pixels = self.defilter(decomp_bytes)

    def defilter(self, data):
        """
        x   the byte being filtered;
        a   the byte corresponding to x in the pixel immediately before the pixel containing x (or the byte
            immediately before x, when the bit depth is less than 8);
        b   the byte corresponding to x in the previous scanline;
        c   the byte corresponding to b in the pixel immediately before the pixel containing b (or the byte
            immediately before b, when the bit depth is less than 8).
        """
        a = array_to_2d(list(data), self.width*3+1) # filter type + 3 bytes per pixel

        for y in range(0, self.height):
            filter_type = a[y][0]
            a[y][0] = 0

            # if filter_type == 0: Recon(x) = Filt(x)
            if filter_type == 1:
                for x in range(3, self.width*3+1):
                    # Recon(x) = Filt(x) + Recon(a)
                    a[y][x] = (a[y][x] + a[y][x-3]) % 256
            elif filter_type == 2:
                for x in range(1, self.width*3+1):
                    # Recon(x) = Filt(x) + Recon(b)
                    a[y][x] = (a[y][x] + a[y-1][x]) % 256
            elif filter_type == 3:
                # TODO: Have not found a file that uses this filter type
                for x in range(1, self.width*3+1):
                    # Recon(x) = Filt(x) + floor((Recon(a) + Recon(b)) / 2)
                    a[y][x] = (a[y][x] + math.floor((a[y][x-3] + a[y-1][x]) / 2)) % 256
            elif filter_type == 4:
                def paeth_predictor(a, b, c):
                    p = a + b - c
                    pa = abs(p - a)
                    pb = abs(p - b)
                    pc = abs(p - c)
                    if pa <= pb and pa <= pc:
                        pr = a
                    elif pb <= pc:
                        pr = b
                    else:
                         pr = c
                    return pr

                for x in range(1, self.width*3+1):
                    # Recon(x) = Filt(x) + PaethPredictor(Recon(a), Recon(b), Recon(c))
                    if x > 3:
                        a[y][x] = (a[y][x] + paeth_predictor(a[y][x-3], a[y-1][x], a[y-1][x-3])) % 256
                    else:
                        a[y][x] = (a[y][x] + paeth_predictor(0, a[y-1][x], 0)) % 256

        pixels = []
        for y in range(0, self.height):
            scanline = []
            for x in xrange(1, self.width*3+1, 3):
                scanline.append((a[y][x], a[y][x+1], a[y][x+2]))
            pixels.append(scanline)

        return pixels

if __name__ == '__main__':
    infile = sys.argv[1]
    img = PNG(infile)

