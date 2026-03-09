from pathlib import Path
import ctypes
import sys

# 1. Check sure the library exists
dyn_library_location = 'build/sdefl.so'
if not Path(dyn_library_location).is_file():
    script_directory = Path(__file__).resolve().parent
    print(f"""ERROR: You must build the shared library first. Copy and paste command:
  mkdir -p "{script_directory}/build" && \\
  cd "{script_directory}/build" && \\
  gcc --shared -fPIC ../sdefl.c ../sinfl.c -o sdefl.so && \\
  cd -""", file=sys.stderr)
    sys.exit(1)

# 2. Load shared library (.so or .dll)
lib_path = "build/sdefl.so"
c_functions = ctypes.CDLL(lib_path)


# 3. Define function prototype (optional but recommended for type safety)
class SDefl(ctypes.Structure):
    _fields_ = [
        ("bits", ctypes.c_int),
        ("cnt", ctypes.c_int),
        ("tbl", ctypes.c_int * ((1 << 8) - 1)),
        ("prv", ctypes.c_int * ((1 << 8))),
    ]
# int sdeflate(struct sdefl *s, unsigned char *out, const unsigned char *in, int in_len, int lvl);
c_functions.sdeflate.restype = ctypes.c_int
c_functions.sdeflate.argtypes = [
    ctypes.POINTER(SDefl),           # struct sdefl *s
    ctypes.POINTER(ctypes.c_ubyte),  # unsigned char *out
    ctypes.POINTER(ctypes.c_ubyte),  # const unsigned char *in
    ctypes.c_int,                    # int in_len
    ctypes.c_int                     # int lvl
]
# int sinflate(unsigned char *out, const unsigned char *in, int size)
c_functions.sinflate.restype = ctypes.c_int
c_functions.sinflate.argtypes = [
    ctypes.POINTER(ctypes.c_ubyte),  # unsigned char *out
    ctypes.POINTER(ctypes.c_ubyte),  # const unsigned char *in
    ctypes.c_int,                    # int size
]
# int sdefl_bound(int in_len)
c_functions.sdefl_bound.restype = ctypes.c_int
c_functions.sdefl_bound.argtypes = [
    ctypes.c_int,                    # int in_len
]

def inflate(compressed_data: bytes, max_output_length = 2**16):
    """ Params:
    compressed_data:   binary data to be extracted/inflated in bytes-like array
    max_output_length: optional maximum size of the decompressed data (needed
                       because of the C-interface). Default is 16KB
    """
    # Prepare params to inflate compressed data
    in_len  = len(compressed_data)
    in_ptr  = (ctypes.c_ubyte * in_len).from_buffer_copy(compressed_data)
    out_ptr = (ctypes.c_ubyte * max_output_length)()

    # Inflate compressed data
    out_len = c_functions.sinflate(out_ptr, in_ptr, in_len)
    return bytes(out_ptr[0:out_len])


def deflate(uncompressed_data: bytes, level = 1):
    """ Params:
    uncompressed_data: binary data to be compressed/deflated in bytes-like array
    level:             compression level
    """
    # Prepare params to deflate data
    c_struc = (SDefl * 1)()
    in_len  = len(uncompressed_data)
    in_ptr  = (ctypes.c_ubyte * in_len).from_buffer_copy(uncompressed_data)
    out_ptr = (ctypes.c_ubyte * c_functions.sdefl_bound(in_len))()  # Calculate and allocate upper bound for compressed data size

    # Deflate compressed data
    out_len = c_functions.sdeflate(c_struc, out_ptr, in_ptr, in_len, level)
    return bytes(out_ptr[0:out_len])

if __name__ == "__main__":
    # Test that everything works
    import random
    random_bytes = random.randbytes(1)
    assert random_bytes == inflate(deflate(random_bytes))
    random_bytes = random.randbytes(1024)
    assert random_bytes == inflate(deflate(random_bytes))
    print("SUCCESS: Random bytes were compressed and decompressed matching original data")
    empty_bytes = b""
    assert empty_bytes == inflate(deflate(empty_bytes))
    print("SUCCESS: Empty bytestring was compressed and decompressed matching original data")

