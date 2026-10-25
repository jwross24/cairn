#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
typedef uint32_t u32;
typedef struct { u32 nA, nB, offA, offB, b00, b01, b10, b11, w0, w0s, w1, w1s, pad[4]; } PInfo;

static const char *SRC =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"struct PInfo { uint nA,nB,offA,offB,b00,b01,b10,b11,w0,w0s,w1,w1s,pad0,pad1,pad2,pad3; };\n"
"struct G { uint np_; uint p0; uint p1; uint cap; };\n"
"kernel void pf(constant G& g [[buffer(0)]], device const PInfo* pi [[buffer(1)]], device const uint* wpref [[buffer(2)]],\n"
"  device const uint* HA0 [[buffer(3)]], device const uint* HA1 [[buffer(4)]], device const uint* HB0 [[buffer(5)]], device const uint* HB1 [[buffer(6)]],\n"
"  device const uint* bm0 [[buffer(7)]], device const uint* bm1 [[buffer(8)]], device atomic_uint* cnt [[buffer(9)]], device uint4* out [[buffer(10)]],\n"
"  uint gid [[thread_position_in_grid]]) {\n"
"  uint total = wpref[g.np_]; if (gid >= total) return;\n"
"  uint lo = 0, hi = g.np_;\n"
"  while (hi - lo > 1) { uint mid = (lo + hi) >> 1; if (wpref[mid] <= gid) lo = mid; else hi = mid; }\n"
"  PInfo P = pi[lo]; uint w = gid - wpref[lo]; uint dn = w >= P.nA ? 1u : 0u; uint ia = w - dn * P.nA;\n"
"  uint p0 = g.p0, p1 = g.p1;\n"
"  uint v0 = (dn ? P.b01 : P.b00) + HA0[P.offA + ia]; if (v0 >= p0) v0 -= p0;\n"
"  uint v1 = (dn ? P.b11 : P.b10) + HA1[P.offA + ia]; if (v1 >= p1) v1 -= p1;\n"
"  for (uint ib = 0; ib < P.nB; ib++) {\n"
"    uint y0 = v0 + HB0[P.offB + ib]; if (y0 >= p0) y0 -= p0;\n"
"    uint q0 = mulhi(y0, P.w0s); uint r0 = y0 * P.w0 - q0 * p0; if (r0 >= p0) r0 -= p0;\n"
"    if (!((bm0[r0 >> 5] >> (r0 & 31u)) & 1u)) continue;\n"
"    uint y1 = v1 + HB1[P.offB + ib]; if (y1 >= p1) y1 -= p1;\n"
"    uint q1 = mulhi(y1, P.w1s); uint r1 = y1 * P.w1 - q1 * p1; if (r1 >= p1) r1 -= p1;\n"
"    if (!((bm1[r1 >> 5] >> (r1 & 31u)) & 1u)) continue;\n"
"    uint idx = atomic_fetch_add_explicit(cnt, 1u, memory_order_relaxed);\n"
"    if (idx < g.cap) out[idx] = uint4(lo, dn, ia, ib);\n"
"  }\n"
"}\n";

static id<MTLDevice> dev; static id<MTLCommandQueue> cq; static id<MTLComputePipelineState> pso;
static id<MTLBuffer> bBm0, bBm1; static u32 gp0, gp1;
static double now_s(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + 1e-9 * t.tv_nsec; }

int gpu_init(const u32 *bm0, size_t n0, const u32 *bm1, size_t n1, u32 p0, u32 p1){
  dev = MTLCreateSystemDefaultDevice(); if(!dev){ fprintf(stderr, "no Metal device\n"); return 1; }
  NSError *err = nil; MTLCompileOptions *co = [MTLCompileOptions new];
  id<MTLLibrary> lib = [dev newLibraryWithSource:[NSString stringWithUTF8String:SRC] options:co error:&err];
  if(!lib){ fprintf(stderr, "metal compile: %s\n", [[err localizedDescription] UTF8String]); return 2; }
  id<MTLFunction> fn = [lib newFunctionWithName:@"pf"];
  pso = [dev newComputePipelineStateWithFunction:fn error:&err]; if(!pso){ fprintf(stderr, "pso: %s\n", [[err localizedDescription] UTF8String]); return 3; }
  cq = [dev newCommandQueue];
  bBm0 = [dev newBufferWithBytes:bm0 length:n0 * 4 options:MTLResourceStorageModeShared];
  bBm1 = [dev newBufferWithBytes:bm1 length:n1 * 4 options:MTLResourceStorageModeShared];
  gp0 = p0; gp1 = p1; return 0;
}

long gpu_batch(u32 nparents, const PInfo *pi, const u32 *HA0, size_t nHA, const u32 *HA1, const u32 *HB0, size_t nHB, const u32 *HB1, u32 cap, u32 *out, double *kernel_s){
  u32 *wp = malloc(4 * (nparents + 1)); wp[0] = 0;
  for(u32 j = 0; j < nparents; j++) wp[j + 1] = wp[j] + 2 * pi[j].nA;
  u32 total = wp[nparents];
  #define BUF(p, n) [dev newBufferWithBytes:(p) length:((n) ? (n) : 4) options:MTLResourceStorageModeShared]
  struct { u32 np_, p0, p1, cap; } g = { nparents, gp0, gp1, cap };
  id<MTLBuffer> bPi = BUF(pi, sizeof(PInfo) * nparents), bWp = BUF(wp, 4 * (nparents + 1));
  id<MTLBuffer> bA0 = BUF(HA0, 4 * nHA), bA1 = BUF(HA1, 4 * nHA), bB0 = BUF(HB0, 4 * nHB), bB1 = BUF(HB1, 4 * nHB);
  id<MTLBuffer> bC = [dev newBufferWithLength:16 options:MTLResourceStorageModeShared];
  id<MTLBuffer> bO = [dev newBufferWithLength:(size_t)cap * 16 options:MTLResourceStorageModeShared];
  *(u32 *)[bC contents] = 0;
  double t0 = now_s();
  id<MTLCommandBuffer> cb = [cq commandBuffer]; id<MTLComputeCommandEncoder> en = [cb computeCommandEncoder];
  [en setComputePipelineState:pso];
  [en setBytes:&g length:sizeof g atIndex:0];
  id<MTLBuffer> bufs[] = { bPi, bWp, bA0, bA1, bB0, bB1, bBm0, bBm1, bC, bO };
  for(int i = 0; i < 10; i++) [en setBuffer:bufs[i] offset:0 atIndex:1 + i];
  NSUInteger tg = pso.maxTotalThreadsPerThreadgroup; if(tg > 256) tg = 256;
  [en dispatchThreads:MTLSizeMake(total, 1, 1) threadsPerThreadgroup:MTLSizeMake(tg, 1, 1)];
  [en endEncoding]; [cb commit]; [cb waitUntilCompleted];
  *kernel_s += now_s() - t0;
  free(wp);
  if(cb.status != MTLCommandBufferStatusCompleted){ fprintf(stderr, "command buffer failed: %s\n", [[[cb error] localizedDescription] UTF8String]); return -2; }
  u32 n = *(u32 *)[bC contents]; if(n > cap) return -1;
  memcpy(out, [bO contents], (size_t)n * 16);
  return (long)n;
}
