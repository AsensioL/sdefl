# Compression/Decompression Tool (`ztool`)

## TLDR: Build the shared library in order to run the Python `ztool`

To avoid accidentally changing the compression/decompression code by
translating it to Python, you must build a shared library containing the
compression and decompression functions.

```shell
mkdir build && cd build
gcc --shared -fPIC ../sdefl.c ../sinfl.c -o sdefl.so
```

## Introduction

This folder is dedicated to a compression-decompression tool which aims to
make it easier for developers to extract data from the controller.

For compression + Base64, the tool expects/uses the following JSON format:
```json
{
    "hash": "<sha256-of-the-original-data>",
    "b64": "original-data-compressed-then-transformed-with-base64"
}
```

For raw compression the tool supports .bin files where the only data is the
result of the compression.

## Use in firmware (compression-only)

```cpp
#include "sdefl.h"
#include "base64.h

// ...

String inputFile(/* externally provided String */);

// Compress input file
size_t compressionBufferSize = sdefl_bound(inputFile.length());
std::vector<uint8_t> outCompressedInputFile(compressionBufferSize, 0); // 0-initialized buffer
{
    struct sdefl s = {0};
    int outsize = sdeflate(&s, outCompressedInputFile.data(), reinterpret_cast<const unsigned char*>(inputFile.c_str()), inputFile.length(), 1); // Lowest compression level (1) is sufficient
    outCompressedInputFile.resize(outsize);
}

// Calculate the Base64 of the compressed input file
size_t b64size = Base64::getEncodedSize(outCompressedInputFile.size(), /* nullTerminate */ true);
std::vector<char> b64CompressedInputFile(b64size, 0);
Base64::encode(outCompressedInputFile.data(), outCompressedInputFile.size(),
        b64CompressedInputFile.data(), b64size, /* nullTerminate */ true);

// Hash original input file
String inputFileHash = sha256(inputFile);

String inputFileInfo = String::format(R"({"hash":"%s","b64":"%s"})", inputFileHash.c_str(), b64CompressedInputFile.data());

Particle.publish("B64CompressedInputFile ", inputFileInfo.c_str());
```

## Use outside firmware (compression and decompression)

The Python `ztool` script implements the decompression code to reverse
the compression performed in firmware by `sdefl.c`.
This tool also implements the same compression algorithm as `sdefl.c` for
validation purposes.

Compression examples:
```shell
./ztool -c file.txt                      # Simple compression using default (JSON output with hash, automatic output filename)
./ztool -c file.txt -o file.json         # Compress to JSON (with hash), manual output filename
./ztool -c file.txt --no-hash            # Compress to JSON (with hash), skip hash field (smaller size)
./ztool -c file.txt --raw                # Compress to RAW (binary) (smallest size)
```

Decompression examples:
```shell
./ztool file.json                        # Simple decompression from JSON (auto-decide output filename, check hash)
./ztool file.json -o contents.txt        # Decompress from JSON (check hash), manual output filename
./ztool file.json --no-hash              # Decompress from JSON (check hash), skip hash check
./ztool file.bin --raw                   # Decompress from RAW (binary) data
```

## Choice of compression algorithm

The compression algorithm is Deflate (RFC 1951), implemented by
https://github.com/fxfactorial/sdefl with some changes to reduce RAM use to
about 2KB (slightly lower compression ratio, but still worth it).

The choice was made between two candidates:
* https://github.com/fxfactorial/sdefl
* https://github.com/ariya/FastLZ

The criteria to chose a compression algorithm were:
* Small binary footprint size
* Small RAM cost
* No dependencies, and few files
* Lowest compress ratio for the reference file
  * Reference file: 1.3.0 Reader Config file (vtap_config_1_3_0.txt) in its
    "modified form". The modified form involves removing empty lines and adding
    2 line jumps at the end of the file, which represents the changes performed
    by the VTAP100 reader when reading this config file back from it.

Compression Results (lower is better)
* FastLZ: 59.9%
* sdefl (original, RAM = 2.2MB, 5 passes):  53.8%
  * Note: Compression parameters are default values: `SDEFL_MAX_OFF = (1 << 15)` and `SDEFL_HASH_BITS = 19`
* sedfl (reduced*, RAM = 2KB, 1 pass): 56.6%  <-- Winner
  * Note: Compression parameters are optimized for low RAM: `SDEFL_MAX_OFF = (1 << 8)` and `SDEFL_HASH_BITS = 8`
