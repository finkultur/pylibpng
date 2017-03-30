#!/usr/bin/python

import sys
import struct
import datetime

def get_bytes(f, num):
    """ Get num bytes from the opened myfile """
    if num == 1: return struct.unpack('!B', f.read(1))[0]
    if num == 2: return struct.unpack('!H', f.read(2))[0]
    if num == 4: return struct.unpack('!I', f.read(4))[0]
    if num == 8: return struct.unpack('!Q', f.read(8))[0]
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
        next_chunk = ptr + 4 + 4 + size + 4 # sizeof{size, type, data, crc}
        print("Chunk ID: %s, size: %i" % (chunk_id, size))

        # Process current chunk
        if chunk_id == "IHDR": self.get_IHDR(f)
        elif chunk_id == "pHYs": self.get_pHYs(size, f, ptr)
        elif chunk_id == "tIME": self.get_tIME(f)
        elif chunk_id == "iTXt": self.get_iTXt(size, f, ptr)
        elif chunk_id == "IDAT": self.get_IDAT(size, f)
        elif chunk_id == "IEND": return

        # TODO: check for other type of chunks like PLTE, sRGB, gAMA, zTXT, tRNS

        # Process next chunk
        self.get_chunk(f, next_chunk)

    def get_IHDR(self, f):
        """ IHDR Header """
        self.width = get_bytes(f, 4)
        self.height = get_bytes(f, 4)
        self.bit_depth = get_bytes(f, 1)
        self.color_type = get_bytes(f, 1)
        self.comp_method = get_bytes(f, 1)
        self.filter_method = get_bytes(f, 1)
        self.interlace_method = get_bytes(f, 1)
        #print("""width: %i, height: %i, bit_depth: %i, color_type: %i, comp_method: %i,
        #         filter_method: %i, interlace_method: %i""" % (self.width, self.height, self.bit_depth,
        #       self.color_type, self.comp_method, self.filter_method, self.interlace_method))

    def get_pHYs(self, size, f, ptr):
        """ pHYs Header """
        pass # Not that important

    def get_tIME(self, f):
        """ tIME Header. Timestamp in UTC """
        year = get_bytes(f, 2) # 0-9999
        month = get_bytes(f, 1) # 1-12
        day = get_bytes(f, 1) # 1-31
        hour = get_bytes(f, 1) # 0-23
        minute = get_bytes(f, 1) # 0-59
        second = get_bytes(f, 1) # 0-60
        self.timestamp = datetime.datetime(year, month, day, hour, minute, second)
        #print("Timestamp: " + str(self.timestamp))

    def get_iTXt(self, size, f, ptr):
        self.kw = ""
        while 1:
            b = f.read(1);
            if b == '\0': break
            self.kw += b
        comp_flag = get_bytes(f, 1)
        comp_method = get_bytes(f, 1)
        lang_tag = ""
        while 1:
            b = f.read(1);
            if b == '\0': break
            lang_tag += b
        translated_kw = ""
        while 1:
            b = f.read(1);
            if b == '\0': break
            translated_kw += b
        self.text = ""
        for i in range(f.tell(), ptr+4+4+size): # sizeof{size, type, data}
            self.text += f.read(1)

    def get_IDAT(self, size, f):
        pass

if __name__ == '__main__':
    infile = sys.argv[1]
    img = PNG(infile)

