#include <stdio.h>
#include <stdlib.h>
#include <signal.h>

int main(int argc,
	 char ** argv)
{
#ifndef _WIN32
  raise(SIGKILL);
#endif

#ifdef _WIN32
  raise(SIGTERM);
#endif

  return 0;
}

