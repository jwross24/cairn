# P1 small-numbers floor decision

**ADOPT for the frozen synthetic comparison; the recorded floor is unenforced.** The endpoint-100 false control completed its registered hunt with no counterexample and exact final wealth `(100/99)^100 < 20`. It is the single binding false survivor. This resource decision proves no mathematical statement and supplies no claim evidence, calibration promotion, or reward.

Calibration: **CONJECTURE for resource utility**. The recorded ADOPT outcome concerns this frozen comparison only.

The immutable quantitative criterion in [preregistration.json](preregistration.json) is ADOPT iff at least one completed SURVIVED planted-false hunt has final `E < 20`; otherwise DROP for this comparison. The stored decision preserves that exact criterion. MagentaSparrow ruling **#446** authorizes an experiment-only close with an explicitly unenforced decision and a separate wiring bead, despite the preregistration's wiring-before-close sentence. The ruling changes the closing scope only; epsilon, alpha, D, budgets, outcomes, and the quantitative decision are identical to the frozen registration.

The admission gap is tracked by **cairn-yrov**, “Wire the adopted P1 floor into Tier-2 proving admission,” blocked by **cairn-ziz**. The dispatcher has no typed Tier-2 proof-generation admission operation. `solutionchecks` verifies existing submissions; it does not admit proof creation. The decision record has `enforced=false` and gates no execution.

## Registered outcomes

All runs use `alpha=1/20`, threshold `1/alpha=20`, and predictable fixed maximum stake `lambda=1/(1-epsilon)`. Updates use exact rational arithmetic `E_next=E*(1-lambda*(X-epsilon))`. Only validated `SURVIVED_TRIAL` is `X=0`; only verified `COUNTEREXAMPLE` is `X=1`. Failed, unverified, over-budget, and INCOMPLETE results cannot supply clean admission. Decimal displays and numeric `log10E` are attributes only.

| Control and uniform D | epsilon | Completed / declared | Hunt | Exact final E; display |
|---|---:|---:|---|---|
| endpoint-100, n=0..99 | 1/100 | 100 / 100 | SURVIVED | `(100/99)^100`; 2.731999026429026 |
| endpoint-1000, n=0..999 | 1/1000 | 113 / 1000 | KILLED | `0` |
| endpoint-2000, n=0..1999 | 1/2000 | 900 / 2000 | KILLED | `0` |
| R4-euler, n=0..40 | 1/41 | 21 / 41 | KILLED | `0` |
| clean-1000, n=0..999 | 1/1000 | 3000 / 3000 | SURVIVED | `(1000/999)^3000`; 20.115707966900594 |

Endpoint controls assert that N does not divide n+1. Each full finite D has exactly one failure, so q=epsilon=1/N. Finite enumeration of Euler's `n*n+n+41` over 0..40 records its sole composite at n=40, where the value is 1681=41², establishing q=1/41 for this D. The clean control asserts n<=999 and has q=0 on its D. Both survivors remain CONJECTURE through ordinary hunt evidence; all three killed statements are SPECULATION. Each statement has one ordinary hunt tag-history entry. Floor results, reproductions, and the decision are outside `evidence_nodes`; tag, history, and `justified_by` are invariant across floor recording and reproduction.

There is **one fresh gate-owned nonce per control**, five registered runs total, with no tuned seeds, outcomes, distributions, or budgets. Hypothesis and protocol nodes precede gate entropy commitment, and the seed-bound run registration precedes trial input writes. [summary.json](summary.json) retains every declared seed, including 887, 1100, and 20 unused seeds in the three killed runs. The 3000-trial clean control is the only registered longer budget.

The study has 4134 completed trials and three counterexample-verifier executions: **4137 original executions, 4137 fresh uncached recipe reruns, and 8274 attempts/receipts**. All real reruns have passing reproducibility records. Executor and verifier source bytes and explicit dispatch settings are pinned in each recipe. Reproduction uses the original committed nonce and compares canonical substantive point/seed/X/E bytes, allowing fresh attempt IDs to differ. It is **not an independent second statistical sample**. There are no missing, failing, filtered, or skipped study cases. The recorded study command exits 0 under the 6 GiB memory cap; its recorded peak footprint is 0.08 GiB.

## Design limit

At completed false-control budgets N, clean maximum-stake wealth `(N/(N-1))^N` is near e and below 20. The floor can therefore deny a false control that survives this particular completed hunt. This single realization supports that binding observation only; it establishes no utility at other distributions, budgets, stakes, resource schedules, or mathematical families.

At budget 3N, clean maximum-stake wealth already exceeds 20. The exact first clean crossings are n=299 for N=100, n=2995 for N=1000, n=5990 for N=2000, and n=122 for N=41. Verified failures already kill the hunt. These exact arithmetic comparisons expose redundancy at 3/epsilon; they are derived calculations, not sampled findings or an in-repository Lean proof. The frozen sampled false budgets are N, not 3N.

## Provenance and replay

