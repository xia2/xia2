/* gsimII mpsa list commands file v1.0
 * maintained by g.winter
 * 16th august 2000
 * 
 * 
 */

#include "mpsa_private.h"

/*[ mpsa_ListClearCmd
 *[ action:  empty a list structure of pointers to particles
 *[ objects: name of list structure
 *[ syntax:  CommandName ListName
 */

int mpsa_ListClearCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_List *List;

  if(argc < 2) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetList(interp, argv[1], &List) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  if(mpsa_ListClear(List) != MPSA_OKAY) {
    Tcl_AppendResult(interp, "Error clearing list", (char *) NULL);
    return TCL_ERROR;
  }

  return TCL_OK;
}

/*[ mpsa_AppendToListCmd
 *[ action:  append particles from simulation structure to a list structure
 *[          according to basic (ie type) criteria
 *[ objects: takes list structure name and particle definition name
 *[ syntax:  CommandName ListName typeName
 */

int mpsa_AppendToListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_Simulation *Sim;
  mpsa_List *List;
  mpsa_ParticleDefn *type;
  int NumberInList;
  char Number[9], Total[9];

  if(argc < 3) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetList(interp, argv[1], &List) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  Sim = List->Simulation;

  if((strcmp(argv[2], "all") == 0) || (strcmp(argv[2], "All") == 0)) {
    if(mpsa_extractAllToList(Sim, List, &NumberInList) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error extracting particles", (char *) NULL);
      return TCL_ERROR;
    }
  } else {
    if(mpsa_GetPclDefn(interp, argv[2], &type) != MPSA_OKAY) {
    return TCL_ERROR;
  }
    if(mpsa_extractSimToList(Sim, List, &NumberInList, type->DynamicID) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error extracting particles", (char *) NULL);
      return TCL_ERROR;
    }
  }

  sprintf(Number, "%d", NumberInList);
  sprintf(Total, "%d", List->NElements);

  Tcl_AppendResult(interp, Number, " particles extracted to ", List->ListName,
    " : ", Total, " Total", (char *) NULL);

  return TCL_OK;
}

/*[ mpsa_DeletePclCmd
 *[ action:  delete all particles extracted into a list from simulation 
 *[          structure and clear the list
 *[ objects: name of list of extracted particles
 *[ syntax:  CommandName ListName
 */

int mpsa_DeletePclCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_List *List;
  mpsa_Simulation *Simulation;
  mpsa_Particle *First, *Last;
  mpsa_Link *Link;
  int NumberToDelete;
  char Number[9];

  if(argc < 2) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetList(interp, argv[1], &List) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  Simulation = List->Simulation;
  NumberToDelete = List->NElements;
  First = Simulation->firstPcl;
  Last = Simulation->lastPcl;

  for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    if(Link->Pcl == First) {
      Simulation->firstPcl = First->nextPcl;
      First = Simulation->firstPcl;
    }
    if(Link->Pcl == Last) {
      Simulation->lastPcl = Last->prevPcl;
      Last = Simulation->lastPcl;
    }
    if(mpsa_DeletePcl(Link->Pcl) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error deleting particles", (char *) NULL);
      return TCL_ERROR;
    }
  }

  sprintf(Number, "%d", NumberToDelete);

  Tcl_AppendResult(interp, Number, " particles deleted", (char *) NULL);

  List->Simulation->NPcls -= NumberToDelete;

  if(mpsa_ListClear(List) != MPSA_OKAY) {
    Tcl_AppendResult(interp, "Error clearing list", (char *) NULL);
    return TCL_ERROR;
  }

  return TCL_OK;
}

/*[ mpsa_FlexibleAppendToListCmd
 *[ action:  append particles from simulation structure to list according to
 *[          a flexible set of criteria defined by user, or criteria included
 *[          within mpsa base
 *[ objects: name of list, name of group (ie pip type or particle), criterion
 *[          within group, operator (described elsewhere) and a value
 *[ syntax:  CommandName ListName GroupName Property Float/Int Operator Value
 */

