/* gsimII mpsa particle movement commands file v1.0
 * maintained by g.winter
 * 21st august 2000
 *
 *
 */

#include "mpsa_private.h"

/*[ mpsa_PclPosUpdateCmd
 *[ action:  move all of the particles in a list by their velocity
 *[          multiplied by dt
 *[ objects: takes a name of a list and dt (a floating point value)
 *[ syntax:  CommandName ListName TimeStep
 */

int mpsa_PclPosUpdateCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_List *List;
  mpsa_Link *Link;
  double TempDouble;
  float DT;

  if(argc != 3) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetList(interp, argv[1], &List) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  if(Tcl_GetDouble(interp, argv[2], &TempDouble) != TCL_OK) {
    Tcl_AppendResult(interp, "Error getting timestep", (char *) NULL);
    return TCL_ERROR;
  }

  DT = TempDouble;

  for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    mpsa_PclPosUpdate(Link->Pcl, DT);
  }

  return TCL_OK;
}

/*[ mpsa_PclVelUpdateCmd
 *[ action:  updates the velolity of all of the particles in the list
 *[          by their acceleration multiplied by dt
 *[ objects: takes a name of a list and dt (a floating point value)
 *[ syntax:  CommandName ListName TimeStep
 */

int mpsa_PclVelUpdateCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_List *List;
  mpsa_Link *Link;
  double TempDouble;
  float DT;

  if(argc != 3) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetList(interp, argv[1], &List) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  if(Tcl_GetDouble(interp, argv[2], &TempDouble) != TCL_OK) {
    Tcl_AppendResult(interp, "Error getting timestep", (char *) NULL);
    return TCL_ERROR;
  }

  DT = TempDouble;

  for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    mpsa_PclVelUpdate(Link->Pcl, DT);
  }

  return TCL_OK;
}