The executable source is commit `a4718e8f60303140b8138a76484b4d1359adc482`. Audit provenance resolves committed bytes with `git show`; concurrent working-tree changes do not redefine the study source. [manifest.json](manifest.json) records archive identities, the exact study command, memory-cap observation, and run/receipt counts. Runtime metadata records CPython 3.14.7, blake3 1.0.9, cairn 0.0.1, cypari2 2.2.4, and cysignals 1.12.6. Package versions are metadata, not a byte-level identity claim for third-party installations.

| Artifact | SHA-256 | Bytes |
|---|---|---:|
| summary.json | `64d2cb7c88b81e5017d381caec995c782b5f2e79322382b0d918e55f47cd799d` | 1844903 |
| substrate.sqlite.gz | `575fec45e4951f06ba2ead3f24664f0b9aa53c72bc3379488a3a3c39c4c36a9b` | 23763379 |
| uncompressed substrate.sqlite | `209f8bf1701a4ca1a83f16588d4e5a7803837c1a260676319032586a85b47183` | 119062528 |

The archive retains 24882 canonical nodes and 22693 blobs, with actual recipes, dispatch documents, attempts, receipts, claims, hunt records, all floor nodes, per-attempt reproducibility records, and lineage. Exact final wealth uses hexadecimal numerator/denominator encoding in the stored result; the transcript supports exact recomputation without decimal conversion limits.

Read-only artifact validation:

```bash
uv run python research/grounding/small-numbers-floor-2026-09-30/audit_study.py --artifact-dir research/grounding/small-numbers-floor-2026-09-30
```

[audit_study.py](audit_study.py) verifies archive byte identities, SQLite integrity, all content hashes, committed worker and sampler source identities, protocol/entropy/input order, all declared seed hashes, finite-control premises, real recipes/dispatch/output/receipt bindings, fresh rerun identities and reproducibility companions, exact X/E/threshold comparisons, decision lineage, and ordinary tag history. It opens SQLite read-only, recomputes recorded arithmetic and seed hashes, and creates no gate entropy, samples, worker executions, or substrate writes. Decompressed audit scratch is retained in a system temporary directory.

Common content hashes:

```text
study cbd7694de827b102d368bbf7c571ac81156537ee88f50d4a90a69bda784d8aee
runtime d2cd8aeaba05fd995e8fb37fdfd1449d6df0cac6f835108679feb7a8c4f1e4bf
decision 5c04ee8e4eb6e32de24782a51406c44cfed0accce3f3bfbafdea3904f5daf02a
preregistration raw BLAKE3 2c9720680665d7c6b14277a4b787f1afa8777ad3fd00e5841c26c09740720ce7
preregistration SHA-256 0eefc3c077b1a083039a53a005377922326c1b2ab8d50dfc8620cd1a1a290f3e
sampler source ce6504b5f7258c6f469b2540b217138c8c2bbad1d721af98c8d39a7fe5fccf2d
executor source 235de450a0cf51f7e3bfc5efb22151d07977a0dcbf495ae75f3213947f8521f5
verifier source dd30e5d58eb84d7a6f4b26d50b0a591809365d56ff652b5478f722b265056800
driver source cb738e0ce3ed590f1739f59485d80f12cadc6ebfd1f60f1f2a70b05fa45e5c67
interpreter bytes 382a68b9d132dc9d2b880c52669eebeb74e2d51b5d7dc117ce5e8ee53cdc4f37
```

The following hashes bind each statement, stable hypothesis, plan, protocol, run registration, entropy commitment, actual hunt, ordinary hunt evidence, floor result, and reproduction. The complete seed and trial transcripts are in the linked summary and substrate.

