default(parisizemax, 2000000000);
N256 = 10^128+1;
N768 = 10^256-10^128+1;
print("Phi256 check: ", polcyclo(256,10)==N256, " Phi768 check: ", polcyclo(768,10)==N768);
f = factor(N256, 10^9); print("Phi256(10) partial: ", f);
f = factor(N768, 10^9); print("Phi768(10) partial: ", f);
