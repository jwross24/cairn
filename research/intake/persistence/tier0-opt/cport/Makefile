CC=clang
CFLAGS=-O2 -std=gnu11 -Wall -Wextra -Wno-unused-parameter -Wno-unused-variable -I/opt/homebrew/include
cport: cport.c
	$(CC) $(CFLAGS) -o cport cport.c -L/opt/homebrew/lib -lgmp -lm