```text
endpoint-100
nonce 57c8c920567f9044ebe58a4ec1d4ab847695471448c4765e68ee87fc870ab493
statement 2c8dec35d0c3b0e201b191af48c52fee8133a5d653cf4226044b6894f184d967
hypothesis d00d794f8ec3da2c3f7cd0877964e000da64ddf6b34458d950a535a54dea4734
plan 643ee8b851a3c9ecfd28f3d268f339babd880476edb1ccb623634f987b28d2e4
protocol ae32e4cea68a9ebe1e9f9ca5bd2bc427acd0f536015e520e6e7cdb45e0276745
registration d79633f6c5fad6f5dbc5bdee4f0bf15df48117b94b7fb04c86b7931a9acfceb8
commitment 2d5619d66991dc0c385acc0ad8dd479756b2cda5b255548f14c3652caf4a09a9
hunt 5ff3d8702014ccec694cec900c7ac2d2f93df2872fb3c097284e6de32b7b2a43
hunt evidence c159cc878312e614770caee6bd588df7c74b5dddeb3702af339b06fa88183b6c
floor 33ff2efa23c6b93e364a721be13fe7c8777ca6a4b03d0f3ded45cb9110509c38
reproduction 803c2d22f0cf5fbc353153fa8ec58f653954613a4b86a84c44687eeaf32067f9

endpoint-1000
nonce 408948fcf24e5b197092439fd23388e5247284852438f63049b808904fad16e2
statement 4af5e40a1e530d48f7ede5564003caf29374a1ca322b89302bf9c4ee96a03e70
hypothesis 38500504d6adda7269d51049ad90b79ae19ee94ffe37135560d9b448c9bc6c3c
plan 53acab230dd0e34662e81778f576fc26ec007f02888d1d562b1cee6f406d01b6
protocol a9904e76acd93bcae8b2290c944f33f8f5503a96f377b1e091bc04bae93deb86
registration a093dec678703246015963fe498d6e15c71a7c679b13c0460ccb35fa2f02224a
commitment ea191fb8e5ee3b2c7c07295089491d0be17b6b35445882fe83781c754c0508f8
hunt bd6f0fdd554855b615a0c1e8f6d991f4ada779adc34fd5175505d60025bea388
hunt evidence a0ef7c97d9ddecb08bc99ad1b2429311b7aad82537c12d928d76bed0407efad1
floor 58099aadb2d8c1852312a12310682da5e68b79d688579fdd24ea56ea0abd2da7
reproduction 426ccd94c277fec5e752739db8696384ab022a81e33a71b25567629332f7fe14

endpoint-2000
nonce eda2e0489778fa9e2e31718a234517dcf11b61b607c4569ac015f72a2dc9b8f3
statement f61cf8731e8c93334af2116997bbf489ba6844d1a6007ea7131b7c8ada6e18b7
hypothesis d66b354c324eec326d69552a44de45796ec20f2f7872ecf587ea43a3d186a83a
plan 0ff15b259db755a2a18190af1edf88a5b11098a5d30f9863a70d55188098d5e2
protocol 452743cd92ba47162ef625cb18d6a179dbcece860ae440d3573d74791d8435de
registration cd517e67a10af33056b3fb727ae656790b6e2c7684e4368d5ba6172819f3bffb
commitment f575f601e8a4474d6287a453eea6e01e306e4880403b6ac381c41a667c5c531d
hunt e3bc377f59edd249859bced622c28ba1b6def5e96d3d0c6419bc2988a7116c75
hunt evidence 8a086b45f4269d9b48c5f6ca300d2f1d042857b6fdd982661e4adaa8048bc4c7
floor 164056e5ec4b63e82b2b6701acaae98575699c2838dafedf7b6a3508cf826261
reproduction 1d303b91a8c21e6d7b2d4c91eee03de7b4d7acf8f2c2f08e8a2e983f0c6a963c

R4-euler
nonce 63d2d06fb613b67714d19347e04dbbc4f1f501528ff81c7512bb608ab5993b1d
statement 3a434c227f1ffcf32d27c9968bdef488f72cfc1b1b8eff1c63590abe779a40cd
hypothesis a24c7390dbf30aab056e563243feb3b9a5d37f01157f17e3e7ed54363d6d66b5
plan 3373761220353a2e63e0b6a06e794df07859a1ac45de3763cc83dab3cbf9a792
protocol a19e7ec519e7c69f5a6b76a01433b6e00547b4d4b8cc35630b3eb87fe7144e40
registration 4979ab98a1b4f919840afa8fd47493656c43bb28c238b418a8e344b98790411c
commitment c8bc1c46c631509b1ab98464bd2f0a6d6047df8c3da7057d21ce1517e05edeb5
hunt c415c72790cfe566e2c0a5c2975089c5f519f0589dd1960417cdcf30c0233cc6
hunt evidence ba7c9829b57d6fcf598aeed7dc0133cacf284432418335aead71169fd4f6ebe7
floor 1380ba8ff48ccbb624eebc2ab52a3fc72621d44bc4a115451ae6c92242a88bb3
reproduction dae53f73bbb393fcf8c34d50a64d3ce15ec3717f2257b4a45488f5c03fd7afee

clean-1000
nonce f80c33e45ca0c0e0703e2e92fae31c2de67e774c49ebc3178bf58555b84f4b0e
statement 04c71c668ed15e690b447b88cd0fb78d18264a3d470f1b6664baf87cdc78cfe4
hypothesis f7b1d540d6e9762fa8a01130ab3895aceb7c5ab2acde524ca5f15473ed089205
plan 461d1f4893755ca043d04a6db2cc160b68886f3de52cb4e05152f0515114bdf8
protocol 0a344ec42bdc645ede1b8df1627339de1234495888784daa03934dadc2f98359
registration 0dff3ede993dc979596291fe47b13bff013204a840ed2626aaa68e9bee83477b
commitment 63c1e1ef39d65d843be09fe00c6c45cfb4295b9f30fc82c664d81d569f4b1f9a
hunt 8c2bff6646c88228948494edf1c4befc6ccef31636a49b485d2d6d8901e602d1
hunt evidence 048711021791c4812cb0e108ba412cbbcb035d935c68ba39e4bbd895db57c2b7
floor f15847521d9a592996f61cddc90539ad596028385cd6d8e4f56c41bfc988dba5
reproduction cb6e6419e5737f330f0e4cc92cd7574584324c5e0212f84562c64b0597772b46
```
