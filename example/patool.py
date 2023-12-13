from argparse import ArgumentParser
from pwn import hexdump, xor

try:
    from delta import parse_delta, get_delta_info
except:
    if __package__ is None:
        # https://stackoverflow.com/questions/11536764/how-to-fix-attempted-relative-import-in-non-package-even-with-init-py/27876800#27876800
        import sys
        from os import path
        sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
        from delta import parse_delta, get_delta_info
    else:
        from ..delta import parse_delta, get_delta_info

if __name__ == "__main__":
    parser = ArgumentParser(
            prog="patool",
            description="Tool to parse PA30 (delta patch) files",
        )

    parser.add_argument("filename", help="The file you want to parse")

    parser.add_argument("--input", "-i", help="If you want to apply the patch the source file to apply the patch to", required=False)
    parser.add_argument("--output", "-o", help="If you want to apply the patch the destination file to output the patched data", required=False)
    parser.add_argument("--diff", "-d", help="Print the diff of the source data (defaults to null bytes) and the output data", required=False, action="store_true")
    parser.add_argument("--verbose", "-v", help="Print extra verbose information", required=False, action="store_true")

    args = parser.parse_args()

    with open(args.filename, "rb") as f:
        data = f.read()
        if data[:4] != b"PA30" and data[4:8] == b"PA30":
            data = data[4:]
        
        delta = get_delta_info(data)

        
        if args.input:
            with open(args.input, "rb") as f:
                source = f.read()
            # fill with null bytes
            source += b"\x00" * (delta.TargetSize - len(source))
            output_patched_data = True
        else:
            source = b"\x00" * delta.TargetSize
            output_patched_data = False
        
        out_data = parse_delta(data, source, args.verbose)

        if args.diff:
            print(hexdump(bytes([out_data[i] if source[i]!=out_data[i] else 0 for i in range(len(out_data))])))
            
        if output_patched_data:
            if args.output:
                with open(args.output, "wb") as f:
                    f.write(out_data)
            elif not args.diff:
                # only print the data if we're not diffing and not writing to a file
                print(hexdump(out_data))

