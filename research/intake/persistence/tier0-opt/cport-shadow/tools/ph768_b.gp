default(parisizemax, 1000000000);
N256 = 10^128+1; N768 = 10^256-10^128+1;
sm256 = [257,15361,453377]; sm768 = [434689,859393];
c256 = N256/prod(i=1,#sm256,sm256[i]); c768 = N768/prod(i=1,#sm768,sm768[i]);
print("Phi256 cofactor: ", #digits(c256), " digits, ispseudoprime=", ispseudoprime(c256));
print("Phi768 cofactor: ", #digits(c768), " digits, ispseudoprime=", ispseudoprime(c768));
foreach(concat(sm256,sm768), p, f = factor(p-1); print("p=", p, " order10=", znorder(Mod(10,p)), " p-1 = ", f, "  eligible level: ", if(Mod(10,p)^768==1 && Mod(10,p)^384!=1, "768-new", "other")));
