#include "sdefl.h"
#include "sinfl.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    if (argc != 2) return 1;

    FILE *f = fopen(argv[1], "rb");
    fseek(f, 0, SEEK_END);
    int size = ftell(f);
    fseek(f, 0, SEEK_SET);
    unsigned char *in = malloc(size);
    fread(in, 1, size, f);
    fclose(f);

    unsigned char *out = malloc(sdefl_bound(size));
    char outname[256] = {0};
    int outsize;

    if (strstr(argv[1], ".dfl")) {
        outsize = sinflate(out, in, size);
        char *p = strstr(argv[1], ".dfl");
        strncpy(outname, argv[1], p - argv[1]);
        strcat(outname, "_inflated");
        strcat(outname, p + 4);
    } else {
        struct sdefl s = {0};
        outsize = sdeflate(&s, out, in, size, 1);
        printf("Hash table size: %lu Deflated: %.1f%% Size: %d\n", sizeof(s), (outsize * 100.0) / size, outsize);
        sprintf(outname, "%s.dfl", argv[1]);
    }

    FILE *g = fopen(outname, "wb");
    fwrite(out, 1, outsize, g);
    fclose(g);
    free(in);
    free(out);
    return 0;
}