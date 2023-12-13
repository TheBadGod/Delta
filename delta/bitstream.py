from .util import LowestLookup
from .compression import CompositeFormat

class BitStream:
    def __init__(self, bts):
        self.bits = []
        for b in bts:
            for i in range(8):
                self.bits.append(1 if b&(1<<i) else 0)
        self.cursor = 0

        leftover = self.r(3)
        if leftover:
            self.bits = self.bits[:-leftover]

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

    def ReadBuffer(self):
        size = self.ReadInt()
        self.cursor += 7
        self.cursor &= 0xfffffff8
        return self.rb(size)
    
    def finished(self):
        return self.cursor >= len(self.bits)

