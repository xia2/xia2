/* gsimII mpsa definition operations file v1.0
 * maintained by g.winter
 * 15th august 2000
 *
 */

#include "mpsa_export.h"
#include "mpsa_private.h"

int MaxPclID = 0;
int MaxPipID = 0;

/*[ mpsa_GetPclDefn
 *[ action:  get a particle definition structure from the appropriate hash
 *[          table, returning it as *Pcl
 *[ objects: takes a tcl interpreter, the name (hash table key), returns
 *[          a pointer to a definition structure
 */

int mpsa_GetPclDefn(
  Tcl_Interp *interp,
  char *typeName,
  mpsa_ParticleDefn **Pcl
)
{
  Tcl_HashEntry *Entry;
  Entry = Tcl_FindHashEntry(&mpsa_ParticletypeHashTable, typeName);
  if(Entry == NULL) {
    return MPSA_FAIL;
  } else {
    *Pcl = (mpsa_ParticleDefn *) Tcl_GetHashValue(Entry);
  }
  return MPSA_OKAY;
}

/*[ mpsa_GetPclDefnFromID
 *[ action:  get a particle definition structure from the appropriate hash
 *[          table, searching through the hash table
 *[ objects: takes a dynamic particle ID, returns a pointer to a definition 
 *[          structure
 */

int mpsa_GetPclDefnFromID(
  int ID,
  mpsa_ParticleDefn **type
)
{
  Tcl_HashEntry *Entry;
  Tcl_HashSearch Search;
  mpsa_ParticleDefn *Temptype;

  for(Entry = Tcl_FirstHashEntry(&mpsa_ParticletypeHashTable, &Search); 
    Entry != NULL; Entry = Tcl_NextHashEntry(&Search)) {
    Temptype = (mpsa_ParticleDefn *) Tcl_GetHashValue(Entry);
    if(Temptype->DynamicID == ID) {
      *type = Temptype;
      return MPSA_OKAY;
    }
  }

  return MPSA_FAIL;
}

/*[ mpsa_GetPipDefn
 *[ action:  get a pip definition structure from the appropriate hash table,
 *[          indexed by Label
 *[ objects: takes a tcl interpreter and a name, returns a pointer to a 
 *[          pip definition structure
 */

int mpsa_GetPipDefn(
  Tcl_Interp *interp,
  char *Label,
  mpsa_Pip **Pip
)
{
  Tcl_HashEntry *Entry;
  Entry = Tcl_FindHashEntry(&mpsa_PiptypeHashTable, Label);
  if(Entry == NULL) {
    return MPSA_FAIL;
  } else {
    *Pip = (mpsa_Pip *) Tcl_GetHashValue(Entry);
  }
  return MPSA_OKAY;
}

/*[ mpsa_GetMaxPclID
 *[ mpsa_IncrementMaxPclID
 *[ mpsa_GetMaxPipID
 *[ mpsa_IncrementMaxPipID
 *[ action:  set of wrapper functions to administer the allocation of 
 *[          dynamic type identifiers
 *[ objects: none
 */

int mpsa_GetMaxPclID()
{
  return MaxPclID;
}

int mpsa_IncrementMaxPclID()
{
  MaxPclID++;
  return MaxPclID;
}

int mpsa_GetMaxPipID()
{
  return MaxPipID;
}

int mpsa_IncrementMaxPipID()
{
  MaxPipID++;
  return MaxPipID;
}

/*[ mpsa_GetPclsWithPip
 *[ action:  get a list of particle definitions which include the 
 *[          given pip definition
 *[ objects: takes a pip definition, and returns an array of pointers to 
 *[          particle definitions and the number of elements of the array
 */

int mpsa_GetPclsWithPip(
  mpsa_Pip *Piptype,
  mpsa_ParticleDefn **typeList,
  int *NumberInList
)
{
  Tcl_HashEntry *Entry;
  Tcl_HashSearch Search;
  mpsa_ParticleDefn *Temptype;

  for(Entry = Tcl_FirstHashEntry(&mpsa_ParticletypeHashTable, &Search);
    Entry != NULL; Entry = Tcl_NextHashEntry(&Search)) {
    Temptype = (mpsa_ParticleDefn *) Tcl_GetHashValue(Entry);
    if(mpsa_DoesPclHavePip(Piptype, Temptype) == MPSA_OKAY) {
      mpsa_AddPcltypeToList(Temptype, typeList, *NumberInList);
      *NumberInList ++;
    }
  }

  return MPSA_OKAY;
}

/*[ mpsa_DoesPclHavePip
 *[ action:  test to see if a particle definition contains a given pip 
 *[          definition
 *[ objects: takes a pip definition and particle definition, returns yes/no
 */

int mpsa_DoesPclHavePip(
  mpsa_Pip *Piptype,
  mpsa_ParticleDefn *Pcltype
)
{
  int i;
  for(i = 0; i < Pcltype->NPips; i++) {
    if(Pcltype->Piptypes[i] == Piptype)
      {
	return MPSA_OKAY;
      }
  }

  return MPSA_FAIL;
}

/*[ mpsa_AddPcltypeToList
 *[ action:  add a particle definition to a list of particle definitions,
 *[          used in mpsa_GetPclsWithPip
 *[ objects: takes new particle definition and old list, and number of elements
 *[          returns new list
 */

int mpsa_AddPcltypeToList(
  mpsa_ParticleDefn *NewEntry,
  mpsa_ParticleDefn **List,
  int NumberInList
)
{
  int i;
  mpsa_ParticleDefn **TempList;

  TempList = (mpsa_ParticleDefn **) malloc (sizeof(mpsa_ParticleDefn *) * (NumberInList + 1));

  for(i = 0; i < NumberInList; i++) {
    TempList[i] = List[i];
  }

  TempList[NumberInList] = NewEntry;

  free(List);
  List = TempList;

  return MPSA_OKAY;
}

/*[ mpsa_GetPipPosition
 *[ action:  takes a particle definition and a pip definition, and returns
 *[          the position of the pip within the particle if applicable
 *[ objects: takes particle definition and pip definition, returns *position
 *[          if returns MPSA_FAIL, particle does not have required pip
 */

int mpsa_GetPipPosition(
  mpsa_ParticleDefn *Pcltype,
  mpsa_Pip *Piptype,
  int *Position
)
{
  int i;

  for(i = 0; i < Pcltype->NPips; i++) {
    if(Pcltype->Piptypes[i] == Piptype) {
      *Position = i;
      return MPSA_OKAY;
    }
  }

  return MPSA_FAIL;
}
