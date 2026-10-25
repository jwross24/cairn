p = "RESULT.md"
s = open(p).read()
s = s.replace("354 of them are closed", "402 of them are closed")
s = s.replace("t-series s193", "s193")
s = s.replace("it is the 99th percentile, not the mean", "it sits near the 98.5th percentile (8 of 547 survivors cost 600 s or more), not at the mean")
open(p, "w").write(s)
