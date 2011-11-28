/* cloud module command file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 14th september 2000
 * 
 */

#include "mpsa_export.h"
#include "tree_export.h"
#include "tree_private.h"
#include "cloud_export.h"

/*[ cloud_CloudCmd
 *[ action:  anything to do with clouds, will control physics etc.
 *[ objects: cloud particles, lists and trees for a variety
 *[          of different tasks
 */

int cloud_CloudCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  if(argc < 2) {
    Tcl_AppendResult(interp, argv[0], " takes one of the following options\n",
      "setradius/SetRadius", (char *) NULL);
    return TCL_ERROR;
  }

  if((strcmp(argv[1], "SetRadius") == 0) || 
     (strcmp(argv[1], "setradius") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *CloudPip;

    if(mpsa_GetPipDefn(interp, "cloud", &CloudPip) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Serious error - cloud pip not defined", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_SetPipToPipType(Link->Pcl, CloudPip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Non cloud particle in list", (char *) NULL);
	return TCL_ERROR;
      } else {
	cloud_SetRadius(Link->Pcl);
      }
    }

    return TCL_OK;
  } else if((strcmp(argv[1], "FindCollisions") == 0) || 
	    (strcmp(argv[1], "findcollisions") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *CloudPipDefn;
    tree_Node *Root;
    int PipPosition;
    float Radius;
    int NDead;
    char Result[10];
    mpsa_ParticleDefn *Definition = NULL;

    if(argc != 4) {
      Tcl_AppendResult(interp, argv[1], " requires a list and a tree", 
	(char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(tree_GetTree(interp, argv[3], &Root) != TREE_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudPipDefn) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(List->firstLink != NULL) {
      mpsa_GetPclDefnFromID(List->firstLink->Pcl->type, &Definition);
    }
    NDead = 0;
    
    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(Link->Pcl->flag != CLOUD_FAIL) {
	if(Definition->DynamicID != Link->Pcl->type) {
	  mpsa_GetPclDefnFromID(Link->Pcl->type, &Definition);
	}
	if(mpsa_GetPipPosition(Definition, CloudPipDefn, &PipPosition) != 
	   MPSA_OKAY) {
	  Tcl_AppendResult(interp, "Non cloud type particle in list",
	    (char *) NULL);
	  return TCL_ERROR;
	}
	Link->Pcl->Pip = Link->Pcl->PipList[PipPosition];
	Radius = ((cloud_Pip *)Link->Pcl->Pip)->radius;
	if(Link->Pcl->flag != CLOUD_FAIL) {
	  cloud_TreeCollisionSearch(Radius, Link->Pcl, Root);
	}
	if(Link->Pcl->flag != CLOUD_FAIL) {
	  NDead ++;
	}
      }
    }

    sprintf(Result, "%d", List->NElements - NDead);
    Tcl_AppendResult(interp, Result, (char *) NULL);

    return TCL_OK;

  } else if((strcmp(argv[1], "GetPip") == 0) || 
	    (strcmp(argv[1], "getpip") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *CloudPip;

    if(mpsa_GetPipDefn(interp, "cloud", &CloudPip) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Serious error - cloud pip not defined", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_SetPipToPipType(Link->Pcl, CloudPip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Non cloud particle in list", (char *) NULL);
	return TCL_ERROR;
      }
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "SetFragParam") == 0) || 
	    (strcmp(argv[1], "setfragparam") == 0)) {
    float MMin, MMax, Index;
    if(argc < 5) {
      Tcl_AppendResult(interp, argv[1], " takes MMin, MMax, Index",
        (char *) NULL);
      return TCL_ERROR;
    }
    if(mpsa_GetFloat(interp, argv[2], &MMin) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(mpsa_GetFloat(interp, argv[3], &MMax) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(mpsa_GetFloat(interp, argv[4], &Index) != MPSA_OKAY) {
      return TCL_ERROR;
    } 

    cloud_SetFragParam(MMin, MMax, Index);

    return TCL_OK;
  } else if((strcmp(argv[1], "Fragment") == 0) ||
	    (strcmp(argv[1], "fragment") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Simulation *Sim;
    mpsa_Pip *CloudPip;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    Sim = List->Simulation;
    if(mpsa_GetPipDefn(interp, "cloud", &CloudPip) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "something seriously wrong here", 
        (char *) NULL);
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(cloud_FragmentCloud(Link->Pcl, Sim, CloudPip) != CLOUD_OKAY) {
	Tcl_AppendResult(interp, "Error fragmenting cloud", (char *) NULL);
	return TCL_ERROR;
      }
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "DeShock") == 0) ||
	    (strcmp(argv[1], "deshock") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *CloudPip;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudPip) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "something seriously wrong here", 
        (char *) NULL);
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_SetPipToPipType(Link->Pcl, CloudPip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Non cloud particle in list", (char *) NULL);
	return TCL_ERROR;
      }
      ((cloud_Pip *) Link->Pcl->Pip)->shocked = 0;
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Cool") == 0) ||
	    (strcmp(argv[1], "cool") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *CloudPip;
    float dt;

    if(argc < 4) {
      Tcl_AppendResult(interp, argv[1], " requires a list and timestep", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &dt) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudPip) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "something seriously wrong here", 
        (char *) NULL);
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_SetPipToPipType(Link->Pcl, CloudPip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Non cloud particle in list", (char *) NULL);
	return TCL_ERROR;
      }
      cloud_CoolCloud(Link->Pcl, dt);
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "SetRho") == 0) ||
	    (strcmp(argv[1], "setrho") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *CloudPip;
    cloud_Pip *Pip;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudPip) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "something seriously wrong here", 
        (char *) NULL);
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_SetPipToPipType(Link->Pcl, CloudPip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Non cloud particle in list", (char *) NULL);
	return TCL_ERROR;
      }
      Pip = (cloud_Pip *) Link->Pcl->Pip;

      /* from kv parameters and n = k / T */

      Pip->rho = 6.54 * (10 / Pip->T);
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "SetRadiusFactor") == 0) ||
	    (strcmp(argv[1], "setradiusfactor") == 0)) {

    /* to set the constant in r = (m t) ^ 0.333 */

    float NewValue;

    if(argc == 2) {
      Tcl_AppendResult(interp, argv[1], " takes a new value to set",
	(char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[2], &NewValue) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    cloud_ChangeRadiusFactor(NewValue);

    return TCL_OK;

  } else if((strcmp(argv[1], "Heat") == 0) ||
	    (strcmp(argv[1], "heat") == 0)) {
    if(argc != 3) {
      Tcl_AppendResult(interp, argv[1], " requires on/off", (char *) NULL);
      return TCL_ERROR;
    }

    if((strcmp(argv[1], "On") == 0) ||
       (strcmp(argv[1], "on") == 0)) {
      cloud_SetHeat(0);
    } else {
      cloud_SetHeat(1);
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Write") == 0) ||
	    (strcmp(argv[1], "write") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    cloud_Pip *Pip;
    mpsa_Pip *CloudPip;
    char x[15], y[15], z[15], m[15], t[15];

    if(argc != 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudPip) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "something seriously wrong here", 
        (char *) NULL);
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_SetPipToPipType(Link->Pcl, CloudPip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Non cloud particle in list", (char *) NULL);
	return TCL_ERROR;
      }
      Pip = (cloud_Pip *) Link->Pcl->Pip;
      sprintf(x, "%e\t", Link->Pcl->x[0]);
      sprintf(y, "%e\t", Link->Pcl->x[1]);
      sprintf(z, "%e\t", Link->Pcl->x[2]);
      sprintf(m, "%e\t", Link->Pcl->mass);;
      sprintf(t, "%e\n", Pip->T);
      Tcl_AppendResult(interp, x, y, z, m, t, (char *) NULL);
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "SetIndex") == 0) ||
	    (strcmp(argv[1], "setindex") == 0)) {
    float NewMIndex, NewTIndex;

    if(argc != 4) {
      Tcl_AppendResult(interp, argv[1], " requires mindex and tindex", 
	(char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[2], &NewMIndex) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &NewTIndex) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    cloud_SetIndices(NewMIndex, NewTIndex);

    return TCL_OK;

  } else if((strcmp(argv[1], "FColl2") == 0) || 
	    (strcmp(argv[1], "fcoll2") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *CloudPipDefn;
    tree_Node *Root;
    int PipPosition, i;
    float Radius, dt, v;
    int NDead;
    char Result[10];
    mpsa_ParticleDefn *Definition = NULL;

    if(argc != 5) {
      Tcl_AppendResult(interp, argv[1], " requires a list, a tree and ", 
        "the timestep size", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(tree_GetTree(interp, argv[3], &Root) != TREE_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &dt) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudPipDefn) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(List->firstLink != NULL) {
      mpsa_GetPclDefnFromID(List->firstLink->Pcl->type, &Definition);
    }
    NDead = 0;
    
    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(Link->Pcl->flag != CLOUD_FAIL) {
	if(Definition->DynamicID != Link->Pcl->type) {
	  mpsa_GetPclDefnFromID(Link->Pcl->type, &Definition);
	}
	if(mpsa_GetPipPosition(Definition, CloudPipDefn, &PipPosition) != 
	   MPSA_OKAY) {
	  Tcl_AppendResult(interp, "Non cloud type particle in list",
	    (char *) NULL);
	  return TCL_ERROR;
	}
	Link->Pcl->Pip = Link->Pcl->PipList[PipPosition];
	Radius = ((cloud_Pip *)Link->Pcl->Pip)->radius;
	v = 0;
	for(i = 0; i < 3; i++) {
	  v += Link->Pcl->v[i] * Link->Pcl->v[i];
	}
	Radius += dt * sqrt(v);
	if(Link->Pcl->flag != CLOUD_FAIL) {
	  cloud_TreeCollisionSearch2(Radius, dt, Link->Pcl, Root);
	}
	if(Link->Pcl->flag != CLOUD_FAIL) {
	  NDead ++;
	}
      }
    }

    sprintf(Result, "%d", List->NElements - NDead);
    Tcl_AppendResult(interp, Result, (char *) NULL);

    return TCL_OK;

  } else if((strcmp(argv[1], "MSpec") == 0) ||
	    (strcmp(argv[1], "mspec") == 0)) {
    mpsa_List *List;
    int print = 0;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(argc == 4) {
      if((strcmp(argv[3], "Print") == 0) ||
	 (strcmp(argv[3], "print") == 0)) {
	print = 1;
      } else {
	Tcl_AppendResult(interp, argv[3], " should be print", (char *) NULL);
	return TCL_ERROR;
      }
    }

    cloud_MassSpectrum(interp, List, print);

    return TCL_OK;

  } else {
    Tcl_AppendResult(interp, "Option ", argv[1], " not recognised", 
      (char *) NULL);
    return TCL_ERROR;
  }
}
