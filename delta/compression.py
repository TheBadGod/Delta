from .huffman import Codes, DecoderTable

class Symbol:
    def __init__(self, ml, val):
        self.MatchLength = ml
        self.Value = val

    def __str__(self):
        if self.MatchLength == 1:
            return f"LiteralSymbol <Value={chr(self.Value)}>"
        if self.Value == 0x54000:
            return f"IotaSymbol <Length={self.MatchLength}>"
        if 0x54000 < self.Value < 0x54004:
            return f"LruSymbol <Length={self.MatchLength} LruIdx={self.Value-0x54001}>"
        if 0x54004 <= self.Value:
            return f"CopySymbol <Length={self.MatchLength} Offset=0x{self.Value-0x54004:x}>"

        return f"Symbol <Value={self.Value:x}, MatchLength={self.MatchLength}>"


class CompressionFormat:
    def __init__(self, codes):
        self.codes0 = Codes(0x258, 0x10, True)
        self.codes1 = Codes(0x100, 0x10, True)
        self.codes2 = Codes(0x10, 0x10, True)

        self.codes0.SetLengths(codes[:0x258])
        self.codes1.SetLengths(codes[0x258:0x358])
        self.codes2.SetLengths(codes[0x358:])

        # main_tree
        self.dc0 = DecoderTable(self.codes0)
        # length_tree
        self.dc1 = DecoderTable(self.codes1)
        # aligned_offset_tree
        self.dc2 = DecoderTable(self.codes2)

    def __str__(self):
        return f"""CompressionFormat <
  DecoderTable0={self.dc0}
  DecoderTable1={self.dc1}
  DecoderTable2={self.dc2}
>"""

    def ReadSymbol(self, bs):
        value = self.dc0.Read(bs)

        if value < 0x100:
            # value < 0x100 is just a literal (with match size 1)
            return Symbol(1, value)
        else:
            length_header = (value-0x100)&7
            position_slot = (value-0x100)>>3

            if position_slot < 3:
                if position_slot == 0:
                    sym = (bs.r(0xe) - 0x2000) & (2**32-1)
                elif position_slot == 1:
                    sym = (bs.r(0x10) - 0x8000) & (2**32-1)
                    sym += 0x2000 * (1 if sym < 0x8000 else -1)
                elif position_slot == 2:
                    sym = (bs.r(0x12) - 0x20000) & (2**32-1)
                    sym += 0xa0000 * (1 if sym < 0x20000 else -1)

                position_slot = sym + 0x2a000
                assert False, "Untested territory 1"
            elif position_slot < 7:
                position_slot = (position_slot - 3) + 0x54000
            else:
                position_slot -= 7
                if position_slot == 0:
                    # some hardcoded huffman tree? values are encoded as
                    # 0XX 10XXX 11XXXX with X being the actual data bits
                    if bs.r(1):
                        if bs.r(1):
                            r = bs.r(4) + 8
                        else:
                            r = bs.r(3)
                        new_slot = r + 4
                    else:
                        new_slot = bs.r(2)
                    position_slot = new_slot + 36

                if position_slot >= 4:
                    nbits = (position_slot >> 1) - 1
                    low = (position_slot & 1) + 2
                    if nbits < 4:
                        position_slot = low << nbits
                        position_slot |= bs.r(nbits)
                    else:
                        nbits = (position_slot >> 1) - 5
                        if nbits:
                            low = low << nbits
                            low |= bs.r(nbits)

                        x = self.dc2.Read(bs)
                        assert x < 16
                        position_slot = x | (low << 4)
                
                position_slot += 0x54003

            if length_header == 0:
                match_length = self.dc1.Read(bs)
                if not match_length:
                    match_length = bs.ReadNumber()
                length_header= match_length + 7

            match_length = length_header + 1

            return Symbol(match_length, position_slot)

    def Decompress(self, bs, source, target_size, debug=False):
        buffer = b""
        length = 0
        
        # you have to imagine the source and target buffer right after
        # each other, special encodings will do target[-x] and some will do
        # target[+x] which in the first case might reach into the source
        # buffer

        lru = [0,0,0]

        while len(buffer) < target_size:
            if bs.finished():
                print(f"Could not read the stream, got {length} bytes, expected {target_size}")
                return None
            sym = self.ReadSymbol(bs)
            # length 1 is always a literal...

            if debug:
                print("Read", sym)

            if sym.MatchLength == 1:
                buffer += bytes([sym.Value])
            else:
                if sym.Value == 0x54000:
                    buffer += source[length:length+sym.MatchLength]
                    addr = length - len(source)
                    if addr != lru[0]:
                        tmp = lru[1]
                        lru[1] = lru[0]
                        if addr != tmp:
                            lru[2] = tmp
                        lru[0] = addr

                elif sym.Value > 0x54000:
                    idx = sym.Value - 0x54001
                    if idx < 3:
                        addr = lru[idx]
                    else:
                        addr = idx - 2

                    #print("Chosen value: ", sym, hex(length-addr), len(buffer), buffer)
                    src_addr = length-addr

                    # update the least recently used addresses. in the binary
                    # this happens after copying the data, but whatever
                    if addr != lru[0]:
                        tmp = lru[1]
                        lru[1] = lru[0]
                        # if lru would be kicked out, then we need to shift it
                        if addr != tmp:
                            lru[2] = tmp
                        lru[0] = addr

                    assert src_addr < len(buffer), "Trying to read uninited memory"
                    for addr in range(src_addr, src_addr + sym.MatchLength):
                        if addr < 0:
                            added = source[addr]
                        else:
                            added = buffer[addr]
                        buffer += bytes([added])


                else:
                    print(f"Rift stuff: {sym} {buffer}")
                    assert False, "NYI (rift table stuff)"

            length += sym.MatchLength

            
        return buffer

class CompositeFormat:
    def __init__(self, bs):
        if bs.r(1):
            self.num_layers = 1
            default_layer = bytes([9]*424+[10]*176+[8]*256+[4]*16)
            assert len(default_layer)==0x368
            self.layers = [default_layer]
        else:
            self.num_layers = n = bs.ReadInt()
            compression_lengths = []
            prev = 0
            # we have n increments (starting with increment from 0)
            for i in range(n):
                length = bs.ReadInt()
                compression_lengths.append(prev + length)
                prev = compression_lengths[-1]

            data = []
            for i in range(39):
                data.append(bs.r(4))
            
            # create codes
            codes = Codes(39, 15, False)
            codes.SetLengths(data)

            # create decodertable
            dt = DecoderTable(codes)

            previous_layer = [0]*0x368
            self.layers = []
            for i in range(n):
                self.layers.append(bs.ReadCompressionLengths(dt, previous_layer))
                previous_layer = self.layers[-1]

    def GetCompressionFormat(self):
        if self.num_layers != 1:
            assert False, "Not implemented, check GetCompressionFormatRead"
        
        # some more bullshit here
        return CompressionFormat(self.layers[0])

        