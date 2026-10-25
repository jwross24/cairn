CC=clang
CFLAGS=-O2 -std=gnu11 -Wall -Wextra -Wno-unused-parameter -Wno-unused-variable -Wno-unused-function -I/opt/homebrew/include
cport_shadow: src/cport_shadow.c
	$(CC) $(CFLAGS) -o cport_shadow src/cport_shadow.c -L/opt/homebrew/lib -lgmp -lm
