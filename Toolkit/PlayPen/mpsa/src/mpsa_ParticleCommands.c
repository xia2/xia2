/* gsimII mpsa particle commands file v1.0
 * maintained by g.winter
 * 15th august 2000
 * 
 * 
 */

#include "mpsa_private.h"

/*[ mpsa_CreatePclCmd
 *[ action:  create a number of particles as described at command line, 
 *[          associating them with a given simulation
 *[ objects: takes a simulation name, a particle type name and an integer
 *[          describing the number to be created
 *[ syntax:  CommandName SimName typeName NumberToMake
 */

int mpsa_CreatePclCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_Simulation *Simulation;
  mpsa_ParticleDefn *type;
  int PclCount, i;

  if(argc < 4) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetSim(interp, argv[1], &Simulation) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  if(mpsa_GetPclDefn(interp, argv[2], &type) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  if(Tcl_GetInt(interp, argv[3], &PclCount) != TCL_OK) {
    Tcl_AppendResult(interp, "Error getting number to make", (char *) NULL);
    return TCL_ERROR;
  }

  Tcl_AppendResult(interp, "Creating ", argv[3], " ", type->Name, " particles",
    (char *) NULL);

  for(i = 0; i < PclCount; i++) {
    if(mpsa_PclCreate(Simulation, type) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error creating particle", (char *) NULL);
      return TCL_ERROR;
    }
  }

  return TCL_OK;
}
