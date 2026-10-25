#include <stdint.h>
#include <stddef.h>
typedef uint32_t u32;
typedef struct { u32 nA, nB, offA, offB, b00, b01, b10, b11, w0, w0s, w1, w1s, pad[4]; } PInfo;
int gpu_init(const u32 *bm0, size_t n0, const u32 *bm1, size_t n1, u32 p0, u32 p1);
long gpu_batch(u32 nparents, const PInfo *pi, const u32 *HA0, size_t nHA, const u32 *HA1, const u32 *HB0, size_t nHB, const u32 *HB1, u32 cap, u32 *out, double *kernel_s);
