/* tree module initialisation file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 1st september 2000
 * 
 */

#include "tree_private.h"

/*
 * hash tables to hold dynamically created trees
 */

Tcl_HashTable tree_TreeHashTable;

int Tree_Init(
  Tcl_Interp *interp
)
{
  Tcl_InitHashTable(&tree_TreeHashTable, TCL_STRING_KEYS);

  Tcl_CreateCommand(interp, "::tree::tree", tree_TreeCmd,
    (ClientData) NULL, (void(*)()) NULL);

  return TCL_OK;
}
