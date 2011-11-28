/* gsimII mpsa sim command file v1.0
 * maintained by g.winter
 * 30th august 2000
 * 
 */

#include "mpsa_private.h"

/*[ mpsa_SimCmd
 *[ action:  creates/destroys simulation structure and hash entry to access it.
 *[ objects: name of simulation structure
 *[ syntax:  CommandName option SimName
 */

int mpsa_SimCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  if(argc < 2) {
    Tcl_AppendResult(interp, "Error - need an option for this command", 
      (char *) NULL);
    return TCL_ERROR;
  }

  if((strcmp(argv[1], "Create") == 0) || (strcmp(argv[1], "create") == 0)) {
    Tcl_HashEntry *SimEntry;
    mpsa_Simulation *Sim;
    int new;

    if(argc < 3) {
      Tcl_AppendResult(interp, "Error - no simulation name specified", (char *) NULL);
      return TCL_ERROR;
    }
    
    Sim = (mpsa_Simulation *) malloc (sizeof(mpsa_Simulation));
    
    mpsa_SimZero(Sim);
    
    
    SimEntry = Tcl_CreateHashEntry(&mpsa_SimHashTable, argv[2], &new);
    if(new) {
      Tcl_SetHashValue(SimEntry, Sim);
    } else {
      Tcl_AppendResult(interp, "Error registering sim", (char *) NULL);
      free(Sim);
      return TCL_ERROR;
    }
    
    return TCL_OK;
    
  } else if((strcmp(argv[1], "Delete") == 0) ||
      (strcmp(argv[1], "delete")== 0)) {
    mpsa_Simulation *Sim;
    int i;
    
    if(argc < 2) {
      Tcl_AppendResult(interp, "Error - no simulation name specified", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_GetSim(interp, argv[2], &Sim) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    mpsa_DeletePcls(Sim->firstPcl);
    
    if(Sim->NLists != 0) {
      for(i = 0; i < Sim->NLists; i++) {
	mpsa_ListClear(Sim->Lists[i]);
	Tcl_AppendElement(interp, Sim->Lists[i]->ListName);
	mpsa_RemoveListFromHash(Sim->Lists[i]->ListName);
	free(Sim->Lists[i]->ListName);
	free(Sim->Lists[i]);
      }
      free(Sim->Lists);
    }
    
    free(Sim);
    mpsa_RemoveSimFromHash(argv[2]);
    return TCL_OK;

  } else if((strcmp(argv[1], "Age") == 0) ||
	    (strcmp(argv[1], "age") == 0)) {
    mpsa_Simulation *Sim;
    mpsa_Particle *Pcl;
    float dt;
    
    if(argc != 4) {
      Tcl_AppendResult(interp, argv[1], " requires a simulation and a dt",
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetSim(interp, argv[2], &Sim) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &dt) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Pcl = Sim->firstPcl; Pcl != NULL; Pcl = Pcl->nextPcl) {
      Pcl->age += dt;
    }

    return TCL_OK;

  } else {
    Tcl_AppendResult(interp, "unrecognised option", (char *) NULL);
    return TCL_ERROR;
  }

}
