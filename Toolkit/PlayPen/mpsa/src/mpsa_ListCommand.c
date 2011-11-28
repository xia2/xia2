/* gsimII mpsa list command v1.1
 * maintained by g.winter
 * 29th august 2000
 *
 */

#include "mpsa_private.h"
#include <math.h>

/*[ mpsa_ListCmd
 *[ action:  anything to do with lists
 *[ objects: lists, simulations, types and particles
 *[ syntax:  too big to explain here
 */

int mpsa_ListCmd(
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

  if((strcmp(argv[1], "Create") == 0) ||
     (strcmp(argv[1], "create") == 0)) {

    /* create a list object associated with a simulation */

    mpsa_List *List;
    mpsa_Simulation *Simulation;
    
    if(argc < 4) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n", 
      "expecting ", argv[0], " create SimName ListName", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_GetSim(interp, argv[2], &Simulation) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    mpsa_ListCreate(Simulation, argv[3], &List);
    
    if(mpsa_ListHashEntryCreate(argv[3], List) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error registering list name", (char *) NULL);
      return TCL_ERROR;
    }
    
    return TCL_OK;
  } else if((strcmp(argv[1], "Delete") == 0) ||
	    (strcmp(argv[1], "delete") == 0)) {

    /* delete the actual list object */

    mpsa_List *List;
    
    if(argc < 3) {
      Tcl_AppendResult(interp, "Error - no listname specified\n",
        "expecting ", argv[0], " delete ListName", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    mpsa_ListDelete(List);
    mpsa_RemoveListFromHash(argv[2]);
    
    return TCL_OK;
    
  } else if((strcmp(argv[1], "Clear") == 0) || 
	    (strcmp(argv[1], "clear") == 0)) {

    /* clear the list of elements */

    mpsa_List *List;
    
    if(argc < 3) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n",
	"expecting ", argv[0], " clear ListName", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    if(mpsa_ListClear(List) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error clearing list", (char *) NULL);
      return TCL_ERROR;
    }
    
    return TCL_OK;
    
  } else if((strcmp(argv[1], "Append") == 0) ||
      (strcmp(argv[1], "append") == 0)) {
    
    /* appending:

       This is quite a complex bit of code, as it has to parse the arguments
       given and set a number of different flags that are either in the 
       basic particle setup or included within snap-on modules. then, these
       flags having been set, all of the particles are chechked for suitability
       for list extraction. the integer flags are used to prevent parsing
       having to take place in the loops, so as to speed them up. this way is 
       quite quick  :O)

    */


    mpsa_List *List;
    mpsa_List *FromList;
    mpsa_Link *FromLink;
    mpsa_Pip *Piptype;
    mpsa_ParticleDefn *Pcltype;
    mpsa_Particle *Pcl;
    mpsa_Simulation *Simulation;
    int IntValue, IsInt = 0, Pclflag = 0, PclCount = 0;
    int Textflag = 0;    /* flags are: is it an integer comparison          */
    double DoubleValue = 0;  /* is it a particle and is the comapator text  */
    float FloatValue = 0;  /* values are for storage of numerical comparator */
    char Number[9];
    
    if(argc < 8) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n",
        "expecting ", argv[0], " append ListName Class Element float/int ", 
        "operator value (from list)", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(argc == 10) {
      if((strcmp(argv[8], "From") == 0) ||
	 (strcmp(argv[8], "from") == 0)) {
	if(mpsa_GetList(interp, argv[9], &FromList) != MPSA_OKAY) {
	  return TCL_ERROR;
	}
      } else {
	Tcl_AppendResult(interp, "usage is: from list", (char *) NULL);
	return TCL_ERROR;
      }
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(argc == 10) {
      if(List->Simulation != FromList->Simulation) {
	Tcl_AppendResult(interp, "lists must both be from the same simulation",
          (char *) NULL);
	return TCL_ERROR;
      }
    }

    if((strcmp(argv[3], "Particle") == 0) ||
      (strcmp(argv[3], "particle") == 0)) {
      Pclflag = MPSA_OKAY;
      if(mpsa_PclSetEntry(argv[4]) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error obtaining particle data entry", 
	  (char *) NULL);
	return TCL_ERROR;
      }
      if((strcmp(argv[4], "Type") == 0) ||
        (strcmp(argv[4], "type") == 0)) {
	Textflag = 1;
      } else {
	Textflag = 0;
      }
    } else {
      Textflag = 0;
      Pclflag = MPSA_FAIL;
      if(mpsa_GetPipDefn(interp, argv[3], &Piptype) != MPSA_OKAY) {
	return TCL_ERROR;
      } else {
	if(Piptype->SetDataEntry(argv[4]) != MPSA_OKAY) {
	  Tcl_AppendResult(interp, "Error setting pip data entry", 
            (char *) NULL);
	  return TCL_ERROR;
	}
      }
    }
    
    if((strcmp(argv[5], "Float") == 0) || (strcmp(argv[5], "float") == 0)) {
      IsInt = 0;
    } else if ((strcmp(argv[5], "Int") == 0) ||
      (strcmp(argv[5], "int") == 0)) {
      IsInt = 1;
    } else {
      Tcl_AppendResult(interp, "Error - type should be float/Float/int/Int",
	(char *) NULL);
    }
    
    if(mpsa_SetOperator(argv[6]) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error parsing operator", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(IsInt == 0) {
      if(Tcl_GetDouble(interp, argv[7], &DoubleValue) != TCL_OK) {
	Tcl_AppendResult(interp, "Error getting float value for comparison",
          (char *) NULL);
	return TCL_ERROR;
      } 
    } else if(IsInt == 1) {
      if(Textflag == 0) {
	if(Tcl_GetInt(interp, argv[7], &IntValue) != TCL_OK) {
	  Tcl_AppendResult(interp, "Error getting int value for comparison",
	    (char *) NULL);
	  return TCL_ERROR;
	}
      } else {
	if(mpsa_GetPclDefn(interp, argv[7], &Pcltype) != MPSA_OKAY) {
	  Tcl_AppendResult(interp, "Error getting type ", argv[7], 
            (char *) NULL);
	  return TCL_ERROR;
	}
	IntValue = Pcltype->DynamicID;
      }
    }
    
    FloatValue = DoubleValue;
    
    Simulation = List->Simulation;
    
    /* the `guts' of the routine

       the flags having all been set, this is where the looping is performed.
       the Pclflag and IsInt determine which tests are to be used, and are
       set in the above parsing section. all that's important here is that any
       add on modules include extraction comparator operations, as seen in 
       mpsa_ParticleExtract.c for particles

    */

    if(argc == 8) {
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
    } else {
      if(Pclflag == MPSA_OKAY) {
	if(IsInt == 1) {
	  for(FromLink = FromList->firstLink; FromLink != NULL; FromLink = 
            FromLink->nextLink) {
	    Pcl = FromLink->Pcl;
	    if(mpsa_IntOperator(mpsa_GetIntEntry(Pcl), IntValue) == 
	      MPSA_OKAY) {
	      PclCount ++;
	      mpsa_AppendToList(List, Pcl);
	    }
	  }
	} else {
	  for(FromLink = FromList->firstLink; FromLink != NULL; FromLink = 
            FromLink->nextLink) {
	    Pcl = FromLink->Pcl;
	    if(mpsa_FloatOperator(mpsa_GetFloatEntry(Pcl), FloatValue) == 
	       MPSA_OKAY) {
	      PclCount ++;
	      mpsa_AppendToList(List, Pcl);
	    }
	  }
	}
      } else {
	if(IsInt == 1) {
	  for(FromLink = FromList->firstLink; FromLink != NULL; FromLink = 
            FromLink->nextLink) {
	    Pcl = FromLink->Pcl;
	    if(mpsa_ParticleHavePip(Pcl, Piptype) == MPSA_OKAY) {
	      if(mpsa_IntOperator(Piptype->GetIntDataEntry(Pcl->Pip), 
	        IntValue) == MPSA_OKAY) {
		PclCount ++;
		mpsa_AppendToList(List, Pcl);
	      }
	    }
	  }
	} else {
	  for(FromLink = FromList->firstLink; FromLink != NULL; FromLink = 
            FromLink->nextLink) {
	    Pcl = FromLink->Pcl;
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
    }      

    sprintf(Number, "%d", PclCount);
    
    Tcl_AppendResult(interp, Number, (char *) NULL);
    return TCL_OK;

  } else if((strcmp(argv[1], "Zero") == 0) ||
	    (strcmp(argv[1], "zero") == 0)) {

    /* zero the accelerations of the particles in the list */

    mpsa_Link *Link;
    mpsa_List *List;
    int i;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " needs a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      for(i = 0; i < 3; i++) {
	Link->Pcl->a[i] = 0;
      }
      Link->Pcl->phi = 0;
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "WriteToInterp") == 0) ||
	    (strcmp(argv[1], "writetointerp") == 0)) {

    /* write particle positions, velocities and masses to the interpreter */

    char x[15], y[15], z[15], m[15], vx[15], vy[15], vz[15];
    mpsa_Link *Link;
    mpsa_List *List;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " needs a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      sprintf(m, "%e ", Link->Pcl->mass);
      sprintf(x, "%e ", Link->Pcl->x[0]);
      sprintf(y, "%e ", Link->Pcl->x[1]);
      sprintf(z, "%e ", Link->Pcl->x[2]);
      sprintf(vx, "%e ", Link->Pcl->v[0]);
      sprintf(vy, "%e ", Link->Pcl->v[1]);
      sprintf(vz, "%e ", Link->Pcl->v[2]);
      Tcl_AppendResult(interp, m, x, y, z, vx, vy, vz, "\n", (char *) NULL);
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "WriteAcc") == 0) ||
	    (strcmp(argv[1], "writeacc") == 0)) {

    /* write the particle accelerations to the interpreter */

    char x[15], y[15], z[15];
    mpsa_Link *Link;
    mpsa_List *List;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " needs a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      sprintf(x, "%e ", Link->Pcl->a[0]);
      sprintf(y, "%e ", Link->Pcl->a[1]);
      sprintf(z, "%e ", Link->Pcl->a[2]);
      Tcl_AppendResult(interp, x, y, z, "\n", (char *) NULL);
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Elements") == 0) ||
	    (strcmp(argv[1], "elements") == 0)) {

    /* verify that the list structure remains in tact */

    int nelements = 0;
    mpsa_Link *Link;
    mpsa_List *List;
    char AnswerA[20], AnswerB[20];

    if(argc != 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      nelements++;
    }

    sprintf(AnswerA, "%d", nelements);
    sprintf(AnswerB, "%d", List->NElements);

    Tcl_AppendResult(interp, "List named ", List->ListName, ": ", 
      AnswerA, " actual ", AnswerB, " expected");
    return TCL_OK;

  } else if((strcmp(argv[1], "FindNaN") == 0) || 
	    (strcmp(argv[1], "findnan") == 0)) {

    /* look for not a numbers - a sure sign that something */
    /* has not been initialised properly! */

    mpsa_List *List;
    mpsa_Link *Link;
    int i;

    if(argc != 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {

      /* check also for negative masses - these can't be good! */

      if(Link->Pcl->mass < 0) {
	Tcl_AppendResult(interp, "Negative mass particle found", 
          (char *) NULL);
	return TCL_ERROR;
      } else {

	/* check for not a numbers in position and velocity */

	for(i = 0; i < 3; i++) {
	  if(isnan(Link->Pcl->x[i]) != 0) {
	    Tcl_AppendResult(interp, "Nan found: position", (char *) NULL);
	    return TCL_ERROR;
	  } else if (isnan(Link->Pcl->v[i]) != 0) {
	    Tcl_AppendResult(interp, "Nan found: velocity", (char *) NULL);
	    return TCL_ERROR;
	  }
	}
      }
    }
    
    return TCL_OK;

  } else if((strcmp(argv[1], "Mass") == 0) ||
	    (strcmp(argv[1], "mass") == 0)) {

    /* calculate the total mass in a list */

    mpsa_List *List;
    mpsa_Link *Link;
    float Mass = 0;
    char Out[15];

    if(argc != 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      Mass += Link->Pcl->mass;
    }

    sprintf(Out, "%e", Mass);
    Tcl_AppendResult(interp, Out, (char *) NULL);

    return TCL_OK;

  } else if((strcmp(argv[1], "Average") == 0) ||
	    (strcmp(argv[1], "average") == 0)) {
    
    /* average a given parameter of the particle, for example mass */
    /* or some element of data from a pip cf. append */

    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *PipType;
    mpsa_ParticleDefn *Type;
    float result = 0;
    int NParticles = 0;
    int PclFlag = 0;
    char out[15];

    if(argc != 5) {
      Tcl_AppendResult(interp, argv[1], " takes a list, class and element",
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if((strcmp(argv[3], "Particle") == 0) ||
       (strcmp(argv[3], "particle") == 0)) {
      PclFlag = MPSA_OKAY;
      if(mpsa_PclSetEntry(argv[4]) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error setting data entry ", argv[4],
          (char *) NULL);
	return TCL_ERROR;
      }
    } else {
      PclFlag = MPSA_FAIL;
      if(mpsa_GetPipDefn(interp, argv[3], &PipType) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error getting pip type", (char *) NULL);
	return TCL_ERROR;
      } else {
	if(PipType->SetDataEntry(argv[4]) != MPSA_OKAY) {
	  Tcl_AppendResult(interp, "Error setting pip entry", (char *) NULL);
	  return TCL_ERROR;
	}
      }
    }

    if(PclFlag == MPSA_OKAY) {
      for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
	result += mpsa_GetFloatEntry(Link->Pcl);
	NParticles ++;
      }
    } else {
      for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
	if(mpsa_ParticleHavePip(Link->Pcl, PipType) == MPSA_OKAY) {
	  result += PipType->GetFloatDataEntry(Link->Pcl->Pip);
	  NParticles ++;
	}
      }
    }

    if(NParticles != 0) {
      result = result / NParticles;
    }

    sprintf(out, "%e", result);

    Tcl_AppendResult(interp, out, (char *) NULL);
    return TCL_OK;

  } else if((strcmp(argv[1], "MassAveraged") == 0) ||
	    (strcmp(argv[1], "massaveraged") == 0)) {
    
    /* average a given parameter of the particle, for example mass */
    /* or some element of data from a pip cf. append */

    mpsa_List *List;
    mpsa_Link *Link;
    mpsa_Pip *PipType;
    mpsa_ParticleDefn *Type;
    float result = 0;
    float totalmass = 0;
    int PclFlag = 0;
    char out[15];

    if(argc != 5) {
      Tcl_AppendResult(interp, argv[1], " takes a list, class and element",
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if((strcmp(argv[3], "Particle") == 0) ||
       (strcmp(argv[3], "particle") == 0)) {
      PclFlag = MPSA_OKAY;
      if(mpsa_PclSetEntry(argv[4]) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error setting data entry ", argv[4],
          (char *) NULL);
	return TCL_ERROR;
      }
    } else {
      PclFlag = MPSA_FAIL;
      if(mpsa_GetPipDefn(interp, argv[3], &PipType) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error getting pip type", (char *) NULL);
	return TCL_ERROR;
      } else {
	if(PipType->SetDataEntry(argv[4]) != MPSA_OKAY) {
	  Tcl_AppendResult(interp, "Error setting pip entry", (char *) NULL);
	  return TCL_ERROR;
	}
      }
    }

    if(PclFlag == MPSA_OKAY) {
      for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
	result += Link->Pcl->mass * mpsa_GetFloatEntry(Link->Pcl);
	totalmass += Link->Pcl->mass;
      }
    } else {
      for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
	if(mpsa_ParticleHavePip(Link->Pcl, PipType) == MPSA_OKAY) {
	  result += Link->Pcl->mass * PipType->GetFloatDataEntry(Link->Pcl->Pip);
	  totalmass += Link->Pcl->mass;
	}
      }
    }

    if(totalmass != 0) {
      result = result / totalmass;
    }

    sprintf(out, "%e", result);

    Tcl_AppendResult(interp, out, (char *) NULL);
    return TCL_OK;

  } else {
    Tcl_AppendResult(interp, "Unrecognised option", (char *) NULL);
    return TCL_ERROR;
  }
}
