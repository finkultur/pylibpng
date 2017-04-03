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
    # Split 
    n = []
    for s in xrange(0, len(a), x):
        n.append(a[s:s+x])
    return n

def is_png(f):
    """ Checks that the first 8 bytes of the opened file is a valid PNG signature """
    return "0x89504e470d0a1a0a" == hex(unpack(f.read(8)))[:-1] # Cut the trailing 'L'

class PNG:
    def __init__(self, filename):
        self.dc_obj = zlib.decompressobj(-zlib.MAX_WBITS)
        self.IDAT = ""
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

    def get_iTXt(self, data):
        """ iTXt Chunk """
        # TODO: Uncompress compressed data
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
        # TODO: Check that data is at least "a few" bytes
        start = 0
        end = len(data)
        if len(self.IDAT) == 0:
            comp_method = unpack(data[0])
            check_bits = unpack(data[1])
            start = 2
        if last_IDAT:
            self.IDAT_check_value = unpack(data[-4:])
            end = -4
        self.IDAT += self.dc_obj.decompress(data[start:end])

        if last_IDAT:
            self.IDAT += self.dc_obj.flush()
            decomp_bytes = struct.unpack('!' + 'B'*len(self.IDAT), self.IDAT)
            self.pixels = self.defilter(decomp_bytes)

    def defilter(self, data):
        """ Defilter image data """
        if self.color_type == 2: pixel_size = 3
        elif self.color_type == 6: pixel_size = 4
        a = array_to_2d(list(data), self.width*pixel_size+1)

        for y in range(0, self.height):
            filter_type = a[y][0]
            a[y][0] = 0
            # if filter_type == 0: # NONE
            if filter_type == 1: # SUB
                for x in range(pixel_size, self.width*pixel_size+1):
                    a[y][x] = (a[y][x] + a[y][x-pixel_size]) % 256
            elif filter_type == 2: # UP
                for x in range(1, self.width*pixel_size+1):
                    a[y][x] = (a[y][x] + a[y-1][x]) % 256
            elif filter_type == 3: # AVERAGE
                for x in range(1, self.width*pixel_size+1):
                    recon_a = a[y][x-pixel_size]
                    recon_b = a[y-1][x] if y > 1 else 0
                    a[y][x] = (a[y][x] + math.floor((recon_a + recon_b) / 2)) % 256
            elif filter_type == 4: # PAETH
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
                for x in range(1, self.width*pixel_size+1):
                    recon_a = a[y][x-pixel_size] if x > pixel_size else 0
                    recon_b = a[y-1][x] if y > 1 else 0
                    recon_c = a[y-1][x-pixel_size] if x > pixel_size else 0
                    a[y][x] = (a[y][x] + paeth_predictor(recon_a, recon_b, recon_c)) % 256

        return self.init_pixels(a, pixel_size)

    def init_pixels(self, a, pixel_size):
        pixels = []
        for y in range(0, self.height):
            scanline = []
            for x in xrange(1, self.width*pixel_size+1, pixel_size):
                if pixel_size == 3:
                    scanline.append((a[y][x], a[y][x+1], a[y][x+2]))
                elif pixel_size == 4:
                    scanline.append((a[y][x], a[y][x+1], a[y][x+2], a[y][x+3]))
            pixels.append(scanline)
        return pixels

if __name__ == '__main__':
    infile = sys.argv[1]
    img = PNG(infile)

