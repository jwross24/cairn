# Lemma C blind re-implementation: results

Code: `lemma_c_blind.py` (this directory). Inputs: anchors.txt, DEEPCUT.md, OPEN-PATTERNS.md only.

## 1. Positive control

50 / 50 random genuine S-units y' = 2^a 3^b 7^c with >= 300 digits (a in [0,40], b in [0,700], c in [0,500])
placed in their own coset (b,c) + Lambda_96 survive the depth-1 (K=96) and depth-2 (K=192) cuts
made with their true lower digits (checked both chained 96 -> 192 and directly at K=192).

Enumeration control: synthetic y' with 6 pattern digits (two sharing a class) at copies 0/1/2: depth-1 case count 48 (expected 48), true y' mod 10^96 among the depth-1 L values: True; true y' mod 10^192 among depth-2 L values: True.

Discrete-log self test against sympy.discrete_log (mod 5^K) and direct power check (mod 2^K): passed. Coset-cut primitive brute-force checked on 200 random small cosets/congruences: passed.

## 2. Lambda_96

Primes used (all primes of 10^96 - 1 except 3 and 7; note 7 | 10^6 - 1 | 10^96 - 1, so 7 is a non-unit and was dropped, which can only enlarge the lattice = conservative): 11, 13, 17, 37, 73, 97, 101, 137, 353, 449, 641, 1409, 9901, 69857, 206209, 5882353, 99990001, 66554101249, 75118313082913, 9999999900000001

- index (determinant) = 280999509749509611991995562563818636457519792000000000000 = 2.809995e+56
- Gauss-reduced basis: (-5834300434592217394015440000, -5252227908597256497593760000), (24550795595028192589139040000, -26061931100684490688131840000)
- shortest vector length = 7.850157e+27
- every basis vector verified directly: 3^db 7^dc = 1 mod (10^96-1)/(27*7)

## 3. Per line (anchors.txt order)

