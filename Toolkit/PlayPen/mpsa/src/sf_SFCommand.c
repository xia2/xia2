/* star formation command file v1.0
 * maintained by g.winter
 * for loading into mpsa
 * 21st september 2000
 */

#include "sf_export.h"
#include <math.h>
#include <stdlib.h>

/*[ sf_SFCmd
 *[ action:  perform all star formation actions at the simplest level
 *[ objects: will take list of clouds and a rule
 */

int sf_SFCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  if(argc < 2) {
    Tcl_AppendResult(interp, argv[0], " takes a rule for star formation",
      (char *) NULL);
    return TCL_ERROR;
  }

  if((strcmp(argv[1], "Stochastic") == 0) ||
     (strcmp(argv[1], "stochastic") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_ParticleDefn *Type;
    mpsa_Pip *CloudDefn;
    mpsa_ParticleDefn *Definition;
    float m0;
    int PipNo;

    if(argc < 5) {
      Tcl_AppendResult(interp, argv[1], " takes a type, list and m0",
	(char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetPclDefn(interp, argv[2], &Type) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[3], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &m0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudDefn) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(List->firstLink != NULL) {
      mpsa_GetPclDefnFromID(List->firstLink->Pcl->type, &Definition);
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(gwrand48() < (Link->Pcl->mass / m0)) {
	if(mpsa_GetPipPosition(Definition, CloudDefn, &PipNo) != 
           MPSA_OKAY) {
          Tcl_AppendResult(interp, "Non cloud type particle in list",
            (char *) NULL);
          return TCL_ERROR;
        }
        Link->Pcl->Pip = Link->Pcl->PipList[PipNo];
	if(sf_StarForm(Link->Pcl, Type, List->Simulation) != SF_OKAY){
	  Tcl_AppendResult(interp, "Error forming ", Type->Name,
            (char *) NULL);
	  return TCL_ERROR;
	}
      }
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "StarForm") == 0) ||
	    (strcmp(argv[1], "starform") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_ParticleDefn *Type;
    mpsa_Pip *CloudDefn;
    mpsa_ParticleDefn *Definition;
    int NoHeat = 0;
    float m0, T0, Tindex, Tkeep;
    int PipNo;

    if(argc < 7) {
      Tcl_AppendResult(interp, argv[1], " takes a type, list, m0, ", 
        "Tindex and T0", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetPclDefn(interp, argv[2], &Type) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[3], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &m0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[5], &Tindex) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[6], &T0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(argc == 8) {
      if((strcmp(argv[7], "NoHeat") == 0) ||
	 (strcmp(argv[7], "noheat") == 0)) {
	NoHeat = 1;
      } else {
	NoHeat = 0;
      }
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudDefn) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(List->firstLink != NULL) {
      mpsa_GetPclDefnFromID(List->firstLink->Pcl->type, &Definition);
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(gwrand48() < (Link->Pcl->mass / m0)) {
	if(mpsa_GetPipPosition(Definition, CloudDefn, &PipNo) != 
           MPSA_OKAY) {
          Tcl_AppendResult(interp, "Non cloud type particle in list",
            (char *) NULL);
          return TCL_ERROR;
        }
        Link->Pcl->Pip = Link->Pcl->PipList[PipNo];
	Tkeep = ((cloud_Pip *) Link->Pcl->Pip)->T;
	if(gwrand48() < (pow(Tkeep / T0, Tindex))) {
	  if(sf_StarForm(Link->Pcl, Type, List->Simulation) != SF_OKAY){
	    Tcl_AppendResult(interp, "Error forming ", Type->Name,
	      (char *) NULL);
	    return TCL_ERROR;
	  }
	  if(NoHeat == 1) {
	    /* a little method or preventing heating from star formation */
	    ((cloud_Pip *) Link->Pcl->Pip)->T = Tkeep;
	  }
	}
      }
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "SFESetup") == 0) ||
	    (strcmp(argv[1], "sfesetup") == 0)) {

    float Constant, massindx, metalindx;

    if(argc < 5) {
      Tcl_AppendResult(interp, argv[1], " takes factor, mass and metal index",
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[2], &Constant) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(mpsa_GetFloat(interp, argv[3], &massindx) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(mpsa_GetFloat(interp, argv[4], &metalindx) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    sf_SetParam(Constant, massindx, metalindx);

    return TCL_OK;
    
  } else if((strcmp(argv[1], "SFE") == 0) ||
	    (strcmp(argv[1], "sfe") == 0)) {

    float Constant, massindx, metalindx;
    float mass0, metal0;

    if(argc < 7) {
      Tcl_AppendResult(interp, argv[1], " takes factor, mass and metal index",
        " mass0 and metal0", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[2], &Constant) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(mpsa_GetFloat(interp, argv[3], &massindx) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(mpsa_GetFloat(interp, argv[4], &metalindx) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(mpsa_GetFloat(interp, argv[5], &mass0) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    if(mpsa_GetFloat(interp, argv[6], &metal0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    Constant *= pow(mass0, -massindx) * pow(metal0, -metalindx);

    sf_SetParam(Constant, massindx, metalindx);

    return TCL_OK;

  } else if((strcmp(argv[1], "TwoPhase") == 0) ||
	    (strcmp(argv[1], "twophase") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_ParticleDefn *Type1;
    mpsa_ParticleDefn *Type2;
    mpsa_Pip *CloudDefn;
    mpsa_ParticleDefn *Definition;
    float m0, m1;
    int PipNo;

    if(argc < 7) {
      Tcl_AppendResult(interp, argv[1], " takes two types, list and m0 for type one and two",
	(char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetPclDefn(interp, argv[2], &Type1) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPclDefn(interp, argv[3], &Type2) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[4], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[5], &m0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[6], &m1) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudDefn) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(List->firstLink != NULL) {
      mpsa_GetPclDefnFromID(List->firstLink->Pcl->type, &Definition);
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(gwrand48() < (Link->Pcl->mass / m0)) {
	if(mpsa_GetPipPosition(Definition, CloudDefn, &PipNo) != 
           MPSA_OKAY) {
          Tcl_AppendResult(interp, "Non cloud type particle in list",
            (char *) NULL);
          return TCL_ERROR;
        }
        Link->Pcl->Pip = Link->Pcl->PipList[PipNo];
	if(sf_StarForm(Link->Pcl, Type1, List->Simulation) != SF_OKAY){
	  Tcl_AppendResult(interp, "Error forming ", Type1->Name,
            (char *) NULL);
	  return TCL_ERROR;
	}
      }
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(gwrand48() < (Link->Pcl->mass / m1)) {
	if(mpsa_GetPipPosition(Definition, CloudDefn, &PipNo) != 
           MPSA_OKAY) {
          Tcl_AppendResult(interp, "Non cloud type particle in list",
            (char *) NULL);
          return TCL_ERROR;
        }
        Link->Pcl->Pip = Link->Pcl->PipList[PipNo];
	if(sf_StarForm(Link->Pcl, Type2, List->Simulation) != SF_OKAY){
	  Tcl_AppendResult(interp, "Error forming ", Type2->Name,
            (char *) NULL);
	  return TCL_ERROR;
	}
      }
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "ShockSF") == 0) ||
	    (strcmp(argv[1], "shocksf") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_ParticleDefn *Type;
    mpsa_Pip *CloudDefn;
    mpsa_ParticleDefn *Definition;
    float m0, T0, Tindex;
    int PipNo;

    if(argc < 7) {
      Tcl_AppendResult(interp, argv[1], " takes a type, list, m0, ", 
        "Tindex and T0", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetPclDefn(interp, argv[2], &Type) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[3], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &m0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[5], &Tindex) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[6], &T0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudDefn) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(List->firstLink != NULL) {
      mpsa_GetPclDefnFromID(List->firstLink->Pcl->type, &Definition);
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      cloud_Pip *Pip;
      if(gwrand48() < (Link->Pcl->mass / m0)) {
	if(mpsa_GetPipPosition(Definition, CloudDefn, &PipNo) != 
           MPSA_OKAY) {
          Tcl_AppendResult(interp, "Non cloud type particle in list",
            (char *) NULL);
          return TCL_ERROR;
        }
        Link->Pcl->Pip = Link->Pcl->PipList[PipNo];
	Pip = (cloud_Pip *) Link->Pcl->Pip;
	if(Pip->shocked == 1) {
	  /* say here that star formation can only be triggered by shocks! */
	  if(gwrand48() < (pow(Pip->T / T0, Tindex))) {
	    if(sf_StarForm(Link->Pcl, Type, List->Simulation) != SF_OKAY){
	      Tcl_AppendResult(interp, "Error forming ", Type->Name,
		(char *) NULL);
	      return TCL_ERROR;
	    }
	  }
	}
      }
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Bimodal.Setup") == 0) ||
	    (strcmp(argv[1], "bimodal.setup") == 0)) {
    float index, lower, inter, higher;

    if(argc != 6) {
      Tcl_AppendResult(interp, argv[1], " requires and index",
        " and three masses", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[2], &index) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &lower) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &inter) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[5], &higher) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    sf_BimodalSetup(interp, index, lower, inter, higher);

    return TCL_OK;

  } else if((strcmp(argv[1], "Bimodal.Form") == 0) ||
	    (strcmp(argv[1], "bimodal.form") == 0)) {
    mpsa_ParticleDefn *Type1;
    mpsa_ParticleDefn *Type2;
    mpsa_Simulation *Sim;
    float m0, t0, tindex;
    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *CloudPip;

    if(argc != 8) {
      Tcl_AppendResult(interp, argv[1], " requires a list, m0, t0, tindex", 
	" lowmasstype and highmasstype", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &m0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &t0) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[5], &tindex) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPipDefn(interp, "cloud", &CloudPip) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPclDefn(interp, argv[6], &Type1) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetPclDefn(interp, argv[7], &Type2) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_SetPipToPipType(Link->Pcl, CloudPip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Non cloud in list", (char *) NULL);
	return TCL_ERROR;
      }

      if((gwrand48() < (Link->Pcl->mass / m0)) &&
	 (gwrand48() < pow(((cloud_Pip *) Link->Pcl->Pip)->T / t0, tindex))) {
	if(sf_BimodalStarForm(Link->Pcl, Type1, Type2, List->Simulation) != 
	  SF_OKAY) {
	  Tcl_AppendResult(interp, "Error forming stars", (char *) NULL);
	  return TCL_ERROR;
	}
      }
    }

    return TCL_OK;

  } else {
    Tcl_AppendResult(interp, "Option ", argv[1], " not recognised",
      (char *) NULL);
    return TCL_ERROR;
  }
}

