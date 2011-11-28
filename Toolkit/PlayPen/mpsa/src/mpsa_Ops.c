/* gsimII mpsa operations file v1.0
 * maintained by g.winter
 * 15th august 2000
 *
 */

#include "mpsa_export.h"
#include "mpsa_private.h"

/*[ mpsa_ListCreate
 *[ action:  create a list of given name and attatch it to a simulation
 *[ objects: simulation pointer, name and pointer to list pointer
 */

int mpsa_ListCreate(
  mpsa_Simulation *Simulation,
  char *ListName,
  mpsa_List **NewList
)
{
  mpsa_List *List;
  int NameLength;

  List = (mpsa_List *) malloc (sizeof(mpsa_List));
  List->Simulation = Simulation;
  List->firstLink = NULL;
  List->lastLink = NULL;
  List->NElements = 0;
  NameLength = strlen(ListName);
  List->ListName = (char *) malloc ((NameLength + 1) * sizeof(char));
  List->ListName = strcpy(List->ListName, ListName);
  mpsa_AddListToSimulation(Simulation, List);

  *NewList = List;

  return MPSA_OKAY;
}

/*[ mpsa_GetList
 *[ action:  gets a list structure pointer from the appropriate hash table
 *[          and returns it in *List
 *[ objects: takes name and tcl interpreter, returns a list pointer
 */

int mpsa_GetList(
  Tcl_Interp *interp,
  char *Label,
  mpsa_List **List
)
{
  Tcl_HashEntry *Entry;
  Entry = Tcl_FindHashEntry(&mpsa_ListHashTable, Label);
  if(Entry == NULL) {
    Tcl_AppendResult(interp, "Error obtaining list named ", Label, 
      (char *) NULL);
    return MPSA_FAIL;
  } else {
    *List = (mpsa_List *) Tcl_GetHashValue(Entry);
  }

  return MPSA_OKAY;
}

/*[ mpsa_GetSim
 *[ action:  get a simulation structure pointer from the hash table and 
 *[          returns it in *Simulation
 *[ objects: takes tcl interpreter and name of the simulation, returns pointer
 */

int mpsa_GetSim(
  Tcl_Interp *interp,
  char *Label,
  mpsa_Simulation **Simulation
)
{
  Tcl_HashEntry *Entry;
  Entry = Tcl_FindHashEntry(&mpsa_SimHashTable, Label);
  if(Entry == NULL) {
    Tcl_AppendResult(interp, "Error obtaining simulation named ", Label,
      (char *) NULL);
    return MPSA_FAIL;
  } else {
    *Simulation = (mpsa_Simulation *) Tcl_GetHashValue(Entry);
  }
  return MPSA_OKAY;
}

/*[ mpsa_RemoveListFromHash
 *[ action:  remove list hash entry with the key ListName
 *[          used when deleteing lists
 *[ objects: name of list
 */

int mpsa_RemoveListFromHash(
  char *ListName
)
{
  Tcl_HashEntry *Entry;
  Entry = Tcl_FindHashEntry(&mpsa_ListHashTable, ListName);
  if(Entry == NULL) {
    return MPSA_FAIL;
  } else {
    Tcl_DeleteHashEntry(Entry);
  }

  return MPSA_OKAY;
}

/*[ mpsa_RemoveSimFromHash
 *[ action:  remove simulation hash entry with the key SimName
 *[          used when deleting simulations
 *[ objects: name of simulation
 */

int mpsa_RemoveSimFromHash(
  char *SimName
)
{
  Tcl_HashEntry *Entry;
  Entry = Tcl_FindHashEntry(&mpsa_SimHashTable, SimName);
  if(Entry == NULL) {
    return MPSA_FAIL;
  } else {
    Tcl_DeleteHashEntry(Entry);
  }

  return MPSA_OKAY;
}

