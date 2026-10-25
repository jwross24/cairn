# Lift ideation round: results

Predictions: PREDICTIONS.md (registered 2026-10-21 15:19 EDT, md5 bf0e1215, unedited). Reference binary for every differential: tier0/lvlN
(md5 9f3da704, read-only); `lvlNf` is the same source with KT[512] (the one defect found, below). All CPU times are rusage CPU seconds at nice 10 on an
Apple M5 under load average 30-60 from other jobs. Every "identical" below is sha256 of the sorted output lines plus equal tail-dead/open/exact counters,
settled in `ldiff.py` (Python). No result here proves any vertex closed. Nothing was swapped; tier0/ and the engine are untouched.

Skills: modes-of-reasoning-project-analysis, idea-wizard and extreme-software-optimization were run in that order by one agent. The multi-agent audit protocol
of the first skill was not run (no swarm); each claim is instead settled by a differential against the production stage with a planted mutant, which is the
independent check available here. Claims that rest only on the model are labeled MODELED.

## Finding that outranks the candidates: production lvlN overruns KT on every equation with A >= 64

`tier0/lvlN.c` line 31 `static int KT[64]`; `read_cfg` reads KT[0..A]. Reproduction (exit 0): `uv run --no-project python repro_kt.py` (ASan build of the
production source reports global-buffer-overflow right after KT on h12/9437184_22222222222222222266, A = 64; the KT[512] source is clean).
Output impact, production vs KT[512] build (the join and GPU programs, built on KT[512], agree with the KT[512] build):

| equation | A | level | production OPEN / tail-dead | KT[512] OPEN / tail-dead |
|---|---|---|---|---|
| 9437184_22222222222222222266 | 64 | 24 | 2585 / 28859 | 2553 / 28891 |
| 9437184_22222222222222222266 | 64 | 48 | 2 / 17 | 0 / 19 |
| 9437184_222222222222222222229 | 67 | 24 | 929 / 9930 | 870 / 9989 |
| 9437184_222222222222222222229 | 67 | 48 | 0 / 14 | 0 / 14 |

Premise count in Tier B (`logs/tierb_A.jsonl`, 20 sampled multisets, min-k and max-k per vertex, sampling stopped when the exact two-adic bound became too slow):
A >= 64 on 14 of 14 sampled multisets with k >= 16 (A = 70-89) and A < 64 on 6 of 6 with k <= 11; 1,719 of 3,284 Tier B multisets (95.7% of level-12 patterns)
have k >= 16. Observation, not a proof for the unsampled ones. The Tier B lane's model assumed A = 40. Three equations in the
214-equation corpus have A >= 64 (two of them at level 48); no Tier A result was re-examined. In these four rows production over-reports OPEN (conservative); the direction is layout dependent, not guaranteed.
Proposed fix (not applied, needs the owner): KT[512] plus an `A >= 512` abort, as in `lvlNf.c` (two-line diff).

## Scoreboard (verdict is against the registered window or kill test)

