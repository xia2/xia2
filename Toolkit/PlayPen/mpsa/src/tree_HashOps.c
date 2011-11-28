/* tree module hash operations file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 1st september 2000
 * 
 */

#include "tree_private.h"

/*[ tree_CreateTree
 *[ action:  creates a new 'blank' tree trunk and pops it into a hash
 *[          table
 *[ objects: takes an interpreter and a name for the tree
 */

int tree_CreateTree(
  Tcl_Interp *interp,
  char *Name
)
{
  Tcl_HashEntry *Entry;
  int new, i;
  tree_Node *Root;
  Root = (tree_Node *) malloc (sizeof(tree_Node));
  Root->Leaf = NULL;
  Root->Trunk = NULL;
  Root->Branch = NULL;
  Root->size = 1;
  for(i = 0; i < 3; i++) {
    Root->centre[i] = 0;
  }

  Entry = Tcl_CreateHashEntry(&tree_TreeHashTable, Name, &new);
  if(new) {
    Tcl_SetHashValue(Entry, Root);
  } else {
    free(Root);
    Tcl_AppendResult(interp, "Error setting hash table entry", (char *) NULL);
    return TREE_FAIL;
  }

  return TREE_OKAY;
}

/*[ tree_GetTree
 *[ action:  retrieves a tree pointer from a hash table
 *[ objects: takes an interpreter, name of a tree and returns a pointer
 */

int tree_GetTree(
  Tcl_Interp *interp,
  char *Name,
  tree_Node **Root
)
{
  Tcl_HashEntry *Entry;

  Entry = Tcl_FindHashEntry(&tree_TreeHashTable, Name);
  if(Entry == NULL) {
    Tcl_AppendResult(interp, "No tree of that name in the hash table", 
      (char *) NULL);
    return TREE_FAIL;
  } else {
    *Root = (tree_Node *) Tcl_GetHashValue(Entry);
  }

  return TREE_OKAY;
}

/*[ tree_DeleteTree
 *[ action:  removes the hash table entry and data from a tree
 *[ objects: takes a name
 */

int tree_DeleteTree(
  Tcl_Interp *interp,
  char *Name
)
{
  tree_Node *Node;
  Tcl_HashEntry *Entry;

  Entry = Tcl_FindHashEntry(&tree_TreeHashTable, Name);
  if(Entry == NULL) {
    Tcl_AppendResult(interp, "No tree of that name in the hash table", 
      (char *) NULL);
    return TREE_FAIL;
  } else {
    Node = (tree_Node *) Tcl_GetHashValue(Entry);
  }

  tree_CloseNode(Node);
  Tcl_DeleteHashEntry(Entry);
  free(Node);
  return TREE_OKAY;
}
