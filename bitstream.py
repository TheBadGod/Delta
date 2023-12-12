from .util import LowestLookup
from .compression import CompositeFormat

class BitStream:
    def __init__(self, bts):
        self.bits = []
        for b in bts:
            for i in range(8):
                self.bits.append(1 if b&(1<<i) else 0)
        self.cursor = 0

    def r(self,n):
        assert self.cursor + n <= len(self.bits), f"Wanted to read {n} bits, only have {len(self.bits)-self.cursor} available"
        b = self.bits[self.cursor:self.cursor+n]
        self.cursor += n
        return sum([c<<i for i,c in enumerate(b)])
    def p(self,n):
        b = self.bits[self.cursor:self.cursor+n]
        return sum([c<<i for i,c in enumerate(b)])
    def rb(self,n):
        return bytes([self.r(8) for _ in range(n)])

    def ReadInt(self):
        size = LowestLookup(self.p(32) | (1<<16))
        assert size != 16, "Cant read that many nibbles!"
        self.r(size + 1) # need to remove the size indicator
        n = self.r(4 * size + 4)
        return n

    def ReadNumber(self):
        v4 = LowestLookup(self.p(32))
        self.r(v4 + 1)
        number = self.r(v4 + 8)
        return (1 << (v4 + 8)) | number

    def ReadCompositeFormat(self):
        return CompositeFormat(self)

    def ReadCompressionLengths(self, dt, previous):
        data = bytearray([0]*0x368)
        offset = 0
        while offset < 0x368:
            value = dt.Read(self)

            if value >= 23:
                value -= 23
                nbits = value & 7
                if nbits >= 3:
                    nbits -= 1
                    n = self.r(nbits) | (1 << nbits)
                else:
                    n = nbits + 1

                # take references, so i don't have to copy stuff later
                if value < 8:
                    A = data
                    src = offset - 1
                else:
                    A = previous
                    src = offset
                
                #print("Inserting", n, "chars")
                for _ in range(n):
                    data[offset + _] = A[src + _]

                offset += n
            elif value >= 0x11:
                assert False, f"NYI: {value}"
            else:
                data[offset] = value
                offset += 1

        return bytes(data)

    def ReadSymbol(self, lut):
        N = bs.p(32) | (1<<31)
        size = LowestLookup(self.p(32) | (1<<31))
        s = [0,1,2,6,10,14,16,17,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18][size]
        o = (N>>(size+1)) & [0,0,3,3,3,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0][size]
        codesize = s + o
        symbol = [0x31,0x30,0x189,0x1bd,0x1bb,0x1c1,0x1a9,0x1b2,
                   0x1b0,0x1ba,0x1ac,0x1b5,0x1b1,0x1bc,0x1aa,0x1ab,
                   0x1a3,0x19d,0x18a][codesize]
        symbol_length = lut[symbol]
        self.r(symbol_length)
        #print(size, codesize, symbol, symbol_length)

        if symbol >= 0x100:
            symbol -= 0x100
            lo = symbol & 7
            hi = symbol >> 3
            print(hi, lo)

            
            if hi == 0:
                length = self.r(14) - 0x2000 + 0x2a000
            elif hi == 1:
                length = self.r(16)
                if length < 0x8000:
                    length = length + 0x2000 + 0x2a000
                else:
                    length = length - 0x2000 + 0x2a000
            elif hi == 2:
                length = self.r(18)
                if length < 0x20000:
                    length = length + 0x34000
                else:
                    length = length - 0xa000
            elif hi < 7:
                length = hi - 3 + 0x54000
            else:
                length = 0
                x = hi - 7
                if x < 4:
                    assert False
                else:
                    a = (x >> 1) - 1
                    b = (x & 1) + 2
                    
                    if a >= 4:
                        a -= 4
                        assert x>>1 != 5, "NYI"
                        value = (b << a) | (self.r(a))
                        print(value)

                    else:
                        assert False

            length &= (2**32-1)
            assert False, "special stuff (delta encoding) not implemented"
        else:
            return symbol
        
        return n

    def ReadBuffer(self):
        size = self.ReadInt()
        self.cursor += 7
        self.cursor &= 0xfffffff8
        return self.rb(size)
    
    def finished(self):
        return self.cursor >= len(self.bits) or (set(self.bits[self.cursor:]) == {0} and len(self.bits)-self.cursor<=7)