| id | prediction | measurement (command / log) | verdict |
|---|---|---|---|
| A0 | N48 >= 60 | 214 equations (`ldiff.py 48 join48_clean.jsonl`) | HELD |
| A1 | join48 identical to lvlN on 100% | 213/214 vs production; the 214th is the KT equation above, where join48 equals the KT[512] reference (`kt_check.out`) | MISSED (reference defect) |
| A2 | >= 15 with open+exact >= 1, >= 40 with count >= 8 | 193 and 173 | HELD |
| A3 | M1' and M2 caught on every non-vacuous equation | M1' (drop odd K) 173/173; M2 (2^a to 1) 172/173; original M1 0/173 (K = 2 sets have no j%8 = 3 element) | KILLED as registered (1 equation), explained: 124416_33344489, a in {0,4}, key prime 17 with K = {1,-1} and 2^4 = -1, so M2 is an equivalent mutant under that key set; under forced key sets 1 and 2 it is caught (`verify_m2b.py`) |
| A4 | join48 speedup median 2.0 in [1.3, 4] | 1.92 (n = 8 equations with >= 1e6 children, range 1.36-5.82) | HELD |
| A5 | lvlN level-48 ns/child median 150 in [80, 300] | 117.7 (n = 8, k <= 21 only); model.py assumed 1000 | HELD |
| B1 | 3-way candidate sets equal to 2-way | cands equal and output identical on 60/60 (level 24), 56/57 (level 48; the 57th is the KT equation) | HELD |
| B2 | 3-way meet ops / 2-way median 3.0 in [1.2, 10] | 1.202 at level 24 (n = 60), 1.184 at level 48 (n = 9); CPU ratio 1.03 and 1.06 | HELD at 24 (edge), MISSED at 48 (edge); no gain either way |
| B2 slope | 3-way exponent in [0.5, 0.75]; the owner's 1/3 exponent is falsified if the slope exceeds 0.45 | d log(meet ops)/d log(C): 0.669 at 24, 0.481 at 48 (2-way: 0.707, 0.487) | owner's 2^{(k+1)/3} KILLED (slope far above 0.33; three lists are the two-list join with a lazily summed outer list) |
| C1 | kernel children/s 3e9 in [1e9, 1e10] | saturated: 1.6e9 (level 24, big prime first), 2.7e9 with the small-prime-first ordering (same 59,088 candidates), 1.09e10 (level 48, 1.3e9 children) | HELD at 24, MISSED at 48 (just above) |
| C2 | level 24 vs lvlN median 40 in [10, 200] | 18.8 (n = 40, range 6.6-68) | HELD |
| C3 | level 24 vs lvlJ join 2.5 in [0.7, 8]; kill if <= 1 | 1.97 CPU, 1.61 wall (n = 40) | HELD |
| C4 | level 48 vs lvlN 60 in [10, 400]; vs join48 8 in [1, 40] | median 4.6 over n = 9 equations with >= 1e6 children (MISSED: fixed GPU setup of ~0.05 s dominates); on the two equations with >= 1.7e8 children 150 and 166 vs lvlN, 27 and 29 vs join | MISSED at median, HELD at scale |
| C5 | identical on >= 20 equations per level; planted mutant caught on all non-vacuous | 40/40 at 24, mutant 40/40; at 48 213/214 (KT) , mutant 172/174 (two equations with count 8 and 10 missed) | HELD (identity), MISSED (mutant, 2 of 174) |
| D0 | zero rank-0 parents | 0 of 2.0e6 parents | HELD |
| D1 | <= 1% of C >= 1024 parents decided dead | 309 of 1,079,559 at level 24 (0.029%); 0 of 6,832 at level 48 | HELD, so the fast path is KILLED as a speedup (survival needed >= 10%) |
| D2 | < 0.1% of children in C <= 64 parents | 0% (0 of 4.65e9 at 24, 0 of 5.7e8 at 48) | HELD |
| D3 | differential identical; mutant caught | identical on 60/60 and 56/57; mutant "shift T*K by one" caught 20/60 and 1/57 (MISSED: it rarely changes a decision); mutant "invert the decision" caught 30/30 and 40/40 | HELD (identity), MISSED (M4) |
| E1 | max/median >= 3 of children per pattern at equal k | 1.3-2.0 per k for k = 7-13; log-residual max x2.2 (`adv_spread.py`) | MISSED |
| E2 | all-2s multiset >= 4x the law | high-k all-2s survivors per pattern (1.2e-4, 3.0e-4) sit on the k trend (x1.24 per digit, fit exp(-13.44 + 0.2148k)); no 4x residual | MISSED |
| E3 | one multiset >= 15% of its vertex; vertex >= 3x law | max 13.8% (vertex 13884223438848); vertex 1783627776 bootstrap p95 / point = 1.67 | MISSED |
| F1 | 1,500 GPU-h in [500, 10,000]; 4,000 USD in [1,300, 27,000] | 2,085 GPU-h; 5,600 USD at 2.69 (MODELED) | HELD |
| F2 | level 12 >= 50% of GPU-h; dual12 lowers total >= 2x | level 12 = 41% (846 of 2,085); dropping it lowers the total x1.7 | MISSED |
| F3 | wall on 8 GPUs in [60, 1,300] h | 261 h (10.9 days) | HELD |
| F4 | host <= 1,000 core-days, PCIe <= 5% | host 1,731 core-days at 3 us per level-12 survivor line, 11,961 at 25 us; PCIe 72 GPU-h equivalent (3.5%) if halves are shipped | MISSED (host), HELD (PCIe) |

