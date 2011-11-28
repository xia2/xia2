/* gsimII list operations file v1.0
 * maintained by g.winter
 * 15th august 2000
 * 
 */ 

#include "mpsa_export.h"
#include "mpsa_private.h"

/*[ mpsa_AddListToSimulation
 *[ action:  add a newly defined list structure to a simulation structure
 *[ objects: takes a pointer to a simulation and a pointer to the list
 */

int mpsa_AddListToSimulation(
  mpsa_Simulation *Simulation,
  mpsa_List *List
)
{
  mpsa_List **NewListList;
  int i, n;

  n = Simulation->NLists + 1;
  NewListList = (mpsa_List **) malloc (sizeof(mpsa_List *) * n);

  for(i = 0; i < n - 1; i++) {
    NewListList[i] = Simulation->Lists[i];
  }

  NewListList[n - 1] = List;

  free(Simulation->Lists);
  Simulation->Lists = NewListList;

  Simulation->NLists ++;

  return MPSA_OKAY;

}

/*[ mpsa_RemoveListFromSimulation
 *[ action:  remove list pointer from list within simulation structure
 *[          in the process of deleteing the list
 *[ objects: takes a pointer to a simulation and a pointer to the list
 */

int mpsa_RemoveListFromSimulation(
  mpsa_Simulation *Simulation,
  mpsa_List *List
)
{
  mpsa_List **NewListList;
  mpsa_List *TempList;
  int i, j, n;

  n = Simulation->NLists - 1;

  if(n < 0) {
    return MPSA_FAIL;
  } else {
    if(mpsa_IsListInSim(Simulation, List) == MPSA_OKAY) {
      NewListList = (mpsa_List **) malloc (sizeof(mpsa_List *) * n);
      j = 0;
      for(i = 0; i < n + 1; i++) {
	if((TempList = Simulation->Lists[i]) != List) {
	  NewListList[j] = TempList;
	  j++;
	}
      }
      free(Simulation->Lists);
      Simulation->Lists = NewListList;
      Simulation->NLists --;
    } else {
      return MPSA_FAIL;
    }
  }

  return MPSA_OKAY;
}

/*[ mpsa_IsListInSim
 *[ action:  tests to see if a given list pointer is associated with a
 *[          simulation, returning either MPSA_OKAY = yes or MPSA_FAIL = no
 *[ objects: takes a pointer to a simulation and a pointer to the list
 */

int mpsa_IsListInSim(
  mpsa_Simulation *Simulation,
  mpsa_List *List
)
{
  int i, n;

  n = Simulation->NLists;

  for(i = 0; i < n; i++) {
    if(Simulation->Lists[i] == List) {
      return MPSA_OKAY;
    }
  }

  return MPSA_FAIL;
}

/*[ mpsa_ListClear
 *[ action:  clear all pointer entries in list structure
 *[ objects: takes pointer to list structure
 */

int mpsa_ListClear(
  mpsa_List *List
)
{
  mpsa_Link *Link;
  mpsa_Link *PlaceHolder;

  for(Link = List->firstLink; Link != NULL; Link = PlaceHolder) {
    PlaceHolder = Link->nextLink;
    free(Link);
  }

  List->firstLink = NULL;
  List->lastLink = NULL;
  List->NElements = 0;

  return MPSA_OKAY;
}

/*[ mpsa_extractSimToList
 *[ action:  extract all particles of a given type from a simulation 
 *[          to a list, counting them as it goes        
 *[ objects: takes pointer to a simulation and pointer to a list, a type 
 *[          described by an integer and returns the number of extractions
 */

int mpsa_extractSimToList(
  mpsa_Simulation *Simulation,
  mpsa_List *List,
  int *InList,
  int type
)
{
  mpsa_Particle *Pcl;
  int i = 0;

  for(Pcl = Simulation->firstPcl; Pcl != NULL; Pcl = 
    Pcl->nextPcl) {
    if(Pcl->type == type) {
      mpsa_AppendToList(List, Pcl);
      i++;
    }
  }

  *InList = i;

  return MPSA_OKAY;
}

/*[ mpsa_extractAllToList
 *[ action:  extract all particles associated with a simulation structure
 *[          to a list
 *[ objects: takes a pointer to a simulation and a pointer to a list, returning
 *[          number of extractions
 */

int mpsa_extractAllToList(
  mpsa_Simulation *Simulation,
  mpsa_List *List,
  int *InList
)
{
  mpsa_Particle *Pcl;
  int i = 0;

  for(Pcl = Simulation->firstPcl; Pcl != NULL; Pcl = 
    Pcl->nextPcl) {
    mpsa_AppendToList(List, Pcl);
    i++;
  }

  *InList = i;

  return MPSA_OKAY;
}
  
/*[ mpsa_AppendToList
 *[ action:  add a particle pointer to a list structure
 *[ objects: a pointer to a list, and a pointer to the particle to be added
 */

int mpsa_AppendToList(
  mpsa_List *List,
  mpsa_Particle *Pcl
)
{
  mpsa_Link *NewLink;

  NewLink = (mpsa_Link *) malloc (sizeof(mpsa_Link));
  NewLink->Pcl = Pcl;
  NewLink->nextLink = NULL;

  if(List->lastLink == NULL) {
    List->firstLink = NewLink;
    List->lastLink = NewLink;
    List->NElements ++;
  } else {
    List->lastLink->nextLink = NewLink;
    List->lastLink = NewLink;
    List->NElements ++;
  }

  return MPSA_OKAY;
}

/*[ mpsa_ListHashEntryCreate
 *[ action:  create a hash entry in the list hash table
 *[ objects: takes the name of a list and a pointer to that list
 */ 

int mpsa_ListHashEntryCreate(
  char *Name,
  mpsa_List *List
)
{
  int new;
  Tcl_HashEntry *ListEntry;
  
  ListEntry = Tcl_CreateHashEntry(&mpsa_ListHashTable, Name, &new);
  if(new) {
    Tcl_SetHashValue(ListEntry, List);
    return MPSA_OKAY;
  } else {
    free(List->ListName);
    free(List);
    return MPSA_FAIL;
  }
}

/*[ mpsa_ListDelete
 *[ action:  deletes all trace of a list
 *[ objects: takes a pointer to a simulation
 */

int mpsa_ListDelete(
  mpsa_List *List
)
{
  mpsa_RemoveListFromSimulation(List->Simulation, List);
  mpsa_ListClear(List);
  free(List->ListName);
  free(List);

  return MPSA_OKAY;
}
