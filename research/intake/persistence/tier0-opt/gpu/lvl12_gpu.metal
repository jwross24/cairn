#include <metal_stdlib>
using namespace metal;

// Constants (NG, INNER, NB, MBi, TGRi, FOFFi, TOFFi, CH, TGSZ, ...) are prepended by the host.

constant uint NGR[NG] = {NGR_INIT};
constant uint GOFF[NG] = {GOFF_INIT};
constant uint GDIG[NG] = {GDIG_INIT};
constant uint CNTM[10] = {CNTM_INIT};
constant uint CISF[NC] = {CISF_INIT};
constant uint CPOS[NC] = {CPOS_INIT};
constant uint CMASK[NC] = {CMASK_INIT};
constant uint RVOFF[NC] = {RVOFF_INIT};
constant uint RVMOFF[NC] = {RVMOFF_INIT};
constant uint BMOFF[NC] = {BMOFF_INIT};
constant uint P2A[ATAB] = {P2A_INIT};
constant uint T3[100] = {T3_INIT};
constant uint T7[100] = {T7_INIT};

typedef LTYPE LT;
struct Params { uint chunk_lo; uint pad; };

struct Ctr { uint split, td, open, exact; };

inline uint decode_outer(uint outer, thread uint* mi) {
    uint rem = outer;
    const uint nu = NU_LO + rem % NUN;
    rem /= NUN;
    for (uint g = 0; g < NG; g++) {
        mi[g] = 0;
        if (g == INNER) continue;
        mi[g] = rem % NGR[g];
        rem /= NGR[g];
    }
    return nu;
}

inline void tail_one(uint sum, uint tsum, uint outer, uint inner_idx, thread Ctr& ct,
    device const LT* rvt, device const uchar* rvm, device const uchar* gmask,
    device atomic_uint* nrec, device uint* recs)
{
    uint mi[NG];
    const uint nu = decode_outer(outer, mi);
    uint idxs[NC];
    uint rs = 0;
    for (uint c = 0; c < NC; c++) {
        idxs[c] = CISF[c] ? ((sum >> CPOS[c]) & CMASK[c]) : ((tsum >> CPOS[c]) & CMASK[c]);
        rs += (uint)rvm[RVMOFF[c] + idxs[c]];
    }
    const uint r0 = rs % (uint)GG;
    if (r0 > (uint)AMAX) return;
    LT V0 = 0, V1 = 0, V2 = 0;
    for (uint c = 0; c < NC; c++) {
        device const LT* rp = rvt + RVOFF[c] + idxs[c] * 3;
        V0 += rp[0]; V1 += rp[1]; V2 += rp[2];
    }
    uint lm[10];
    for (uint d = 0; d < 10; d++) lm[d] = 0;
    for (uint g = 0; g < NG; g++) {
        uint m = (g == INNER) ? inner_idx : mi[g];
        lm[GDIG[g]] = gmask[GOFF[g] + m];
    }
    for (LT a0 = (LT)r0; a0 <= AMAX; a0 += GG) {
        LT k = (a0 - V0) / GG;
        LT b = V1 + k * U1;
        LT c = V2 + k * U2;
        ct.split++;
        uint bm = (uint)(((b % 100) + 100) % 100);
        uint cm = (uint)(((c % 100) + 100) % 100);
        uint Y = ((P2A[(uint)a0] * T3[bm]) % 1000u * T7[cm]) % 1000u;
        uint dg[3] = {Y % 10u, (Y / 10u) % 10u, Y / 100u};
        uint nY = Y >= 100u ? 3u : (Y >= 10u ? 2u : (Y > 0u ? 1u : 0u));
        bool ex = false;
        if (Y >= 10u && ((nY + NYOFF) % L) == (nu % L)) {
            uint have[10];
            for (uint d = 0; d < 10; d++) have[d] = 0;
            bool okx = true;
            for (uint i = 0; i < nY; i++) {
                uint d = dg[i];
                if (d == 0) { okx = false; break; }
                if (d == 1) continue;
                have[d]++;
                if (have[d] > CNTM[d]) { okx = false; break; }
                if (((lm[d] >> i) & 1u) < 1u) { okx = false; break; }
            }
            if (okx) { for (uint d = 2; d <= 9; d++) if (have[d] != CNTM[d]) okx = false; }
            ex = okx;
        }
        bool op = true;
        {
            uint have[10];
            for (uint d = 0; d < 10; d++) have[d] = 0;
            for (uint i = 0; i < 3; i++) {
                uint d = dg[i];
                if (d == 0) { op = false; break; }
                if (d == 1) continue;
                have[d]++;
                if (have[d] > CNTM[d]) { op = false; break; }
                if (((lm[d] >> (i + OPENSH)) & 1u) < 1u) { op = false; break; }
            }
        }
        if (ex) ct.exact++;
        if (op) ct.open++;
        if (!ex && !op) ct.td++;
        if (ex || op) {
            uint slot = atomic_fetch_add_explicit(nrec, 1u, memory_order_relaxed);
            if (slot < RECCAP) {
                device uint* rc = recs + slot * 16;
                rc[0] = (uint)a0 | (nu << 8) | ((ex ? 1u : 0u) << 16) | ((op ? 1u : 0u) << 17);
                for (uint g = 0; g < NG; g++) rc[1 + g] = (g == INNER) ? inner_idx : mi[g];
                rc[11] = (uint)((ulong)b & 0xFFFFFFFFul);
                rc[12] = (uint)((ulong)b >> 32);
                rc[13] = (uint)((ulong)c & 0xFFFFFFFFul);
                rc[14] = (uint)((ulong)c >> 32);
                rc[15] = Y;
            }
        }
    }
}

