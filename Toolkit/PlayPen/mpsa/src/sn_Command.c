/* sn command file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 16th october 2000
 * 
 */

#include "tcl.h"
#include "mpsa_export.h"
#include "tree_export.h"
#include "tree_private.h"
#include "sn_export.h"

/*[ sn_SNovaCmd.c
 *[ action:  catch all function implementing supernova physics
 *[ objects: can take almost anything
 */

int sn_SNovaCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  if(argc == 1) {
    Tcl_AppendResult(interp, argv[0], " requires at least one option", 
      (char *) NULL);
    return TCL_ERROR;
  }

  if((strcmp(argv[1], "StartSN") == 0) ||
     (strcmp(argv[1], "startsn") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_ParticleDefn *SNType;
    mpsa_Simulation *Sim;

    if(argc != 4) {
      Tcl_AppendResult(interp, argv[1], " requires a list and a type",
	(char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPclDefn(interp, argv[3], &SNType) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    Sim = List->Simulation;

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      sn_SNForm(Link->Pcl, SNType, Sim);
    }

    return TCL_OK;
  } else if((strcmp(argv[1], "Shock") == 0) ||
	    (strcmp(argv[1], "shock") == 0)) {
    tree_Node *Tree;
    mpsa_Link *Link;
    mpsa_List *List;
    mpsa_Pip *SNPip;
    float dt, rmin, rmax;

    if(argc != 5) {
      Tcl_AppendResult(interp, argv[1], " requires a list, tree and dt", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(tree_GetTree(interp, argv[3], &Tree) != TREE_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &dt) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "sn", &SNPip) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Supernova pip not defined?", (char *) NULL);
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_SetPipToPipType(Link->Pcl, SNPip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error getting pip", (char *) NULL);
	return TCL_ERROR;
      }

      rmin = ((sn_Pip *) Link->Pcl->Pip)->radius;
      rmax = ((sn_Pip *) Link->Pcl->Pip)->radius + 
        dt * ((sn_Pip *) Link->Pcl->Pip)->speed;
      sn_CloudInteractionFind(rmin, rmax, Link->Pcl, Tree);
    }

    return TCL_OK;
  } else if((strcmp(argv[1], "Update") == 0) ||
	    (strcmp(argv[1], "update") == 0)) {
    mpsa_Link *Link;
    mpsa_List *List;
    mpsa_Pip *SNPip;
    float dt;

    if(argc != 4) {
      Tcl_AppendResult(interp, argv[1], " requires a list and dt", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &dt) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "sn", &SNPip) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_SetPipToPipType(Link->Pcl, SNPip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error getting pip", (char *) NULL);
	return TCL_ERROR;
      }
      sn_UpdateRadius(Link->Pcl, (sn_Pip *) Link->Pcl->Pip, dt);
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Setup") == 0) ||
	    (strcmp(argv[1], "setup") == 0)) {
    float m0, t0;

    if(argc != 4) {
      Tcl_AppendResult(interp, argv[1], " requires mass0 and time0",
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[2], &m0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &t0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    sn_SetParam(t0, m0);

    return TCL_OK;

  } else if((strcmp(argv[1], "Heat") == 0) ||
	    (strcmp(argv[1], "heat") == 0)) {
    if(argc != 3) {
      Tcl_AppendResult(interp, argv[1], " requires on/off", (char *) NULL);
      return TCL_ERROR;
    }

    if((strcmp(argv[2], "On") == 0) ||
       (strcmp(argv[2], "on") == 0)) {
      sn_HeatSet(0);
    } else {
      sn_HeatSet(1);
    }

    return  TCL_OK;

  } else {
    Tcl_AppendResult(interp, argv[1], " not recognised", (char *) NULL);
    return TCL_ERROR;
  }
}
