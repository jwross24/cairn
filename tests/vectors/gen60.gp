setrand(1); p = randomprime([2^59, 2^60]); tries = 0;
while(1, a = random(p); b = random(p); if((4*a^3 + 27*b^2) % p == 0, next); tries++; E = ellinit([a,b], p); n = ellsea(E, 1); if(n && isprime(n), break));
if(ellcard(E) != n, error("confirm"));
P = random(E);
print("{\"bits\": 60, \"seed\": 1, \"p\": \"", p, "\", \"a\": \"", a, "\", \"b\": \"", b, "\", \"n\": \"", n, "\", \"P\": [\"", lift(P[1]), "\", \"", lift(P[2]), "\"], \"tries\": ", tries, ", \"origin\": \"author_supplied\", \"generator\": \"tests/vectors/gen60.gp\"}");
