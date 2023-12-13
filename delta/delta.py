from .bitstream import BitStream

class DeltaInfo:
    def __init__(self, Version, Code, Flags, TargetSize, HashAlgId, Hash):
        self.Version = Version
        self.Code = Code
        self.Flags = Flags
        self.TargetSize = TargetSize
        self.HashAlgId = HashAlgId
        self.Hash = Hash

    def __str__(self):
        return f"Delta <Version={self.Version} Code={self.Code} Flags=0x{self.Flags:x} TargetSize=0x{self.TargetSize:x} HashAlgId=0x{self.HashAlgId:x} Hash={self.Hash}>"

def get_delta_info(pa30):
    assert pa30[:4] == b"PA30"

    # go to start of bitstream
    # first four are b"PA30" header
    # then 8 bytes timestamp?
    pa30 = pa30[12:]

    bs = BitStream(pa30)
    
    Version = bs.ReadInt()
    Code = bs.ReadInt()
    Flags = bs.ReadInt()
    TargetSize = bs.ReadInt()
    HashAlgId = bs.ReadInt()
    Hash = bs.ReadBuffer().hex()

    return DeltaInfo(Version, Code, Flags, TargetSize, HashAlgId, Hash)

def parse_delta(pa30, source, debug=False):
    assert pa30[:4] == b"PA30"

    # go to start of bitstream
    # first four are b"PA30" header
    # then 8 bytes timestamp?
    pa30 = pa30[12:]

    bs = BitStream(pa30)
    
    Version = bs.ReadInt()
    Code = bs.ReadInt()
    Flags = bs.ReadInt()
    TargetSize = bs.ReadInt()
    HashAlgId = bs.ReadInt()
    Hash = bs.ReadBuffer().hex()

    # code 1 == raw
    if debug:
        print(f"{Version=}, {Code=}, {Flags=}, {TargetSize=}, {HashAlgId=:x}, {Hash=}")

    preProcessBuffer = bs.ReadBuffer()
    if preProcessBuffer:
        print("There seems to be a preprocessbuffer, idk how to handle those")
        return None
    patchBuffer = bs.ReadBuffer()

    # create new bitstream with patchbuffer
    bs = BitStream(patchBuffer)

    # compo::RiftTable::InternalFromBitReader
    if bs.r(1):
        print("Parsing a rifttable, not implemented")
        print(bs.ReadInt())
        print(bs.ReadInt())
        # compo::RiftTable::FromBitReaderWithFormat
        for _ in range(bs.ReadInt()):
            # i wouldnt even know what to do here
            pass
        return None

    # compo::CompositeFormat::InternalFromBitReader
    composite_format = bs.ReadCompositeFormat()
    fmt = composite_format.GetCompressionFormat()

    decoded = fmt.Decompress(bs, source, TargetSize, debug)

    assert bs.finished(), f"Bitreader should be finished, but has {len(bs.bits)-bs.cursor} bits left"

    return decoded

