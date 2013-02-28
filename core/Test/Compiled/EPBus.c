#include <stdio.h>
#include <stdlib.h>
#include <signal.h>

#ifdef _WIN32
#include <errno.h>
#endif

int main(int argc,
	 char ** argv)
{

#ifndef _WIN32
  raise(SIGBUS);
#endif

#ifdef _WIN32
  raise(EINVAL);
#endif

  return 0;
}

