verify(p,a,b,n,Px,Py,Qx,Qy,x)=
{
  my(E, P, Q, r);
  if(!ispseudoprime(p), print("FAIL ", ["p-not-prime"]); quit(1));
  if(Mod(4*a^3 + 27*b^2, p) == 0, print("FAIL ", ["singular"]); quit(1));
  E = ellinit([a, b], p);
  P = [Px, Py];
  Q = [Qx, Qy];
  r = [];
  if(!ellisoncurve(E, P), r = concat(r, ["P-off-curve"]));
  if(!ellisoncurve(E, Q), r = concat(r, ["Q-off-curve"]));
  if(#r, print("FAIL ", r); quit(1));
  if(ellmul(E, Q, n) != [0], print("FAIL ", ["nQ-not-O"]); quit(1));
  if(ellmul(E, P, x) != Q, print("FAIL ", ["xP-ne-Q"]); quit(1));
  print("OK");
  quit(0);
}
crash_selftest(p,a,b)=
{
  ellcard(ellinit([a, b], p));
  print("OK");
  quit(0);
}
