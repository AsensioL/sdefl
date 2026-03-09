#!/usr/bin/env python3
from sdefl_wrapper import inflate, deflate
from pathlib import Path
import argparse
import hashlib
import base64
import json
import sys

# Options:
#   -o, --output FILE      Output file (auto-generated if not specified)
#   -c, --compress         Compression mode (default is decompress)
#   -r, --raw              Compressed data is binary (instead of JSON)
#   -y, --yes              Overwrite output file without prompting
#   --no-hash              Skip adding/verifying SHA256 (no effect in raw mode)
#   -h, --help             Show this help message

def cli():
    parser = argparse.ArgumentParser(description="Compression/decompression tool", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("input_file", default=None, help="Input file")
    parser.add_argument("-o", "--output", required=False, default=None, help="Output file")
    parser.add_argument("-c", "--compress", action="store_true", help="Compression mode (default is decompress)")
    parser.add_argument("-r", "--raw", action="store_true", default=False, help="Compressed data is binary (instead of JSON)")
    parser.add_argument("-y", "--yes", action="store_true", default=False, help="Overwrite output file without prompting")
    parser.add_argument("--no-hash", action="store_true", default=False, help="Skip adding/verifying SHA256 (has no effect in raw mode)")

    example_help = f"""Basic examples:
  {sys.argv[0]} -c file.txt                      Compress to JSON (auto-decide output filename)
  {sys.argv[0]} file.json                        Decompress from JSON (auto-decide output filename)

Advanced examples:
  {sys.argv[0]} file.json -o contents.txt        Decompress from JSON with provided output filename
  {sys.argv[0]} file.bin -r                      Decompress RAW (binary) data
  {sys.argv[0]} -c file.txt -o file.json         Compress to JSON (with hash)
  {sys.argv[0]} -c file.txt -o file.json --raw   Compress to RAW (binary) (can't include hash)
    """
    parser.epilog = example_help

    args = parser.parse_args()

    # Check input file
    input_file = Path(args.input_file)
    if not input_file.is_file():
        print(f"Error: input file {args.input_file} does not exist", file=sys.stderr)

    # Auto-generate output file name if not defined
    if not args.output:
        if args.compress and args.raw:
            args.output = input_file.with_suffix('.bin')
        elif args.compress and not args.raw:
            args.output = input_file.with_suffix('.json')
        else: # decompress
            # we can't guess what the original data was, so use txt
            args.output = input_file.with_suffix('.txt')

    if Path(args.output).is_file() and not args.yes:
        reply = input(f"WARNING: output file {args.output} already exist. Overwrite? [y/n] ")
        if 'y' not in reply.lower():
            print(f"Stopped")
            sys.exit(1)

    return args


def decompress(input_file: Path, output_file: Path, use_json = True, hash_check = True):
    # Load input_data
    if use_json:
        # input data is in json format, parse b64 field contents
        input_json = input_file.read_text()
        parsed_json = json.loads(input_json)
        input_b64 = parsed_json.get('b64', None)
        if input_b64 is None:
            print(f'Expected `b64` field with compressed contents in Base64 format', file=sys.stderr)
            sys.exit(1)

        try:
            input_data = base64.b64decode(input_b64, validate=True)
        except Exception as e:
            print(f'Invalid Base64 data in `b64` field', file=sys.stderr)
            sys.exit(1)
    else:
        input_data = input_file.read_bytes()

    # Decompress and write to file
    output_data = inflate(input_data)

    if use_json and hash_check:
        original_hash = parsed_json.get('hash', None)
        if not original_hash:
            print(f'WARNING: Could not validate hash. Expected `hash` field missing', file=sys.stderr)
            # Continue execution and write to the output file
        else:
            # Hash the original file, if required
            calculated_hash = hashlib.sha256(output_data).hexdigest()
            if (original_hash != calculated_hash):
                print(f'ERROR: Calculated hash `{calculated_hash}` does not match original file', file=sys.stderr)
                sys.exit(1)

    output_file.write_bytes(output_data)
    print(f"Contents writen to {output_file.absolute()}")

    # Heuristic check for inflate error
    if len(output_data) == 0:
        # If the original data was empty, don't show the error
        original_data_was_empty =  use_json and hash_check and original_hash == hashlib.sha256(b"").hexdigest()
        if original_data_was_empty:
            print("Original data was an empty file, so decompressed data is also an empty file")
        else:
            print("ERROR: Deflate output is 0 bytes. This usually indicates an error", file=sys.stderr)
            sys.exit(1)


def compress(input_file: Path, output_file: Path, use_json = True, hash_check = True):
    # Load input data and compress it
    input_data = input_file.read_bytes()
    deflated_input_data = deflate(input_data)

    # Hash the original file, if required
    input_hash = None
    if hash_check:
        input_hash = hashlib.sha256(output_data).hexdigest()

    if use_json:
        # output data needs to be in json format, encode into b64 field
        output_b64 = base64.b64encode(deflated_input_data)
        output_dict = { 'b64': output_b64.decode() } # json.dumps needs string
        if input_hash:
            output_dict['hash'] = input_hash
        output_data = json.dumps(output_dict).encode() # writer needs bytes
    else:
        output_data = deflated_input_data

    # Write to file
    output_file.write_bytes(output_data)
    print(f"Contents written to {output_file.absolute()}")


def main():
    args = cli()

    input_file = Path(args.input_file)
    output_file = Path(args.output)
    use_json = not args.raw
    hash_check = not args.no_hash

    if args.compress:
        compress(input_file, output_file, use_json=use_json, hash_check=hash_check)
    else:
        decompress(input_file, output_file, use_json=use_json, hash_check=hash_check)


if __name__ == "__main__":
    main()