#!/usr/bin/python

import sys
import struct
import datetime
import zlib
import math
from itertools import chain

adam7 = ((0,8,0,8),
         (4,8,0,8),
         (0,4,4,8),
         (2,4,0,4),
         (0,2,2,4),
         (1,2,0,2),
         (0,1,1,2))


def unpack(s):
    """ Unpack bytes from string s """
    if len(s) == 1: return struct.unpack('!B', s)[0]
    if len(s) == 2: return struct.unpack('!H', s)[0]
    if len(s) == 4: return struct.unpack('!I', s)[0]
    if len(s) == 8: return struct.unpack('!Q', s)[0]
    else: return -1

def get_until_null(s, start=0):
    end = s.find('\0')
    return end+1, s[start:end]

class PNG(object):
    def __init__(self, filename):
        self.dc_obj = zlib.decompressobj(-zlib.MAX_WBITS)
        self.width = 0
        self.height = 0
        self.pixels = []
        self.idat = ""
        self.chrm = None
        self.color_type = -1
        self.bit_depth = -1
        self.timestamp = None
        self.bkgd = None
        with open(filename, 'rb') as f:
            if not PNG.is_png(f):
                print("File is not a PNG")
                return
            self.get_chunk(f)

    @staticmethod
    def is_png(f):
        """ Checks that the first 8 bytes of the opened file is a valid PNG signature """
        return hex(unpack(f.read(8)))[:-1] == "0x89504e470d0a1a0a" # Cut the trailing 'L'

    @staticmethod
    def check_crc(chunk_id, chunk_data, crc):
        """ Check that crc(chunk_id+chunk_data) == crc """
        calc_crc = zlib.crc32(chunk_id + chunk_data) & 0xffffffff
        if (crc != calc_crc):
            print("CRC mismatch, file corrupted")
            return

    def get_chunk(self, f):
        size = unpack(f.read(4))
        chunk_id = f.read(4)
        chunk_data = f.read(size)
        print("Chunk ID: %s, size: %i" % (chunk_id, size))
        crc = unpack(f.read(4))
        PNG.check_crc(chunk_id, chunk_data, crc)

        # Process current chunk
        if chunk_id == "IHDR": self.get_ihdr(chunk_data)
        elif chunk_id == "tIME": self.get_time(chunk_data)
        elif chunk_id == "iTXt": self.get_itxt(chunk_data)
        elif chunk_id == "zTXt": self.get_ztxt(chunk_data)
        elif chunk_id == "cHRM": pass
        elif chunk_id == "gAMA": self.get_gama(chunk_data)
        elif chunk_id == "sBIT": pass
        elif chunk_id == "PLTE": pass
        elif chunk_id == "bKGD": self.get_bkgd(chunk_data)
        elif chunk_id == "hIST": pass
        elif chunk_id == "tRNS": pass
        elif chunk_id == "pHYs": self.get_phys(chunk_data)
        elif chunk_id == "IDAT":
            f.seek(f.tell()+4) # Skip size of next chunk
            next_chunk_id = f.read(4)
            self.get_idat(chunk_data, next_chunk_id != 'IDAT')
            f.seek(f.tell()-8) # Return file ptr
        elif chunk_id == "IEND":
            if self.interlace_method == 0:
                df_data = self.defilter(self.idat, self.width, self.height, self.pixel_size)
                self.pixels = PNG.init_pixels(df_data, self.width, self.height, 0)
            elif self.interlace_method == 1:
                passes = PNG.deinterlace(self.idat, self.width, self.height, self.pixel_size)
                self.pixels = PNG.init_pixels(passes, self.width, self.height, 1)
            return

        # Process next chunk
        self.get_chunk(f)

    def get_ihdr(self, data):
        """ IHDR Chunk """
        self.width = unpack(data[0:4])
        self.height = unpack(data[4:8])
        self.bit_depth = unpack(data[8])
        self.color_type = unpack(data[9])
        self.comp_method = unpack(data[10])
        self.filter_method = unpack(data[11])
        self.interlace_method = unpack(data[12])

        if self.color_type == 2:
            self.pixel_size = 3
        elif self.color_type == 6:
            self.pixel_size = 4
        print("""width: %i, height: %i, bit_depth: %i, color_type: %i, comp_method: %i,
                 filter_method: %i, interlace_method: %i""" %
              (self.width, self.height, self.bit_depth, self.color_type, self.comp_method,
               self.filter_method, self.interlace_method))

    def get_time(self, data):
        """ tIME Chunk. Timestamp in UTC """
        if len(data) == 7:
            year, month, day, hour, minute, second = struct.unpack('!hBBBBB', data)
            self.timestamp = datetime.datetime(year, month, day, hour, minute, second)

    def get_itxt(self, data):
        """ iTXt Chunk """
        # TODO: Uncompress compressed data
        pos, self.kw = get_until_null(data)
        comp_flag = unpack(data[pos]); pos += 1
        comp_method = unpack(data[pos]); pos += 1
        pos, lang_tag = get_until_null(data, pos)
        pos, translated_kw = get_until_null(data, pos)
        self.text = data[pos:]

    def get_ztxt(self, data):
        pass

    def get_chrm(self, data):
        if len(data) == 32:
            self.chrm.white = (unpack(data[0:4]) / 100000, unpack(data[4:8]) / 100000)
            self.chrm.red = (unpack(data[8:12]) / 100000, unpack(data[12:16]) / 100000)
            self.chrm.green = (unpack(data[16:20]) / 100000, unpack(data[20:24]) / 100000)
            self.chrm.blue = (unpack(data[24:28]) / 100000, unpack(data[28:32]) / 100000)

    def get_gama(self, data):
        if len(data) == 4:
            self.gamma = unpack(data) / 100000

    def get_sbit(self, data):
        pass

    def get_plte(self, data):
        pass

    def get_bkgd(self, data):
        if self.color_type == 0 or self.color_type == 4:
            self.bkgd = unpack(data[0:2])
        elif self.color_type == 2 or self.color_type == 6:
            self.bkgd = (unpack(data[0:2]), unpack(data[2:4]), unpack(data[4:6]))

    def get_hist(self, data):
        pass

    def get_trns(self, data):
        pass

    def get_phys(self, data):
        """ pHYs Chunk """
        pass

    def get_idat(self, data, last):
        """ IDAT Chunk """
        # TODO: Check that data is at least "a few" bytes
        start = 0
        end = len(data)
        if len(self.idat) == 0:
            comp_method = unpack(data[0])
            check_bits = unpack(data[1])
            start = 2
        if last:
            idat_adler = unpack(data[-4:])
            end = -4
        self.idat += self.dc_obj.decompress(data[start:end])

        if last:
            self.idat += self.dc_obj.flush()
            if (zlib.adler32(self.idat) & 0xffffffff) != idat_adler:
                print("IDAT Adler calculation mismatch")
            self.idat = list(struct.unpack('!' + 'B'*len(self.idat), self.idat))

    @staticmethod
    def defilter(data, width, height, pixel_size):
        """ Defilter image data """
        row_size = width * pixel_size + 1
        a = [data[i:i+row_size] for i in range(0, len(data), row_size)]
        a[0] = PNG.defilter_scanline(a[0], [0]*row_size, pixel_size)
        for y in range(1, height):
            a[y] = PNG.defilter_scanline(a[y], a[y-1], pixel_size)

        # Return a flat list with pixel-tuples (w/o filter bytes)
        return zip(*[iter( sum([d[1:] for d in a ],[]) )] * pixel_size)

    @staticmethod
    def defilter_scanline(scanline, prev, pixel_size):
        """ Defilter a single scanline """
        filter_type = scanline[0]

        if filter_type == 0: # NONE
            return scanline
        elif filter_type == 1: # SUB
            for x in range(pixel_size, len(scanline)):
                scanline[x] = (scanline[x] + scanline[x-pixel_size]) % 256
        elif filter_type == 2: # UP
            for x in range(1, len(scanline)):
                scanline[x] = (scanline[x] + prev[x]) % 256
        elif filter_type == 3: # AVERAGE
            for x in range(1, len(scanline)):
                recon_a = scanline[x-pixel_size] if x > pixel_size else 0
                recon_b = prev[x]
                scanline[x] = (scanline[x] + math.floor((recon_a + recon_b) / 2)) % 256
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
            for x in range(1, len(scanline)):
                recon_a = scanline[x-pixel_size] if x > pixel_size else 0
                recon_b = prev[x]
                recon_c = prev[x-pixel_size] if x > pixel_size else 0
                scanline[x] = (scanline[x] + paeth_predictor(recon_a, recon_b, recon_c)) % 256
        return scanline

    @staticmethod
    def init_pixels(data, width, height, interlace_method):
        """ Initialize pixels
            For non-interlaced images, data is just a flat list of pixel-tuples.
            For interlaced images, data is a list of list of pixel-tuples, one for each pass.
        """
        pixels = [[None for i in range(width)] for j in range(height)]
        if interlace_method == 0:
            i = 0
            for y in range(0, height):
                for x in range(0, width):
                    pixels[y][x] = data[i]
                    i += 1
        elif interlace_method == 1:
            # Combine all 7 passes to single image
            for p, (x0, xstep, y0, ystep) in enumerate(adam7):
                indices = [(x, y) for y in xrange(y0, height, ystep) for x in xrange(x0, width, xstep)]
                for i in range(0, len(indices)):
                    x, y = indices[i]
                    pixels[y][x] = data[p][i]
        return pixels

    @staticmethod
    def deinterlace(data, width, height, pixel_size):
        """ Deinterlace image data.
            Returns a list of list of pixel-tuples, one for each of the 7 passes.
         """
        passes = []
        ptr = 0
        for x0, xstep, y0, ystep in adam7:
            x_size = int(math.ceil(float(width-x0)/xstep))
            y_size = int(math.ceil(float(height-y0)/ystep))
            row_size = x_size * pixel_size + 1
            uf_d = data[ptr:ptr + row_size * y_size]
            ptr += row_size * y_size
            f_d = PNG.defilter(uf_d, x_size, y_size, pixel_size)
            # Creates a list of pixel-tuples (w/o filter bytes) from a list of scanlines (w/ f-bytes)
            #f_d_wo_fb = zip(*[iter( sum([d[1:] for d in f_d ],[]) )] * pixel_size)
            passes.append(f_d)
        return passes


if __name__ == '__main__':
    infile = sys.argv[1]
    img = PNG(infile)

