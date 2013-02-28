#include <stdio.h>
#include <stdlib.h>
#include <signal.h>

int main(int argc,
	 char ** argv)
{
  raise(SIGABRT);

  return 0;
}

