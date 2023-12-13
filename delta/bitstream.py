from .util import LowestLookup
from .compression import CompositeFormat

class BitStream:
    """
    As the name implies this is just a stream of bits
    """
    def __init__(self, bts):
        """
        Initialize a bitstream with the given bytes, reads 3 bits which
        signify how many leftover bits there are at the end of the stream
        """
        self.bits = []
        for b in bts:
            for i in range(8):
                self.bits.append(1 if b&(1<<i) else 0)
        self.cursor = 0

        leftover = self.r(3)
        if leftover:
            self.bits = self.bits[:-leftover]

    def r(self,n):
        """
        Read a specific amount of bits, advances the current position in the stream
        """
        assert self.cursor + n <= len(self.bits), f"Wanted to read {n} bits, only have {len(self.bits)-self.cursor} available"
        b = self.bits[self.cursor:self.cursor+n]
        self.cursor += n
        return sum([c<<i for i,c in enumerate(b)])
    def p(self,n):
        """
        Read a specific amount of bits without advancing the position
        """
        b = self.bits[self.cursor:self.cursor+n]
        return sum([c<<i for i,c in enumerate(b)])
    def rb(self,n):
        """
        Read raw bytes by simply reading a single byte n times
        """
        return bytes([self.r(8) for _ in range(n)])

    def ReadInt(self):
        """
        Reads an int, which is encoded as (nibble_count-1) zero-bits followed
        by 4*nibble_count bits making up the number
        """
        size = LowestLookup(self.p(32) | (1<<16))
        assert size != 16, "Cant read that many nibbles!"
        self.r(size + 1) # need to remove the size indicator
        n = self.r(4 * size + 4)
        return n

    def ReadNumber(self):
        """
        Reads a number. The length is unary-encoded with (bit_length-9) zero bits
        followed by a one bit, and then the number with bit_length-1 bits.
        The topmost bit is implied to be 1 (else we could store it in fewer bits)
        """
        v4 = LowestLookup(self.p(32))
        self.r(v4 + 1)
        number = self.r(v4 + 8)
        return (1 << (v4 + 8)) | number

    def ReadCompositeFormat(self):
        """
        Reads a composite format from the stream
        """
        return CompositeFormat(self)

    def ReadCompressionLengths(self, dt, previous):
        """
        Read a single layer of compression lengths given a decompression tree
        and the previous layer (which we can copy from)
        """
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
                # we take from the previous layer and add/subtract a small value
                add_value = value - 0x11
                if add_value < 3:
                    data[offset] = previous[offset] + add_value + 1
                else:
                    data[offset] = previous[offset] - add_value + 2
                offset += 1
            else:
                data[offset] = value
                offset += 1

        return bytes(data)

    def ReadBuffer(self):
        """
        Reads a buffer from the stream. The length is encoded as an int, then
        we go to the next full byte position and read length bytes
        """
        size = self.ReadInt()
        self.cursor += 7
        self.cursor &= 0xfffffff8
        return self.rb(size)
    
    def finished(self):
        """
        Returns true if the end of the stream has been reached
        """
        return self.cursor >= len(self.bits)