| line | s | M | a | y | reps | depth-1 cases (distinct L) | depth-1 survivors | depth-2 cases (distinct L) | depth-2 survivors | result |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 6 | 23 | 2 | 111132 | 1 | 4 | 0 | 0 | 0 | CLOSED  |
| 2 | 12 | 223 | 1 | 13122 | 1 | 8 | 0 | 0 | 0 | CLOSED  |
| 3 | 12 | 223 | 2 | 111132 | 1 | 8 | 0 | 0 | 0 | CLOSED  |
| 4 | 24 | 2223 | 1 | 13122 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 5 | 24 | 2223 | 2 | 111132 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 6 | 48 | 22223 | 1 | 13122 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 7 | 48 | 22223 | 2 | 111132 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 8 | 162 | 2339 | 2 | 111132 | 2 | 24 | 0 | 0 | 0 | CLOSED  |
| 9 | 168 | 2267 | 4 | 27216 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 10 | 144 | 466 | 4 | 11664 | 1 | 8 | 0 | 0 | 0 | CLOSED  |
| 11 | 224 | 22247 | 3 | 122472 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 12 | 224 | 2447 | 1 | 71442 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 13 | 216 | 22239 | 2 | 111132 | 5 | 64 | 0 | 0 | 0 | CLOSED  |
| 14 | 216 | 2349 | 2 | 111132 | 1 | 12 | 0 | 0 | 0 | CLOSED  |
| 15 | 216 | 2366 | 2 | 111132 | 2 | 16 | 0 | 0 | 0 | CLOSED  |
| 16 | 216 | 2366 | 2 | 61236 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 17 | 216 | 3346 | 1 | 33614 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 18 | 378 | 23337 | 2 | 111132 | 2 | 24 | 0 | 0 | 0 | CLOSED  |
| 19 | 324 | 22339 | 1 | 13122 | 3 | 52 | 0 | 0 | 0 | CLOSED  |
| 20 | 324 | 22339 | 2 | 111132 | 3 | 64 | 0 | 0 | 0 | CLOSED  |
| 21 | 784 | 2778 | 6 | 1778112 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 22 | 1372 | 4777 | 0 | 177147 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 23 | 1176 | 3778 | 0 | 137781 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 24 | 1176 | 4677 | 3 | 1417176 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 25 | 1764 | 23677 | 3 | 1417176 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 26 | 2744 | 24777 | 0 | 177147 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 27 | 448 | 22447 | 1 | 71442 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 28 | 448 | 222247 | 3 | 122472 | 1 | 64 | 0 | 0 | 0 | CLOSED  |
| 29 | 192 | 2268 | 4 | 21168 | 1 | 8 | 0 | 0 | 0 | CLOSED  |
| 30 | 192 | 2348 | 2 | 111132 | 2 | 24 | 0 | 0 | 0 | CLOSED  |
| 31 | 192 | 2348 | 1 | 43218 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 32 | 192 | 2348 | 2 | 12348 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 33 | 192 | 2348 | 1 | 23814 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 34 | 192 | 2222223 | 1 | 13122 | 2 | 80 | 0 | 0 | 0 | CLOSED  |
| 35 | 192 | 2222223 | 2 | 111132 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 36 | 972 | 3669 | 4 | 3111696 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 37 | 972 | 333334 | 0 | 413343 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 38 | 972 | 233336 | 2 | 111132 | 1 | 12 | 0 | 0 | 0 | CLOSED  |
| 39 | 288 | 2466 | 4 | 11664 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 40 | 288 | 3446 | 0 | 531441 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 41 | 288 | 22338 | 2 | 111132 | 3 | 44 | 0 | 0 | 0 | CLOSED  |
| 42 | 288 | 22346 | 1 | 214326 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 43 | 43218 | 367777 | 3 | 1417176 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 44 | 43218 | 2337777 | 2 | 2333772 | 1 | 64 | 0 | 0 | 0 | CLOSED  |
| 45 | 896 | 222447 | 1 | 71442 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 46 | 896 | 2222247 | 3 | 122472 | 1 | 64 | 0 | 0 | 0 | CLOSED  |
| 47 | 648 | 2499 | 3 | 941192 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 48 | 648 | 233334 | 0 | 413343 | 2 | 96 | 0 | 0 | 0 | CLOSED  |
| 49 | 648 | 222339 | 1 | 13122 | 4 | 124 | 0 | 0 | 0 | CLOSED  |
| 50 | 648 | 222339 | 2 | 111132 | 4 | 160 | 0 | 0 | 0 | CLOSED  |
| 51 | 648 | 223336 | 2 | 111132 | 3 | 44 | 0 | 0 | 0 | CLOSED  |
| 52 | 672 | 222267 | 4 | 27216 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 53 | 672 | 2222237 | 2 | 111132 | 5 | 72 | 0 | 0 | 0 | CLOSED  |
| 54 | 672 | 222347 | 1 | 13122 | 4 | 84 | 0 | 0 | 0 | CLOSED  |
| 55 | 672 | 222347 | 2 | 111132 | 5 | 128 | 0 | 0 | 0 | CLOSED  |
| 56 | 432 | 33344 | 0 | 413343 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 57 | 432 | 33344 | 0 | 531441 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 58 | 432 | 23338 | 2 | 111132 | 1 | 12 | 0 | 0 | 0 | CLOSED  |
| 59 | 432 | 22366 | 1 | 13122 | 3 | 40 | 0 | 0 | 0 | CLOSED  |
| 60 | 432 | 22366 | 2 | 111132 | 3 | 44 | 0 | 0 | 0 | CLOSED  |
| 61 | 432 | 22366 | 2 | 61236 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 62 | 432 | 22349 | 1 | 13122 | 4 | 74 | 0 | 0 | 0 | CLOSED  |
| 63 | 432 | 22349 | 2 | 111132 | 2 | 48 | 0 | 0 | 0 | CLOSED  |
| 64 | 432 | 23346 | 1 | 33614 | 2 | 48 | 0 | 0 | 0 | CLOSED  |
| 65 | 432 | 23346 | 2 | 111132 | 2 | 32 | 0 | 0 | 0 | CLOSED  |
| 66 | 432 | 23346 | 1 | 214326 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 67 | 432 | 222239 | 1 | 13122 | 6 | 140 | 0 | 0 | 0 | CLOSED  |
| 68 | 432 | 222239 | 2 | 111132 | 7 | 156 | 0 | 0 | 0 | CLOSED  |
| 69 | 2268 | 33667 | 0 | 1361367 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 70 | 2268 | 23679 | 3 | 2571912 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 71 | 2268 | 223379 | 3 | 2571912 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 72 | 1792 | 4788 | 2 | 1411788 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 73 | 1792 | 22788 | 6 | 1778112 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 74 | 1792 | 24478 | 8 | 7112448 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 75 | 1792 | 2222447 | 1 | 71442 | 1 | 72 | 0 | 0 | 0 | CLOSED  |
| 76 | 1792 | 22222247 | 3 | 122472 | 1 | 64 | 0 | 0 | 0 | CLOSED  |
| 77 | 1344 | 4678 | 4 | 148176 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 78 | 1344 | 22678 | 2 | 67228 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 79 | 1344 | 22678 | 1 | 2117682 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 80 | 1344 | 2222267 | 4 | 27216 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 81 | 1344 | 22222237 | 1 | 13122 | 6 | 164 | 0 | 0 | 0 | CLOSED  |
| 82 | 1344 | 22222237 | 2 | 111132 | 7 | 172 | 0 | 0 | 0 | CLOSED  |
| 83 | 1344 | 2222347 | 1 | 13122 | 7 | 220 | 0 | 0 | 0 | CLOSED  |
| 84 | 1344 | 2222347 | 2 | 111132 | 7 | 320 | 0 | 0 | 0 | CLOSED  |
| 85 | 1944 | 23499 | 4 | 49392 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 86 | 1944 | 23499 | 4 | 34992 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 87 | 1944 | 23669 | 5 | 163296 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 88 | 1944 | 23669 | 2 | 236196 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 89 | 1944 | 23669 | 4 | 3111696 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 90 | 1944 | 2333334 | 2 | 111132 | 1 | 12 | 0 | 0 | 0 | CLOSED  |
| 91 | 1944 | 2333334 | 0 | 413343 | 1 | 64 | 0 | 0 | 0 | CLOSED  |
| 92 | 1944 | 2233336 | 1 | 13122 | 2 | 30 | 0 | 0 | 0 | CLOSED  |
| 93 | 1944 | 2233336 | 2 | 111132 | 2 | 48 | 0 | 0 | 0 | CLOSED  |
| 94 | 1944 | 22233333 | 2 | 111132 | 5 | 52 | 0 | 0 | 0 | CLOSED  |
| 95 | 1944 | 2223339 | 3 | 1134213192 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 96 | 864 | 222366 | 1 | 13122 | 4 | 90 | 0 | 0 | 0 | CLOSED  |
| 97 | 864 | 222366 | 2 | 111132 | 4 | 112 | 0 | 0 | 0 | CLOSED  |
| 98 | 864 | 222366 | 2 | 61236 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 99 | 864 | 223338 | 1 | 13122 | 2 | 30 | 0 | 0 | 0 | CLOSED  |
| 100 | 864 | 223338 | 2 | 111132 | 2 | 48 | 0 | 0 | 0 | CLOSED  |
| 101 | 864 | 233344 | 2 | 111132 | 2 | 24 | 0 | 0 | 0 | CLOSED  |
| 102 | 864 | 233344 | 0 | 413343 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 103 | 864 | 233344 | 0 | 531441 | 3 | 96 | 0 | 0 | 0 | CLOSED  |
| 104 | 864 | 2222239 | 1 | 13122 | 7 | 206 | 0 | 0 | 0 | CLOSED  |
| 105 | 864 | 2222239 | 2 | 111132 | 9 | 368 | 0 | 0 | 0 | CLOSED  |
| 106 | 864 | 222349 | 1 | 13122 | 7 | 264 | 0 | 0 | 0 | CLOSED  |
| 107 | 864 | 222349 | 2 | 111132 | 3 | 144 | 0 | 0 | 0 | CLOSED  |
| 108 | 864 | 223346 | 1 | 33614 | 3 | 108 | 0 | 0 | 0 | CLOSED  |
| 109 | 864 | 223346 | 1 | 13122 | 3 | 68 | 0 | 0 | 0 | CLOSED  |
| 110 | 864 | 223346 | 2 | 111132 | 3 | 84 | 0 | 0 | 0 | CLOSED  |
| 111 | 864 | 223346 | 1 | 214326 | 1 | 64 | 0 | 0 | 0 | CLOSED  |
| 112 | 864 | 2222336 | 2 | 111132 | 5 | 80 | 0 | 0 | 0 | CLOSED  |
| 113 | 864 | 2223334 | 0 | 413343 | 8 | 352 | 0 | 0 | 0 | CLOSED  |
| 114 | 23814 | 237799 | 2 | 111132 | 4 | 78 | 0 | 0 | 0 | CLOSED  |
| 115 | 23814 | 336779 | 6 | 3779136 | 1 | 64 | 0 | 0 | 0 | CLOSED  |
| 116 | 23814 | 336779 | 3 | 1417176 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 117 | 23814 | 23333377 | 2 | 111132 | 3 | 96 | 0 | 0 | 0 | CLOSED  |
| 118 | 6272 | 2222778 | 3 | 172872 | 2 | 192 | 0 | 0 | 0 | CLOSED  |
| 119 | 6272 | 2222778 | 6 | 1778112 | 3 | 216 | 0 | 0 | 0 | CLOSED  |
| 120 | 1411788 | 223777777 | 2 | 111132 | 2 | 48 | 0 | 0 | 0 | CLOSED  |
| 121 | 2117682 | 233777777 | 2 | 111132 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 122 | 8748 | 3333349 | 0 | 413343 | 2 | 144 | 0 | 0 | 0 | CLOSED  |
| 123 | 8748 | 2233399 | 1 | 13122 | 6 | 250 | 0 | 0 | 0 | CLOSED  |
| 124 | 8748 | 2233399 | 2 | 111132 | 6 | 336 | 0 | 0 | 0 | CLOSED  |
| 125 | 8748 | 2333369 | 2 | 111132 | 6 | 146 | 0 | 0 | 0 | CLOSED  |
| 126 | 8748 | 2333369 | 2 | 333396 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 127 | 1728 | 6668 | 3 | 518616 | 1 | 16 | 0 | 0 | 0 | CLOSED  |
| 128 | 1728 | 22689 | 4 | 268912 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 129 | 1728 | 24469 | 3 | 941192 | 2 | 48 | 0 | 0 | 0 | CLOSED  |
| 130 | 1728 | 23489 | 3 | 941192 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 131 | 1728 | 23489 | 4 | 314928 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 132 | 1728 | 23489 | 0 | 321489 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 133 | 1728 | 2222366 | 1 | 13122 | 5 | 200 | 0 | 0 | 0 | CLOSED  |
| 134 | 1728 | 2222366 | 2 | 111132 | 5 | 256 | 0 | 0 | 0 | CLOSED  |
| 135 | 1728 | 2222366 | 2 | 61236 | 2 | 96 | 0 | 0 | 0 | CLOSED  |
| 136 | 1728 | 2223338 | 1 | 13122 | 4 | 144 | 0 | 0 | 0 | CLOSED  |
| 137 | 1728 | 2223338 | 2 | 111132 | 3 | 144 | 0 | 0 | 0 | CLOSED  |
| 138 | 1728 | 22222239 | 1 | 13122 | 9 | 400 | 0 | 0 | 0 | CLOSED  |
| 139 | 1728 | 22222239 | 2 | 111132 | 10 | 720 | 0 | 0 | 0 | CLOSED  |
| 140 | 1728 | 2233344 | 1 | 13122 | 3 | 52 | 0 | 0 | 0 | CLOSED  |
| 141 | 1728 | 2233344 | 2 | 111132 | 3 | 64 | 0 | 0 | 0 | CLOSED  |
| 142 | 1728 | 2233344 | 0 | 413343 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 143 | 1728 | 2233344 | 0 | 531441 | 6 | 270 | 0 | 0 | 0 | CLOSED  |
| 144 | 1728 | 2222349 | 1 | 13122 | 10 | 472 | 0 | 0 | 0 | CLOSED  |
| 145 | 1728 | 2222349 | 2 | 111132 | 9 | 664 | 0 | 0 | 0 | CLOSED  |
| 146 | 1728 | 2222349 | 3 | 1134213192 | 2 | 128 | 0 | 0 | 0 | CLOSED  |
| 147 | 1728 | 22222336 | 1 | 13122 | 6 | 176 | 0 | 0 | 0 | CLOSED  |
| 148 | 1728 | 22222336 | 2 | 111132 | 7 | 192 | 0 | 0 | 0 | CLOSED  |
| 149 | 1728 | 2223346 | 1 | 33614 | 3 | 162 | 0 | 0 | 0 | CLOSED  |
| 150 | 1728 | 2223346 | 1 | 13122 | 6 | 210 | 0 | 0 | 0 | CLOSED  |
| 151 | 1728 | 2223346 | 2 | 111132 | 4 | 208 | 0 | 0 | 0 | CLOSED  |
| 152 | 1728 | 2223346 | 1 | 214326 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 153 | 1728 | 22223334 | 2 | 111132 | 5 | 80 | 0 | 0 | 0 | CLOSED  |
| 154 | 1728 | 22223334 | 0 | 413343 | 11 | 536 | 0 | 0 | 0 | CLOSED  |
| 155 | 71442 | 3336779 | 3 | 1417176 | 3 | 72 | 0 | 0 | 0 | CLOSED  |
| 156 | 71442 | 23333779 | 2 | 2333772 | 2 | 288 | 0 | 0 | 0 | CLOSED  |
| 157 | 71442 | 23333779 | 3 | 2571912 | 7 | 264 | 0 | 0 | 0 | CLOSED  |
| 158 | 32928 | 446777 | 1 | 57177414 | 1 | 64 | 1 | 2 | 2 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2086e+02  |
| 159 | 32928 | 267778 | 6 | 1778112 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 160 | 32928 | 267778 | 3 | 1417176 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 161 | 32928 | 2237778 | 4 | 1067311728 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 162 | 32928 | 2344777 | 5 | 1613472 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 163 | 8192 | 444448 | 2 | 63011844 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 164 | 8192 | 224888 | 2 | 28812 | 2 | 48 | 0 | 0 | 0 | CLOSED  |
| 165 | 8192 | 2244448 | 10 | 1741824 | 1 | 64 | 0 | 0 | 0 | CLOSED  |
| 166 | 8192 | 2244448 | 0 | 330812181 | 2 | 96 | 1 | 2 | 2 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2109e+02  |
| 167 | 8192 | 2244448 | 8 | 7112448 | 2 | 96 | 0 | 0 | 0 | CLOSED  |
| 168 | 8192 | 2224488 | 10 | 1741824 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 169 | 8192 | 2224488 | 2 | 142884 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 170 | 8192 | 2224488 | 8 | 7112448 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 171 | 8192 | 2224488 | 0 | 330812181 | 1 | 96 | 1 | 4 | 4 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2109e+02  |
| 172 | 8192 | 2224488 | 8 | 30118144 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 173 | 8192 | 222222288 | 2 | 28812 | 1 | 72 | 0 | 0 | 0 | CLOSED  |
| 174 | 8192 | 222222288 | 0 | 330812181 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 175 | 8192 | 22222488 | 1 | 52081218 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 176 | 8192 | 22222488 | 0 | 330812181 | 2 | 96 | 2 | 12 | 12 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2109e+02  |
| 177 | 8192 | 22224448 | 5 | 14521248 | 1 | 192 | 0 | 0 | 0 | CLOSED  |
| 178 | 8192 | 22224448 | 8 | 7112448 | 3 | 112 | 0 | 0 | 0 | CLOSED  |
| 179 | 8192 | 22224448 | 3 | 25412184 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 180 | 8192 | 2222222248 | 1 | 121522842 | 2 | 320 | 0 | 0 | 0 | CLOSED  |
| 181 | 8192 | 2222222248 | 7 | 224042112 | 1 | 192 | 0 | 0 | 0 | CLOSED  |
| 182 | 8192 | 222222448 | 1 | 121522842 | 1 | 384 | 0 | 0 | 0 | CLOSED  |
| 183 | 8192 | 222222448 | 5 | 14521248 | 3 | 256 | 0 | 0 | 0 | CLOSED  |
| 184 | 8192 | 222222448 | 3 | 25412184 | 3 | 256 | 0 | 0 | 0 | CLOSED  |
| 185 | 14112 | 227789 | 3 | 2571912 | 2 | 68 | 0 | 0 | 0 | CLOSED  |
| 186 | 14112 | 2226677 | 4 | 27216 | 3 | 80 | 0 | 0 | 0 | CLOSED  |
| 187 | 14112 | 2334477 | 1 | 71442 | 3 | 132 | 0 | 0 | 0 | CLOSED  |
| 188 | 14112 | 2234677 | 2 | 111132 | 8 | 384 | 0 | 0 | 0 | CLOSED  |
| 189 | 14112 | 2234677 | 4 | 27216 | 7 | 252 | 0 | 0 | 0 | CLOSED  |
| 190 | 14112 | 22223677 | 4 | 27216 | 3 | 88 | 0 | 0 | 0 | CLOSED  |
| 191 | 14112 | 22223677 | 3 | 1417176 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 192 | 14112 | 222223377 | 4 | 1037232 | 3 | 352 | 0 | 0 | 0 | CLOSED  |
| 193 | 14112 | 222223377 | 2 | 2333772 | 6 | 768 | 0 | 0 | 0 | CLOSED  |
| 194 | 14112 | 22233477 | 4 | 1037232 | 5 | 528 | 0 | 0 | 0 | CLOSED  |
| 195 | 14112 | 22233477 | 2 | 111132 | 16 | 602 | 0 | 0 | 0 | CLOSED  |
| 196 | 14112 | 22233477 | 3 | 122472 | 6 | 480 | 0 | 0 | 0 | CLOSED  |
| 197 | 14112 | 22233477 | 2 | 2333772 | 3 | 384 | 0 | 0 | 0 | CLOSED  |
| 198 | 14112 | 22233477 | 1 | 2722734 | 1 | 192 | 1 | 3 | 3 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2086e+02  |
| 199 | 111132 | 2367779 | 7 | 45177216 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 200 | 111132 | 23336777 | 3 | 1417176 | 5 | 224 | 0 | 0 | 0 | CLOSED  |
| 201 | 111132 | 22337779 | 1 | 13122 | 14 | 480 | 0 | 0 | 0 | CLOSED  |
| 202 | 111132 | 22337779 | 2 | 111132 | 12 | 476 | 0 | 0 | 0 | CLOSED  |
| 203 | 111132 | 223333777 | 2 | 133923132 | 2 | 384 | 0 | 0 | 0 | CLOSED  |
| 204 | 49392 | 447779 | 0 | 177147 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 205 | 49392 | 466777 | 0 | 177147 | 1 | 24 | 0 | 0 | 0 | CLOSED  |
| 206 | 49392 | 466777 | 3 | 1417176 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 207 | 49392 | 367778 | 0 | 137781 | 2 | 68 | 0 | 0 | 0 | CLOSED  |
| 208 | 49392 | 2266777 | 3 | 1417176 | 3 | 104 | 0 | 0 | 0 | CLOSED  |
| 209 | 49392 | 3344777 | 1 | 57177414 | 1 | 64 | 0 | 0 | 0 | CLOSED  |
| 210 | 49392 | 2247779 | 2 | 6377292 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 211 | 49392 | 2247779 | 3 | 2571912 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 212 | 49392 | 2247779 | 2 | 777924 | 1 | 96 | 1 | 3 | 3 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2056e+02  |
| 213 | 49392 | 2247779 | 0 | 177147 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 214 | 49392 | 2337778 | 6 | 1778112 | 2 | 72 | 0 | 0 | 0 | CLOSED  |
| 215 | 49392 | 22227779 | 2 | 6377292 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 216 | 49392 | 22227779 | 3 | 2571912 | 2 | 120 | 0 | 0 | 0 | CLOSED  |
| 217 | 49392 | 2346777 | 3 | 1417176 | 3 | 132 | 0 | 0 | 0 | CLOSED  |
| 218 | 49392 | 22334777 | 5 | 1613472 | 2 | 136 | 0 | 0 | 0 | CLOSED  |
| 219 | 214326 | 2377999 | 3 | 2571912 | 3 | 128 | 0 | 0 | 0 | CLOSED  |
| 220 | 214326 | 333333677 | 3 | 1417176 | 3 | 128 | 0 | 0 | 0 | CLOSED  |
| 221 | 214326 | 233333779 | 2 | 111132 | 21 | 839 | 0 | 0 | 0 | CLOSED  |
| 222 | 214326 | 233333779 | 2 | 2333772 | 2 | 480 | 0 | 0 | 0 | CLOSED  |
| 223 | 214326 | 233333779 | 3 | 2571912 | 4 | 324 | 0 | 0 | 0 | CLOSED  |
| 224 | 14336 | 47888 | 0 | 7411887 | 1 | 32 | 1 | 2 | 2 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2109e+02  |
| 225 | 14336 | 227888 | 0 | 78121827 | 1 | 64 | 1 | 2 | 2 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2109e+02  |
| 226 | 14336 | 22222788 | 6 | 1778112 | 3 | 384 | 0 | 0 | 0 | CLOSED  |
| 227 | 14336 | 22222788 | 2 | 1411788 | 1 | 32 | 0 | 0 | 0 | CLOSED  |
| 228 | 14336 | 2224788 | 2 | 28812 | 7 | 252 | 0 | 0 | 0 | CLOSED  |
| 229 | 14336 | 2224788 | 2 | 1411788 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 230 | 14336 | 2244478 | 1 | 71442 | 6 | 304 | 0 | 0 | 0 | CLOSED  |
| 231 | 14336 | 2244478 | 2 | 63011844 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 232 | 14336 | 2244478 | 2 | 161414428 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 233 | 14336 | 22244447 | 6 | 34012224 | 1 | 192 | 0 | 0 | 0 | CLOSED  |
| 234 | 14336 | 2222222278 | 6 | 1778112 | 2 | 64 | 0 | 0 | 0 | CLOSED  |
| 235 | 14336 | 2222222278 | 0 | 330812181 | 2 | 96 | 1 | 8 | 8 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2109e+02  |
| 236 | 14336 | 22224478 | 1 | 71442 | 14 | 524 | 0 | 0 | 0 | CLOSED  |
| 237 | 14336 | 22224478 | 3 | 122472 | 5 | 384 | 0 | 0 | 0 | CLOSED  |
| 238 | 14336 | 22224478 | 6 | 1778112 | 6 | 432 | 0 | 0 | 0 | CLOSED  |
| 239 | 14336 | 22224478 | 10 | 1741824 | 2 | 288 | 0 | 0 | 0 | CLOSED  |
| 240 | 14336 | 22224478 | 0 | 330812181 | 2 | 240 | 1 | 6 | 6 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2109e+02  |
| 241 | 14336 | 22224478 | 8 | 7112448 | 2 | 384 | 0 | 0 | 0 | CLOSED  |
| 242 | 14336 | 22224478 | 2 | 63011844 | 3 | 192 | 0 | 0 | 0 | CLOSED  |
| 243 | 14336 | 222224447 | 6 | 34012224 | 1 | 192 | 0 | 0 | 0 | CLOSED  |
| 244 | 14336 | 222222478 | 3 | 122472 | 9 | 680 | 0 | 0 | 0 | CLOSED  |
| 245 | 14336 | 222222478 | 6 | 1778112 | 4 | 240 | 0 | 0 | 0 | CLOSED  |
| 246 | 14336 | 222222478 | 0 | 330812181 | 4 | 240 | 2 | 18 | 18 | OPEN, shortest vector of finest surviving sub-coset = 10^1.2109e+02  |
| 247 | 14336 | 22222222247 | 3 | 122472 | 1 | 144 | 0 | 0 | 0 | CLOSED  |
| 248 | 14336 | 22222222247 | 7 | 224042112 | 2 | 384 | 0 | 0 | 0 | CLOSED  |
| 249 | 14336 | 2222222447 | 7 | 224042112 | 1 | 192 | 0 | 0 | 0 | CLOSED  |
| 250 | 14336 | 2222222447 | 6 | 34012224 | 1 | 192 | 0 | 0 | 0 | CLOSED  |
| 251 | 14336 | 2222222447 | 1 | 71442 | 1 | 216 | 0 | 0 | 0 | CLOSED  |
| 252 | 11664 | 3333449 | 0 | 413343 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 253 | 11664 | 3333449 | 0 | 531441 | 3 | 144 | 0 | 0 | 0 | CLOSED  |
| 254 | 11664 | 3333466 | 0 | 413343 | 2 | 112 | 0 | 0 | 0 | CLOSED  |
| 255 | 11664 | 3333466 | 6 | 5334336 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 256 | 11664 | 2333666 | 2 | 111132 | 6 | 98 | 0 | 0 | 0 | CLOSED  |
| 257 | 11664 | 2333389 | 2 | 111132 | 4 | 144 | 0 | 0 | 0 | CLOSED  |
| 258 | 11664 | 2223699 | 3 | 1134213192 | 1 | 96 | 0 | 0 | 0 | CLOSED  |
| 259 | 11664 | 2233499 | 1 | 13122 | 15 | 712 | 0 | 0 | 0 | CLOSED  |
| 260 | 11664 | 2233499 | 2 | 111132 | 9 | 528 | 0 | 0 | 0 | CLOSED  |
| 261 | 11664 | 2233669 | 1 | 13122 | 14 | 400 | 0 | 0 | 0 | CLOSED  |
| 262 | 11664 | 2233669 | 2 | 111132 | 12 | 464 | 0 | 0 | 0 | CLOSED  |
| 263 | 11664 | 2233669 | 2 | 61236 | 3 | 148 | 0 | 0 | 0 | CLOSED  |
| 264 | 11664 | 2233669 | 1 | 39366 | 1 | 72 | 0 | 0 | 0 | CLOSED  |
| 265 | 11664 | 2233669 | 2 | 236196 | 1 | 72 | 0 | 0 | 0 | CLOSED  |
| 266 | 11664 | 2233669 | 9 | 1229312 | 3 | 160 | 0 | 0 | 0 | CLOSED  |
| 267 | 11664 | 2333469 | 1 | 33614 | 8 | 410 | 0 | 0 | 0 | CLOSED  |
| 268 | 11664 | 2333469 | 2 | 111132 | 9 | 314 | 0 | 0 | 0 | CLOSED  |
| 269 | 11664 | 2333469 | 1 | 214326 | 3 | 200 | 0 | 0 | 0 | CLOSED  |
| 270 | 11664 | 2333469 | 2 | 333396 | 2 | 192 | 0 | 0 | 0 | CLOSED  |
| 271 | 11664 | 22223399 | 1 | 13122 | 18 | 904 | 0 | 0 | 0 | CLOSED  |
| 272 | 11664 | 22223399 | 2 | 111132 | 25 | 1576 | 0 | 0 | 0 | CLOSED  |
| 273 | 11664 | 22333349 | 3 | 941192 | 3 | 84 | 0 | 0 | 0 | CLOSED  |
| 274 | 11664 | 22333349 | 0 | 1594323 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 275 | 11664 | 22333349 | 0 | 413343 | 16 | 1376 | 0 | 0 | 0 | CLOSED  |
| 276 | 11664 | 2222333333 | 1 | 13122 | 5 | 192 | 0 | 0 | 0 | CLOSED  |
| 277 | 11664 | 2222333333 | 2 | 111132 | 5 | 240 | 0 | 0 | 0 | CLOSED  |
| 278 | 11664 | 222333336 | 2 | 133923132 | 1 | 256 | 0 | 0 | 0 | CLOSED  |
| 279 | 11664 | 22233369 | 2 | 111132 | 20 | 660 | 0 | 0 | 0 | CLOSED  |
| 280 | 11664 | 22233369 | 2 | 333396 | 4 | 352 | 0 | 0 | 0 | CLOSED  |
| 281 | 11664 | 222233339 | 5 | 6223392 | 1 | 192 | 0 | 0 | 0 | CLOSED  |
| 282 | 11664 | 222233339 | 2 | 133923132 | 1 | 384 | 0 | 0 | 0 | CLOSED  |
| 283 | 61236 | 3336679 | 0 | 1361367 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 284 | 61236 | 3336679 | 2 | 236196 | 2 | 60 | 0 | 0 | 0 | CLOSED  |
| 285 | 61236 | 3336679 | 4 | 3111696 | 2 | 120 | 0 | 0 | 0 | CLOSED  |
| 286 | 61236 | 333333347 | 0 | 413343 | 1 | 48 | 0 | 0 | 0 | CLOSED  |
| 287 | 61236 | 2336799 | 3 | 2571912 | 2 | 168 | 0 | 0 | 0 | CLOSED  |
| 288 | 61236 | 233333367 | 2 | 111132 | 8 | 240 | 0 | 0 | 0 | CLOSED  |
| 289 | 61236 | 22333799 | 4 | 1037232 | 3 | 312 | 0 | 0 | 0 | CLOSED  |
| 290 | 61236 | 22333799 | 3 | 472392 | 4 | 440 | 0 | 0 | 0 | CLOSED  |
| 291 | 61236 | 22333799 | 3 | 2571912 | 7 | 432 | 0 | 0 | 0 | CLOSED  |
| 292 | 61236 | 23333679 | 8 | 35271936 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 293 | 61236 | 2233333337 | 1 | 44471322 | 1 | 128 | 0 | 0 | 0 | CLOSED  |
| 294 | 61236 | 2233333337 | 4 | 1037232 | 6 | 400 | 0 | 0 | 0 | CLOSED  |
| 295 | 61236 | 2233333337 | 2 | 111132 | 15 | 318 | 0 | 0 | 0 | CLOSED  |
| 296 | 61236 | 223333379 | 3 | 1134213192 | 6 | 1040 | 0 | 0 | 0 | CLOSED  |
| 297 | 1166886 | 33677779 | 3 | 1417176 | 2 | 84 | 0 | 0 | 0 | CLOSED  |
| 298 | 1166886 | 233377779 | 2 | 2333772 | 7 | 1056 | 0 | 0 | 0 | CLOSED  |
| 299 | 1166886 | 233377779 | 3 | 2571912 | 9 | 592 | 0 | 0 | 0 | CLOSED  |