## What was built and gated

- `lvlJ3.c`: the level-24/48 join of the Tier B lane (lvlJ.c) plus a stronger mutant (drop odd K), a three-list mode, and a parent-level decision mode, on the KT[512] source.
  Gate: join48 identical on 213/214 vs production and 214/214 modulo the KT equation; join24 identical on 100/100 (40 + 60 equations).
  Speedup vs lvlN (CPU seconds): level 24 median 9.2 (n = 40); level 48 median 1.92 (n = 8 with >= 1e6 children).
- `lvlG.c` + `gpu.m`: Metal prefilter. The CPU forms the two half lists; the GPU tests, for every child, the coset-membership of two key primes (bitmaps of K, Shoup
  multiplication by T^-1) and emits candidate indices; the CPU runs the unchanged process_child. Sound by construction (necessary conditions). Identical on 40/40
  (level 24) and 213/214 (level 48, the 214th being the KT equation); planted mutant caught 40/40 and 172/174.
  End to end vs lvlN: level 24 median 18.8x; level 48 150-166x on the two largest equations. Limits: the saturated kernel (2.7e9 children/s at 24, 1.09e10 at 48) is not
  the bottleneck at Tier A sizes; host half-list preparation is (5.5 us per parent at C = 2,870) and so is candidate verification (330-430 ns each at a 2.4e-3 candidate fraction at 48).
- Fast path (D), three-way join (B): built, gated, KILLED as speedups.

## Revised Tier B cost model

CPU, from `tierb-lift/model.py` re-run (command: `T_CHILD48=1.18e-7 T_CHILD24=2.81e-8 J48_GAIN=1.92 A_ASSUME=75 uv run --no-project --with sympy python model.py`, MODELED, laws extrapolated from k <= 21):
default parameters reproduce reference 4.49e4 and mixed (dual12 + join24 + join48) 5.29e3 Mac-days at 2 cores, not the 1.8e3 quoted by the lane (not reconciled);
with measured parameters reference 3.25e4 and mixed 1.87e3 Mac-days. The join48 term fell from 8.4e3 to 1.55e3 core-days because the model's 1 us per child is 8.5x the measured 118 ns (and the join gain 1.92, not 3).

GPU (`model_cuda.py`, MODELED): H100 SXM5 80 GB, 16.7e12 IMAD/s published peak (33.5 INT32 TOPS counting an IMAD as two ops, NVIDIA Hopper whitepaper table); this M5 measures 1.0e12 IMAD/s
(`imad.m`), scale 16.7x; efficiency 0.6 of the M5 kernels' efficiency (unmeasured on CUDA; 0.4-1.0 tested). Measured M5 inputs: level-12 kernel 1.3e10 patterns/s (documented
in COORDINATION 2026-10-20 15:40; re-run end to end gives 2.1e9/s on 3.6e8 patterns with 0.14 s setup, consistent), prefilter 2.7e9 (24) and 1.09e10 (48) children/s, candidate fractions 3.4e-5 and 2.44e-3.
Rate 2.69 USD/GPU-h (RunPod community H100 SXM; Vast median 2.07, Lambda 8x 3.99; page dated 2026-10-18).

