/* gsimII mpsa commands file v1.0
 * maintained by g.winter
 * 15th august 2000
 * 
 */

#include "mpsa_export.h"
#include "mpsa_private.h"
#include <string.h>

/*[ mpsa_CreateListCmd
 *[ action:  create a new list structure, register with hash table and
 *[          simulation structure
 *[ objects: takes name of a simulation and name of new list structure
 *[ syntax:  CommandName SimName ListName
 */

int mpsa_CreateListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  Tcl_HashEntry *ListEntry;
  mpsa_List *List;
  int new;
  mpsa_Simulation *Simulation;

  if(argc < 3) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetSim(interp, argv[1], &Simulation) != MPSA_OKAY) {
        return TCL_ERROR;
  }

  mpsa_ListCreate(Simulation, argv[2], &List);

  ListEntry = Tcl_CreateHashEntry(&mpsa_ListHashTable, argv[2], &new);
  if(new) {
    Tcl_SetHashValue(ListEntry, List);
  } else {
    Tcl_AppendResult(interp, "Error registering listname", (char *) NULL);
    free(List->ListName);
    free(List);
    return TCL_ERROR;
  }

  return TCL_OK;
}

/*[ mpsa_DeleteListCmd
 *[ action:  fetch and delete list structure from hash table, delete hash
 *[          table entry and pointer to list within simulation structure
 *[ objects: takes name of list structure to be deleted
 *[ syntax:  CommandName ListName
 */

int mpsa_DeleteListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_List *List;

  if(argc < 2) {
    Tcl_AppendResult(interp, "Error - no listname specified", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetList(interp, argv[1], &List) != MPSA_OKAY) {
    return TCL_ERROR;
  }
  mpsa_RemoveListFromSimulation(List->Simulation, List);
  mpsa_ListClear(List);
  free(List->ListName);
  free(List);
  mpsa_RemoveListFromHash(argv[1]);

  return TCL_OK;
}

/*[ mpsa_CreateSimulationCmd
 *[ action:  creates simulation structure and creates a hash entry 
 *[          to access it.
 *[ objects: name of new simulation structure
 *[ syntax:  CommandName SimName
 */

int mpsa_CreateSimulationCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{  
  Tcl_HashEntry *SimEntry;
  mpsa_Simulation *Sim;
  int new;

  if(argc < 2) {
    Tcl_AppendResult(interp, "Error - no simulation name specified", (char *) NULL);
    return TCL_ERROR;
  }

  Sim = (mpsa_Simulation *) malloc (sizeof(mpsa_Simulation));

  mpsa_SimZero(Sim);
  
  
  SimEntry = Tcl_CreateHashEntry(&mpsa_SimHashTable, argv[1], &new);
  if(new) {
    Tcl_SetHashValue(SimEntry, Sim);
  } else {
    Tcl_AppendResult(interp, "Error registering sim", (char *) NULL);
    free(Sim);
    return TCL_ERROR;
  }

  return TCL_OK;
}

/*[ mpsa_DeleteSimulationCmd
 *[ action:  fetch and delete simulation structure, as well as all lists and
 *[          particles associated with it, deleteing hash entry
 *[ objects: simulation name
 *[ syntax:  CommandName SimName
 */

int mpsa_DeleteSimulationCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_Simulation *Sim;
  int i;
  
  if(argc < 2) {
    Tcl_AppendResult(interp, "Error - no simulation name specified", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetSim(interp, argv[1], &Sim) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  mpsa_DeletePcls(Sim->firstPcl);

  if(Sim->NLists != 0) {
    Tcl_AppendResult(interp, "Removing ", (char *) NULL);
    for(i = 0; i < Sim->NLists; i++) {
      mpsa_ListClear(Sim->Lists[i]);

      Tcl_AppendResult(interp, Sim->Lists[i]->ListName, " ", (char *) NULL);
     
      mpsa_RemoveListFromHash(Sim->Lists[i]->ListName);
      free(Sim->Lists[i]->ListName);
      free(Sim->Lists[i]);
    }
    free(Sim->Lists);
  }

  free(Sim);
  mpsa_RemoveSimFromHash(argv[1]);
  return TCL_OK;
}

/*[ mpsa_RegisterNewPcltypeCmd
 *[ action:  create a new particle definition according to users specification
 *[          using predefined pip types
 *[ objects: type name, number of pips and list of pip names
 *[ syntax:  CommandName typeName NumberOfPips PipName1 ... PipNameN
 */

int mpsa_RegisterNewPcltypeCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  Tcl_HashEntry *Entry;
  mpsa_ParticleDefn *NewDefn;
  int PipCount;
  mpsa_Pip **PipList, *Pip;
  int new, i, NameLength;

  if(argc < 3) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  NewDefn = (mpsa_ParticleDefn *) malloc (sizeof(mpsa_ParticleDefn));
  NewDefn->DynamicID = mpsa_GetMaxPclID();
  NameLength = strlen(argv[1]);
  NewDefn->Name = (char *) malloc ((NameLength + 1) * (sizeof(char)));
  NewDefn->Name = strcpy(NewDefn->Name, argv[1]);

  if(Tcl_GetInt(interp, argv[2], &PipCount) != TCL_OK) {
    Tcl_AppendResult(interp, "Error obtaining number of pips", (char *) NULL);
    free(NewDefn->Name);
    free(NewDefn);
    return TCL_ERROR;
  }

  Entry = Tcl_CreateHashEntry(&mpsa_ParticletypeHashTable, argv[1], &new);
  if(new) {
    Tcl_SetHashValue(Entry, NewDefn);
  } else {
    Tcl_AppendResult(interp, "Error registering particle type", (char *) NULL);
    free(NewDefn->Name);
    free(NewDefn);
    return TCL_ERROR;
  }

  NewDefn->NPips = PipCount;

  if(PipCount != (argc - 3)) {
    Tcl_AppendResult(interp, "Error obtaining pip names", (char *) NULL);
    free(NewDefn->Name);
    free(NewDefn);
    return TCL_ERROR;
  }

  if(PipCount == 0) {
    PipList = NULL;
  } else {
    PipList = (mpsa_Pip **) malloc (sizeof(mpsa_Pip *) * PipCount);
  }

  for(i = 0; i < PipCount; i++) {
    if(mpsa_GetPipDefn(interp, argv[3 + i], &Pip) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error obtaining pip definition", (char *) NULL);
      free(NewDefn->Name);
      free(PipList);
      free(NewDefn);
      return TCL_ERROR;
    }
    PipList[i] = Pip;
  }

  NewDefn->Piptypes = PipList;

  mpsa_IncrementMaxPclID();
  
  return TCL_OK;
}

/*[ mpsa_CheckPipDefinedCmd
 *[ action:  determine whether a certain pip has been defined
 *[ objects: name of a pip, returns pass (yes) or fail (no)
 *[ syntax:  CommandName PipName
 */

int mpsa_CheckPipDefinedCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_Pip *Pip;

  if(argc < 2) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetPipDefn(interp, argv[1], &Pip) != MPSA_OKAY) {
    Tcl_AppendResult(interp, "no", (char *) NULL);
    return TCL_OK;
  } else {
    Tcl_AppendResult(interp, "yes", (char *) NULL);
    return TCL_OK;
  }
}
