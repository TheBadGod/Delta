from argparse import ArgumentParser

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

    args = parser.parse_args()

    with open(args.filename, "rb") as f:
        data = f.read()
        if data[:4] != b"PA30" and data[4:8] == b"PA30":
            data = data[4:]
        
        delta = get_delta_info(data)
        source = b"\x00" * delta.TargetSize
        parse_delta(data, source, True)