kernel void lvl12k(
    constant Params& prm [[buffer(0)]],
    device const ushort* ytab [[buffer(1)]],
    device const uint* filt [[buffer(2)]],
    device const uint* taill [[buffer(3)]],
    device const uint* bmap [[buffer(4)]],
    device const LT* rvt [[buffer(5)]],
    device const uchar* gmask [[buffer(6)]],
    device const ushort* rtab [[buffer(7)]],
    device atomic_uint* cnt [[buffer(8)]],
    device atomic_uint* nrec [[buffer(9)]],
    device uint* recs [[buffer(10)]],
    device const uchar* rvm [[buffer(11)]],
    uint2 tgp [[threadgroup_position_in_grid]],
    uint tid [[thread_index_in_threadgroup]],
    uint lane [[thread_index_in_simdgroup]])
{
    threadgroup ushort st0[CH];
#if NB > 1
    threadgroup ushort st1[CH];
#endif
#if NB > 2
    threadgroup ushort st2[CH];
#endif
    threadgroup uint tg0[TGS0];
    threadgroup uint tg1[TGS1];
    threadgroup uint tg2[TGS2];
    threadgroup uint tbm[BMWORDS];
    threadgroup uint qsum[QCAP], qtsum[QCAP], qout[QCAP], qin[QCAP];
    threadgroup atomic_uint qn;
    threadgroup uint qcount;

    const uint ci = prm.chunk_lo + tgp.y;
    const uint ibase = ci * CH;
    #if PLANT == 6
    const uint len = min((uint)CH, (uint)(NINNER - ibase)) - 1;
#else
    const uint len = min((uint)CH, (uint)(NINNER - ibase));
#endif

    for (uint k = tid; k < len; k += TGSZ) {
        st0[k] = ytab[0 * YTOT + GOFF[INNER] + ibase + k];
#if NB > 1
        st1[k] = ytab[1 * YTOT + GOFF[INNER] + ibase + k];
#endif
#if NB > 2
        st2[k] = ytab[2 * YTOT + GOFF[INNER] + ibase + k];
#endif
    }
#if TGR0
    for (uint k = tid; k < MB0; k += TGSZ) tg0[k] = filt[FOFF0 + k];
#endif
#if NB > 1 && TGR1
    for (uint k = tid; k < MB1; k += TGSZ) tg1[k] = filt[FOFF1 + k];
#endif
#if NB > 2 && TGR2
    for (uint k = tid; k < MB2; k += TGSZ) tg2[k] = filt[FOFF2 + k];
#endif
    for (uint k = tid; k < BMWORDS; k += TGSZ) tbm[k] = bmap[k];
    if (tid == 0) atomic_store_explicit(&qn, 0u, memory_order_relaxed);
    threadgroup_barrier(mem_flags::mem_threadgroup);

    const uint outer = tgp.x * TGSZ + tid;
    #if PLANT == 5
    const bool active = outer < OUTER_N && tid != 17;
#else
    const bool active = outer < OUTER_N;
#endif

    uint cpat = 0, czero = 0, cpre = 0;
    Ctr ct = {0, 0, 0, 0};

    uint s0 = 0, s1 = 0, s2 = 0;
    if (active) {
        uint mi[NG];
        const uint nu = decode_outer(outer, mi);
        s0 = rtab[0 * L + nu];
#if NB > 1
        s1 = rtab[1 * L + nu];
#endif
#if NB > 2
        s2 = rtab[2 * L + nu];
#endif
        for (uint g = 0; g < NG; g++) {
            if (g == INNER) continue;
            uint m = mi[g];
            s0 += ytab[0 * YTOT + GOFF[g] + m]; s0 = s0 >= MB0 ? s0 - MB0 : s0;
#if NB > 1
            s1 += ytab[1 * YTOT + GOFF[g] + m]; s1 = s1 >= MB1 ? s1 - MB1 : s1;
#endif
#if NB > 2
            s2 += ytab[2 * YTOT + GOFF[g] + m]; s2 = s2 >= MB2 ? s2 - MB2 : s2;
#endif
        }
        cpat = len;
    }

    for (uint jb = 0; jb < len; jb += JB) {
        const uint je = min(jb + (uint)JB, len);
        if (active) {
            for (uint j = jb; j < je; j++) {
                uint v0 = s0 + (uint)st0[j]; v0 = v0 >= MB0 ? v0 - MB0 : v0;
#if TGR0
                uint e0 = tg0[v0];
#else
                uint e0 = filt[FOFF0 + v0];
#endif
                uint zz = e0, sum = e0;
#if NB > 1
                uint v1 = s1 + (uint)st1[j]; v1 = v1 >= MB1 ? v1 - MB1 : v1;
#if TGR1
                #if PLANT == 4
                uint e1 = tg1[min(v1 + 1, (uint)MB1 - 1)];
#else
                uint e1 = tg1[v1];
#endif
#else
                uint e1 = filt[FOFF1 + v1];
#endif
                zz |= e1; sum += e1;
#endif
#if NB > 2
                uint v2 = s2 + (uint)st2[j]; v2 = v2 >= MB2 ? v2 - MB2 : v2;
#if TGR2
                uint e2 = tg2[v2];
#else
                uint e2 = filt[FOFF2 + v2];
#endif
                zz |= e2; sum += e2;
#endif
                const uint zf = zz >> 31;
                uint okm = 1;
                for (uint c = 0; c < NC; c++) {
                    if (CISF[c]) {
                        uint idx = (sum >> CPOS[c]) & CMASK[c];
                        okm &= (tbm[BMOFF[c] + (idx >> 5)] >> (idx & 31)) & 1u;
                    }
                }
                czero += zf;
                cpre += (zf ^ 1u) & (okm ^ 1u);
                if ((zf | (okm ^ 1u)) == 0u) {
                    uint tsum = taill[TOFF0 + v0];
#if NB > 1
                    tsum += taill[TOFF1 + v1];
#endif
#if NB > 2
                    tsum += taill[TOFF2 + v2];
#endif
                    uint slot = atomic_fetch_add_explicit(&qn, 1u, memory_order_relaxed);
                    if (slot < QCAP) {
                        qsum[slot] = sum; qtsum[slot] = tsum; qout[slot] = outer; qin[slot] = ibase + j;
                    } else {
                        tail_one(sum, tsum, outer, ibase + j, ct, rvt, rvm, gmask, nrec, recs);
                    }
                }
            }
        }
        threadgroup_barrier(mem_flags::mem_threadgroup);
        uint nq = min(atomic_load_explicit(&qn, memory_order_relaxed), (uint)QCAP);
        for (uint k = tid; k < nq; k += TGSZ)
            tail_one(qsum[k], qtsum[k], qout[k], qin[k], ct, rvt, rvm, gmask, nrec, recs);
        threadgroup_barrier(mem_flags::mem_threadgroup);
        if (tid == 0) atomic_store_explicit(&qn, 0u, memory_order_relaxed);
        threadgroup_barrier(mem_flags::mem_threadgroup);
    }

    cpat = simd_sum(cpat); czero = simd_sum(czero); cpre = simd_sum(cpre);
    uint csplit = simd_sum(ct.split), ctd = simd_sum(ct.td), copen = simd_sum(ct.open), cexact = simd_sum(ct.exact);
    if (lane == 0) {
        atomic_fetch_add_explicit(&cnt[0], cpat, memory_order_relaxed);
        atomic_fetch_add_explicit(&cnt[1], czero, memory_order_relaxed);
        atomic_fetch_add_explicit(&cnt[2], cpre, memory_order_relaxed);
        atomic_fetch_add_explicit(&cnt[3], csplit, memory_order_relaxed);
        atomic_fetch_add_explicit(&cnt[4], ctd, memory_order_relaxed);
        atomic_fetch_add_explicit(&cnt[5], copen, memory_order_relaxed);
        atomic_fetch_add_explicit(&cnt[6], cexact, memory_order_relaxed);
    }
}