## 4. Totals

- lines: 299, representations: 975 (by wrap index k, value = y + k R_96: k=0: 729, k=1: 1, k=9: 245)
- CLOSED: 288
- surviving (OPEN): 11
- vertices with a surviving line: 8192, 14112, 14336, 32928, 49392

Survivors in detail:

- line 158: s=32928 M=446777 a=1 y=57177414: 1 representations
    - rep nu=7 digits=((4, 0), (4, 2), (6, 7), (7, 3), (7, 4), (7, 6)): depth-1 1/64 survive, depth-2 2/2 survive
        - copies=[0, 0, 0, 0, 0, 1]  log10(shortest vector)=1.2086e+02  log10(index)=2.4194e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 0, 0, 'inf']  log10(shortest vector)=1.2086e+02  log10(index)=2.4194e+02  anchor point in sub-coset: False
- line 166: s=8192 M=2244448 a=0 y=330812181: 2 representations
    - rep nu=6 digits=((2, 3), (2, 5), (4, 5), (4, 5), (4, 7), (4, 8), (8, 1)): depth-1 1/48 survive, depth-2 2/2 survive
        - copies=[0, 0, 1, 'inf', 0, 0, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 'inf', 0, 0, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
- line 171: s=8192 M=2224488 a=0 y=330812181: 1 representations
    - rep nu=4 digits=((2, 3), (2, 4), (2, 5), (4, 7), (4, 8), (8, 1), (8, 5)): depth-1 1/96 survive, depth-2 4/4 survive
        - copies=[0, 1, 0, 0, 0, 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 1, 0, 0, 0, 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 'inf', 0, 0, 0, 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 'inf', 0, 0, 0, 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
- line 176: s=8192 M=22222488 a=0 y=330812181: 2 representations
    - rep nu=5 digits=((2, 3), (2, 5), (2, 7), (2, 7), (2, 7), (4, 8), (8, 1), (8, 5)): depth-1 1/48 survive, depth-2 8/8 survive
        - copies=[0, 0, 0, 1, 'inf', 1, 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 1, 'inf', 1, 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 1, 'inf', 'inf', 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 1, 'inf', 'inf', 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 1, 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 1, 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 'inf', 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 'inf', 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
    - rep nu=5 digits=((2, 3), (2, 5), (2, 8), (2, 8), (2, 8), (4, 7), (8, 1), (8, 5)): depth-1 1/48 survive, depth-2 4/4 survive
        - copies=[0, 0, 0, 1, 'inf', 0, 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 1, 'inf', 0, 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 0, 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 0, 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
- line 198: s=14112 M=22233477 a=1 y=2722734: 1 representations
    - rep nu=5 digits=((2, 3), (2, 4), (2, 5), (3, 1), (3, 6), (4, 0), (7, 2), (7, 5)): depth-1 1/192 survive, depth-2 3/3 survive
        - copies=[0, 0, 1, 0, 0, 0, 0, 'inf']  log10(shortest vector)=1.2086e+02  log10(index)=2.4194e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 0, 0, 0, 1]  log10(shortest vector)=1.2086e+02  log10(index)=2.4194e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 0, 0, 0, 'inf']  log10(shortest vector)=1.2086e+02  log10(index)=2.4194e+02  anchor point in sub-coset: False
- line 212: s=49392 M=2247779 a=2 y=777924: 1 representations
    - rep nu=5 digits=((2, 1), (2, 5), (4, 0), (7, 3), (7, 4), (7, 5), (9, 2)): depth-1 1/96 survive, depth-2 3/3 survive
        - copies=[0, 1, 0, 0, 0, 'inf', 0]  log10(shortest vector)=1.2056e+02  log10(index)=2.4164e+02  anchor point in sub-coset: False
        - copies=[0, 'inf', 0, 0, 0, 1, 0]  log10(shortest vector)=1.2056e+02  log10(index)=2.4164e+02  anchor point in sub-coset: False
        - copies=[0, 'inf', 0, 0, 0, 'inf', 0]  log10(shortest vector)=1.2056e+02  log10(index)=2.4164e+02  anchor point in sub-coset: False
- line 224: s=14336 M=47888 a=0 y=7411887: 1 representations
    - rep nu=6 digits=((4, 5), (7, 0), (8, 1), (8, 2), (8, 6)): depth-1 1/32 survive, depth-2 2/2 survive
        - copies=[0, 0, 0, 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
- line 225: s=14336 M=227888 a=0 y=78121827: 1 representations
    - rep nu=7 digits=((2, 1), (2, 4), (7, 0), (8, 2), (8, 6), (8, 7)): depth-1 1/64 survive, depth-2 2/2 survive
        - copies=[0, 0, 0, 0, 0, 1]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 0, 0, 'inf']  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
- line 235: s=14336 M=2222222278 a=0 y=330812181: 2 representations
    - rep nu=6 digits=((2, 3), (2, 5), (2, 7), (2, 7), (2, 7), (2, 8), (2, 8), (2, 8), (7, 5), (8, 1)): depth-1 1/48 survive, depth-2 8/8 survive
        - copies=[0, 0, 0, 1, 'inf', 1, 'inf', 'inf', 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 1, 'inf', 1, 'inf', 'inf', 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 1, 'inf', 'inf', 'inf', 'inf', 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 1, 'inf', 'inf', 'inf', 'inf', 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 1, 'inf', 'inf', 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 1, 'inf', 'inf', 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 'inf', 'inf', 'inf', 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 0, 'inf', 'inf', 'inf', 'inf', 'inf', 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
- line 240: s=14336 M=22224478 a=0 y=330812181: 2 representations
    - rep nu=4 digits=((2, 3), (2, 4), (2, 5), (2, 5), (4, 7), (4, 8), (7, 5), (8, 1)): depth-1 1/96 survive, depth-2 6/6 survive
        - copies=[0, 1, 0, 1, 0, 0, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 1, 0, 'inf', 0, 0, 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 1, 0, 'inf', 0, 0, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 'inf', 0, 1, 0, 0, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 'inf', 0, 'inf', 0, 0, 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 'inf', 0, 'inf', 0, 0, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
- line 246: s=14336 M=222222478 a=0 y=330812181: 4 representations
    - rep nu=5 digits=((2, 3), (2, 5), (2, 5), (2, 7), (2, 7), (2, 7), (4, 8), (7, 5), (8, 1)): depth-1 1/48 survive, depth-2 12/12 survive
        - copies=[0, 0, 1, 0, 1, 'inf', 1, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 1, 0, 1, 'inf', 'inf', 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 1, 0, 'inf', 'inf', 1, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 1, 0, 'inf', 'inf', 'inf', 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 1, 'inf', 1, 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 1, 'inf', 1, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 1, 'inf', 'inf', 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 1, 'inf', 'inf', 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 'inf', 'inf', 1, 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 'inf', 'inf', 1, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 'inf', 'inf', 'inf', 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 'inf', 'inf', 'inf', 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
    - rep nu=5 digits=((2, 3), (2, 5), (2, 5), (2, 8), (2, 8), (2, 8), (4, 7), (7, 5), (8, 1)): depth-1 1/48 survive, depth-2 6/6 survive
        - copies=[0, 0, 1, 0, 1, 'inf', 0, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 1, 0, 'inf', 'inf', 0, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 1, 'inf', 0, 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 1, 'inf', 0, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 'inf', 'inf', 0, 1, 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False
        - copies=[0, 0, 'inf', 0, 'inf', 'inf', 0, 'inf', 0]  log10(shortest vector)=1.2109e+02  log10(index)=2.4224e+02  anchor point in sub-coset: False

## 5. Observations

- Negative control (30 genuine S-units, one lower digit corrupted): depth-1 corruption at position 50: cut empty 0, true point excluded 30, true point kept 0; depth-2 corruption at position 150: cut empty 0, true point excluded 30, kept 0.
- Image of Lambda_96 in (Z/5^96)^*: order 5^91, index 2500 = {2: 2, 5: 4}; in (Z/2^96)^* (a=0): order 2^87, index 256 = {2: 8}; joint index in G_96 = 640000 (so a random target survives a depth-1 case with probability about 1.6e-06; DEEPCUT says ~1e-6).
  Consequence: the depth-1 verdict depends only on L mod 5^5 and L mod 2^9 (times the Z/4 and sign parts), i.e. on the pattern digits at positions below ~9 and their copy choice; higher digits only move the surviving sub-coset.
- Image of the depth-1 sublattice in the kernel U of G_192 -> G_96: order 1.000e+96 vs |U| = 1.000e+96 (ratio 1.000). The depth-2 congruences therefore never exclude a depth-1 survivor (every depth-2 extension of every depth-1 survivor survived in the run above, and a corrupted digit at position 150 moves but never empties the coset); depth 2 only refines the lattice by |U| ~ 10^96, i.e. raises the bound by ~10^48, exactly as DEEPCUT.md describes.
- 7 divides 10^96 - 1 (7 | 10^6 - 1), contrary to the task statement; it was dropped from Lambda_96 (non-unit). The resulting index 2.81e56 and shortest vector 7.85e27 match DEEPCUT.md, so the original did the same. Dropping it is conservative (the exact coset for a 7-free anchor would even be 1-dimensional).
- Representation count: 975 here vs 964 in DEEPCUT.md (k = 0: 729, k = 1: 1, k = 9: 245). The 11 extra representations cannot be identified blind; none of them changes a verdict (all CLOSED/OPEN verdicts match the expected list). With k in {0, 1} only (OPEN-PATTERNS.md's statement) the count would be 730.

Total run time: 48 s (2 processes)
