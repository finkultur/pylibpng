#!/usr/bin/python

import sys
import struct
import datetime
import binascii

def get_bytes(f, num):
    """ Get num bytes from the opened myfile """
    if num == 1: return struct.unpack('!B', f.read(1))[0]
    if num == 2: return struct.unpack('!H', f.read(2))[0]
    if num == 4: return struct.unpack('!I', f.read(4))[0]
    if num == 8: return struct.unpack('!Q', f.read(8))[0]
    else: return -1

def unpack(s):
    """ Unpack bytes from string s """
    if len(s) == 1: return struct.unpack('!B', s)[0]
    if len(s) == 2: return struct.unpack('!H', s)[0]
    if len(s) == 4: return struct.unpack('!I', s)[0]
    if len(s) == 8: return struct.unpack('!Q', s)[0]
    else: return -1

def is_png(f):
    """ Checks that the first 8 bytes of the opened file is a valid PNG signature """
    return "0x89504e470d0a1a0a" == hex(get_bytes(f, 8))[:-1] # Cut the trailing 'L'

class PNG:
    def __init__(self, filename):
        with open(filename, 'rb') as f:
            if not is_png(f):
                print("File is not a PNG")
                return
            self.get_chunk(f, 8)

    def get_chunk(self, f, ptr):
        f.seek(ptr) # File pointer is probably already here (?)
        size = get_bytes(f, 4)
        chunk_id = f.read(4)
        chunk_data = f.read(size)

        # Check CRC
        crc = unpack(f.read(4))
        calc_crc = binascii.crc32(chunk_id + chunk_data) & 0xffffffff
        if (crc != calc_crc):
            print("CRC mismatch, file corrupted")
            return

        print("Chunk ID: %s, size: %i" % (chunk_id, size))

        # Process current chunk
        if chunk_id == "IHDR": self.get_IHDR(chunk_data)
        elif chunk_id == "pHYs": self.get_pHYs(chunk_data)
        elif chunk_id == "tIME": self.get_tIME(chunk_data)
        elif chunk_id == "iTXt": self.get_iTXt(chunk_data)
        elif chunk_id == "IDAT": self.get_IDAT(chunk_data)
        elif chunk_id == "IEND":
            return

        # TODO: check for other type of chunks like PLTE, sRGB, gAMA, zTXT, tRNS

        # Process next chunk
        next_chunk = ptr + 4 + 4 + size + 4 # sizeof{size, type, data, crc}
        self.get_chunk(f, next_chunk)

    def check_crc():
        pass

    def get_IHDR(self, data):
        """ IHDR Header """
        self.width = unpack(data[0:4])
        self.height = unpack(data[4:8])
        self.bit_depth = unpack(data[8])
        self.color_type = unpack(data[9])
        self.comp_method = unpack(data[10])
        self.filter_method = unpack(data[11])
        self.interlace_method = unpack(data[12])
        #print("""width: %i, height: %i, bit_depth: %i, color_type: %i, comp_method: %i,
        #         filter_method: %i, interlace_method: %i""" % (self.width, self.height, self.bit_depth,
        #       self.color_type, self.comp_method, self.filter_method, self.interlace_method))

    def get_pHYs(self, data):
        """ pHYs Header """
        pass # Not that important

    def get_tIME(self, data):
        """ tIME Header. Timestamp in UTC """
        year = unpack(data[0:2]) # 0-9999
        month = unpack(data[2]) # 1-12
        day = unpack(data[3]) # 1-31
        hour = unpack(data[4]) # 0-23
        minute = unpack(data[5]) # 0-59
        second = unpack(data[6]) # 0-60
        self.timestamp = datetime.datetime(year, month, day, hour, minute, second)
        #print("Timestamp: " + str(self.timestamp))

    def get_iTXt(self, data):
        """ iTXt Header """
        def get_until_null(s, start=0):
            end = s.find('\0')
            return end+1, s[start:end]
        pos, self.kw = get_until_null(data)
        comp_flag = unpack(data[pos]); pos += 1
        comp_method = unpack(data[pos]); pos += 1
        pos, lang_tag = get_until_null(data, pos)
        pos, translated_kw = get_until_null(data, pos)
        self.text = data[pos:]

    def get_IDAT(self, data):
        pass

if __name__ == '__main__':
    infile = sys.argv[1]
    img = PNG(infile)