| item | value |
|---|---|
| level 12 (brute force, 3.97e17 patterns) | 846 GPU-h |
| lift 12-24 (brute force prefilter, 1.2e17 children) | 1,233 GPU-h |
| lift 24-48 (2.2e15 children) | 6 GPU-h |
| total, nominal | 2,085 GPU-h = 5,600 USD = 261 h on 8 GPUs |
| band (judgment) | 1,100-6,000 GPU-h; 2,300-24,000 USD (efficiency 0.4-1.0, law-refit bootstrap p5-p95 1,980-3,110, plus an allowance for extrapolating k = 22-29 from six points at k >= 15) |
| host | candidates about 80 core-days; half-list preparation about 250 (3.2 us + 0.022 us per half-list entry per parent, fitted on two measured points); level-12 survivor stream 4.0e13 lines is the uncontrolled term: 1,700 core-days at 3 us per line, 12,000 at 25 us. It must be consumed on the device (4.0e13 lines at 64 B is 2.6 PB). |
| PCIe | 6.5e15 B if half lists are shipped (72 GPU-h equivalent, overlappable); 1.5e14 B if only parent records are shipped and halves are built on the GPU |
| porting effort (estimate) | CUDA level 12 from the Metal kernel 5-10 engineer-days, prefilter + device-side parent handling + gates 10-20; the Metal level-12 kernel landed inside the 2026-10-20 13:55-15:40 window of the optimization campaign |

Per vertex (GPU-h, nominal): 71663616: 9; 226492416: 19; 1194891264: 14; 169869312: 22; 4182119424: 16; 1792336896: 20; 13884223438848: 127; 2113929216: 200;
1811939328: 280; 11329339392: 197; 4444263936: 138; 3699376128: 284; 1783627776: 760.
The GPU model does not use the join (halving children); a device-side join on the lift 12-24 would cut the 1,233 by up to the CPU join factor, and is unbuilt.

## Adversarial lane (MODELED, with measured inputs)

No single multiset is the killer: the most expensive one costs at most 13.8% of its vertex (vertex 13884223438848, k = 23) and 2.4% of vertex 1783627776. The
adversary is the budget, not a multiset. Vertex 1783627776 (N12 = 1.57e17, k up to 26) costs 760 GPU-h nominal (816 median, 1,267 at bootstrap p95; 1,900 at p95 with efficiency 0.4),
57% of an assumed 8 x 168 = 1,344 GPU-h budget (the owner gave none) and above it in the adverse case; all 13 total 1.55x that budget nominally. The sampled measurements bound the law
only for k <= 21, where the residual spread across multisets is x2.2.

## Skill-surfaced ranking (impact x confidence / effort, only >= 2.0 acted on)

KT fix 5x5/1 = 25 (found, reproduced, not applied); measured t_child48 (free) 20; join24 as drop-in 4x5/2 = 10; GPU prefilter with device-side halves 5x3/4 = 3.8;
join48 on CPU 2x4/2 = 4; three-way 1x5/2 = 2.5 on paper, measured 1.0 so dropped; rank fast path 1x5/3 below threshold, dropped.

## Recommended next gated swap

1. KT[512] and the A >= 512 abort in tier0/lvlN.c (the only change; owner's go needed). Gate: ASan clean on both A >= 64 equations; byte-identical outputs on the 214-equation corpus for A < 64
   (sha256 per equation, settled in Python); gatev2 green; planted negative: an `A = 600` cfg must abort with exit 12.
2. Then join24 (`lvlJ3` with the join, no fast path, no three-way) for the 12-to-24 lift. Gate: identical on at least 200 equations including every A >= 64 equation, mutant M1' caught on every
   equation with count >= 8, mutant M2 caught under every forced key set, and `JOIN_FORCE_SET` sweep identical; expected CPU gain x9 (level 24).
   Join48 is worth x1.9 and only after (2) holds; the GPU prefilter is a build item (CUDA), not a swap.

Files (all under tier0-opt/math/lift-ideation/): PREDICTIONS.md, RESULT.md, lvlJ3.c, lvlJ3m5.c, lvlG.c, gpu.m, gpu.h, lvlNf.c, ldiff.py, repro_kt.py, kt_check.py, verify_m2.py, verify_m2b.py,
model_cuda.py, measured.json, adv_*.py, summ*.py, imad.m, sat_bench.py, lvl12_bench.py, logs/ (join48_clean, gpu48_clean, gpu24_top, fp_way3_24, fp_way3_48, fp_m5_*, kt_check.out, tierb_A.jsonl).
Logs named *_RACE_* were produced while two drivers shared an output path; they are kept, not used, and the clean reruns replace them.
