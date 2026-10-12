verify(p,a,b,n,Px,Py,Qx,Qy,x)=
{
  my(E = ellinit([a, b], p), P = [Px, Py], Q = [Qx, Qy]);
  if(ellmul(E, P, x) == Q, print("FAIL ", ["xP-ne-Q"]); quit(1));
  print("FAIL ", ["P-off-curve"]);
  quit(1);
}
