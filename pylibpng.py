#!/usr/bin/python

import sys
import struct
import datetime
import binascii
import zlib

def unpack(s):
    """ Unpack bytes from string s """
    if len(s) == 1: return struct.unpack('!B', s)[0]
    if len(s) == 2: return struct.unpack('!H', s)[0]
    if len(s) == 4: return struct.unpack('!I', s)[0]
    if len(s) == 8: return struct.unpack('!Q', s)[0]
    else: return -1

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

        # This may probably be solved with a pretty sweet list comprehension but im hungover
        self.pixels = []
        i = 0
        for y in range(0, self.height):
            scanline = []
            i = i + 1
            for x in range(0, self.width):
                scanline.append((decomp_bytes[i], decomp_bytes[i+1], decomp_bytes[i+2]))
                i = i + 3
            self.pixels.append(scanline)

        #print("IDAT: decompressed bytes: " + str(decomp_bytes))

    def defilter(self, scanline):
        pass

if __name__ == '__main__':
    infile = sys.argv[1]
    img = PNG(infile)
    print(img.pixels)

