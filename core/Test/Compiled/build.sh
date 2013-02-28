#!/bin/bash
for program in EPAbrt EPBus EPKill EPSegv; do
    cc -o ${program} ${program}.c
done

# build the "missing shared library" example
# this does not work in a portable fashion yet - perhaps I need a pukka
# makefile?
cc -c EPLib2.c 
cc -c EPLib.c 
ld -o EPLib2.so EPLib2.o
ld -o EPLib EPLib.o EPLib2.so 
mv EPLib2.so EPLib2.os