int mpsa_FlexibleAppendToListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_List *List;
  mpsa_Pip *Piptype;
  mpsa_ParticleDefn *Pcltype;
  mpsa_Particle *Pcl;
  mpsa_Simulation *Simulation;
  int IntValue, IsInt = 0, Pclflag = 0, PclCount = 0;
  int Textflag = 0;
  double DoubleValue;
  float FloatValue;
  char Number[9], Total[9];

  if(argc < 7) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetList(interp, argv[1], &List) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  if((strcmp(argv[2], "Pcl") == 0) || (strcmp(argv[2], "particle")
    ==0)) {
    Pclflag = MPSA_OKAY;
    if(mpsa_PclSetEntry(argv[3]) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error obtaining particle data entry", 
        (char *) NULL);
      return TCL_ERROR;
    }
    if((strcmp(argv[2], "type") == 0) || (strcmp(argv[2], "type") == 0)) {
      Textflag = 1;
    } else {
      Textflag = 0;
    }
  } else {
    Textflag = 0;
    Pclflag = MPSA_FAIL;
    if(mpsa_GetPipDefn(interp, argv[2], &Piptype) != MPSA_OKAY) {
      return TCL_ERROR;
    } else {
      if(Piptype->SetDataEntry(argv[3]) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error setting pip data entry", (char *) NULL);
	return TCL_ERROR;
      }
    }
  }

  if((strcmp(argv[4], "Float") == 0) || (strcmp(argv[4], "float") == 0)) {
    IsInt = 0;
  } else if ((strcmp(argv[4], "Int") == 0) || (strcmp(argv[4], "int") == 0)) {
    IsInt = 1;
  } else {
    Tcl_AppendResult(interp, "Error - type should be float/Float/int/Int",
      (char *) NULL);
  }

  if(mpsa_SetOperator(argv[5]) != MPSA_OKAY) {
    Tcl_AppendResult(interp, "Error parsing operator", (char *) NULL);
    return TCL_ERROR;
  }

  if(IsInt == 0) {
    if(Tcl_GetDouble(interp, argv[6], &DoubleValue) != TCL_OK) {
      Tcl_AppendResult(interp, "Error getting floating value for comparison",
        (char *) NULL);
      return TCL_ERROR;
    } 
  } else if(IsInt == 1) {
    if(Textflag == 0) {
      if(Tcl_GetInt(interp, argv[6], &IntValue) != TCL_OK) {
	Tcl_AppendResult(interp, "Error getting integer value for comparison",
	  (char *) NULL);
	return TCL_ERROR;
      }
    } else {
      if(mpsa_GetPclDefn(interp, argv[6], &Pcltype) != 
        MPSA_OKAY) {
	return TCL_ERROR;
      }
      IntValue = Pcltype->DynamicID;
    }
  }

  FloatValue = DoubleValue;

  Simulation = List->Simulation;

  if(Pclflag == MPSA_OKAY) {
    if(IsInt == 1) {
      for(Pcl = Simulation->firstPcl; Pcl != NULL;
        Pcl = Pcl->nextPcl) {
	if(mpsa_IntOperator(mpsa_GetIntEntry(Pcl), IntValue) == 
          MPSA_OKAY) {
	  PclCount ++;
	  mpsa_AppendToList(List, Pcl);
	}
      }
    } else {
      for(Pcl = Simulation->firstPcl; Pcl != NULL;
        Pcl = Pcl->nextPcl) {
	if(mpsa_FloatOperator(mpsa_GetFloatEntry(Pcl), FloatValue) == 
          MPSA_OKAY) {
	  PclCount ++;
	  mpsa_AppendToList(List, Pcl);
	}
      }
    }
  } else {
    if(IsInt == 1) {
      for(Pcl = Simulation->firstPcl; Pcl != NULL;
        Pcl = Pcl->nextPcl) {
	if(mpsa_ParticleHavePip(Pcl, Piptype) == MPSA_OKAY) {
	  if(mpsa_IntOperator(Piptype->GetIntDataEntry(Pcl->Pip), 
	    IntValue) == MPSA_OKAY) {
	    PclCount ++;
	    mpsa_AppendToList(List, Pcl);
	  }
	}
      }
    } else {
      for(Pcl = Simulation->firstPcl; Pcl != NULL;
        Pcl = Pcl->nextPcl) {
	if(mpsa_ParticleHavePip(Pcl, Piptype) == MPSA_OKAY) {
	  if(mpsa_FloatOperator(Piptype->GetFloatDataEntry(Pcl->Pip),
            FloatValue) == MPSA_OKAY) {
	    PclCount ++;
	    mpsa_AppendToList(List, Pcl);
	  }
	}
      }
    }
  }

  sprintf(Number, "%d", PclCount);
  sprintf(Total, "%d", List->NElements);

  Tcl_AppendResult(interp, Number, " particles extracted: ", Total, " total",
    (char *) NULL);
  return TCL_OK;
}

