if __name__ == '__main__':
    if __package__ is None:
        # https://stackoverflow.com/questions/11536764/how-to-fix-attempted-relative-import-in-non-package-even-with-init-py/27876800#27876800
        import sys
        from os import path
        sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
        from delta import parse_delta
    else:
        from ..delta import parse_delta

    xor = lambda x,y: bytes([a^b for a, b in zip(x, y)])

    # get the delta.exe file from the CTF challenge "delta" 
    # from 0ctf 2023
    from blobs import *

    # computed by a patched msdelta.dll to not care about checksums
    # and same source array as we have here
    wanted = open("out.dat","rb").read()

    DEBUG = False

    for i, blob in enumerate(blobs):
        source = bytes(range(256))[::-1]
        decoded = parse_delta(blob, source, DEBUG)
        if DEBUG:
            print(f"Decoded buffer {i} = {decoded}")

        diff = xor(wanted[i*0x100:i*0x100+0x100], decoded)
        if set(diff) != {0}:
            print(f"failed at {i}, diff: {diff.hex()}")
        else:
            print(f"success {i}")


