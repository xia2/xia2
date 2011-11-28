/* gsimII mpsa interface file v1.0
 * maintained by g.winter
 * 22nd august 2000
 *
 */

#include "mpsa_export.h"
#include "mpsa_private.h"

/*[ mpsa_RegisterNewPip
 *[ action:  register a new pip definition structure with the hash table
 *[          this is an external "interface" function
 *[ objects: takes a pointer to a new pip definition structure
 */

int mpsa_RegisterNewPip(
  mpsa_Pip *NewPip
)
{
  Tcl_HashEntry *Entry;
  int new;
  char *Name;

  Name = NewPip->Name;

  Entry = Tcl_CreateHashEntry(&mpsa_PiptypeHashTable, Name, &new);
  if(new) {
    Tcl_SetHashValue(Entry, NewPip);
    NewPip->DynamicID = mpsa_GetMaxPipID();
    mpsa_IncrementMaxPipID();
  } else {
    return MPSA_FAIL;
  }

  return MPSA_OKAY;
}
