/* gsimII kernel main file v1.0
 * maintained by g.winter
 * 15th august 2000
 * 
 * based on tclAppInit.c
 * 
 * Copyright (c) 1993 The Regents of the University of California.
 * Copyright (c) 1994 Sun Microsystems, Inc.
 *
 */

#include "tcl.h"
#include "mpsa_export.h"

#ifdef I386DEBUG
  #include <fenv.h>
#endif

extern int matherr();
int *tclDummyMathPtr = (int *) matherr;

/* Mpsa routine, calls Tcl_Main which does all of the work and 
 * never returns.
 */

int main(
  int argc, 
  char **argv
)
{

  #ifdef I386DEBUG
    fesetenv(FE_INVALID);
  #endif

  mpsa_TclMain(argc, argv, Tcl_AppInit);
  return 0;
}

/* Initialisation routine, similar to that in loadable modules
 * run on startup to initialise mpsa commands and data structures. 
 */

int Tcl_AppInit(
  Tcl_Interp *interp
)
{
  if(Tcl_Init(interp) != TCL_OK) {
    return TCL_ERROR;
  }

  if(mpsa_Init(interp) != TCL_OK) {
    return TCL_ERROR;
  }

  return TCL_OK;
}
