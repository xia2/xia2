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
  raise(SIGSEGV);
#endif

#ifdef _WIN32
  raise(EFAULT);
#endif

  return 0;
}

