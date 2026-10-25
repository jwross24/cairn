#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <stdio.h>
#include <time.h>
static const char *SRC =
"#include <metal_stdlib>\nusing namespace metal;\n"
"kernel void imad(device uint* out [[buffer(0)]], constant uint& iters [[buffer(1)]], uint gid [[thread_position_in_grid]]) {\n"
"  uint x0=gid,x1=gid+1,x2=gid+2,x3=gid+3,x4=gid+4,x5=gid+5,x6=gid+6,x7=gid+7; uint a=2654435761u, b=40503u;\n"
"  for (uint i = 0; i < iters; i++) {\n"
"    x0=x0*a+b; x1=x1*a+b; x2=x2*a+b; x3=x3*a+b; x4=x4*a+b; x5=x5*a+b; x6=x6*a+b; x7=x7*a+b;\n"
"  }\n"
"  out[gid] = x0^x1^x2^x3^x4^x5^x6^x7;\n}\n";
int main(void){
  id<MTLDevice> dev = MTLCreateSystemDefaultDevice(); NSError *err = nil;
  id<MTLLibrary> lib = [dev newLibraryWithSource:[NSString stringWithUTF8String:SRC] options:[MTLCompileOptions new] error:&err];
  id<MTLComputePipelineState> pso = [dev newComputePipelineStateWithFunction:[lib newFunctionWithName:@"imad"] error:&err];
  id<MTLCommandQueue> cq = [dev newCommandQueue];
  uint32_t threads = 1 << 20, iters = 20000;
  id<MTLBuffer> bo = [dev newBufferWithLength:threads * 4 options:MTLResourceStorageModeShared];
  id<MTLBuffer> bi = [dev newBufferWithBytes:&iters length:4 options:MTLResourceStorageModeShared];
  for(int rep = 0; rep < 4; rep++){
    struct timespec t0, t1; clock_gettime(CLOCK_MONOTONIC, &t0);
    id<MTLCommandBuffer> cb = [cq commandBuffer]; id<MTLComputeCommandEncoder> en = [cb computeCommandEncoder];
    [en setComputePipelineState:pso]; [en setBuffer:bo offset:0 atIndex:0]; [en setBuffer:bi offset:0 atIndex:1];
    [en dispatchThreads:MTLSizeMake(threads, 1, 1) threadsPerThreadgroup:MTLSizeMake(256, 1, 1)];
    [en endEncoding]; [cb commit]; [cb waitUntilCompleted];
    clock_gettime(CLOCK_MONOTONIC, &t1);
    double dt = (t1.tv_sec - t0.tv_sec) + 1e-9 * (t1.tv_nsec - t0.tv_nsec);
    double ops = (double)threads * iters * 8;
    printf("rep %d dt %.4f s  IMAD/s %.3e  (gpu cores %s)\n", rep, dt, ops / dt, [[dev name] UTF8String]);
  }
  return 0;
}
