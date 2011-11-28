/* tree module internal header file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 1st september 2000
 * 
 */

#ifndef _TREE_PRIV
#define _TREE_PRIV

#define TREEOPENINGBASIC 100
#define TREEOPENINGOFFSET 101
#define TREEROOTEXACT 110
#define TREEROOTBARNES 111
#define TREEOPENCOM 120
#define TREEOPENGEOM 121

#include "tree_export.h"

extern Tcl_HashTable tree_TreeHashTable;

/*[ tree_SetGravParam
 *[ action:  set global gravity variables
 *[ objects: takes two floating variables
 */

extern int tree_SetGravParam(
  float theta,
  float eps
);

/*[ tree_PclInNode
 *[ action:  calculates whether a particle is within a node
 *[ objects: takes a particle and a node
 */

extern int tree_PclInNode(
  mpsa_Particle *Pcl,
  tree_Node *Node
);

/*[ tree_WhichNode
 *[ action:  returns the number of the sub node which Pcl is in
 *[ objects: takes a node and a particle
 */

extern int tree_WhichNode(
  mpsa_Particle *Pcl,
  tree_Node *Node
);

/*[ tree_OpenNode
 *[ action:  create eight sub nodes to the node being opened and
 *[          move the leaf to the appropriate one
 *[ objects: takes a node
 */

extern int tree_OpenNode(
  tree_Node *Node
);

/*[ tree_CloseNode
 *[ action:  reverse of open node!
 *[ objects: takes a node
 */

extern int tree_CloseNode(
  tree_Node *Node
);

/*[ tree_IsNodeOpen
 *[ action:  does exactly what it ways on the tin
 *[ objects: takes a node
 */

extern int tree_IsNodeOpen(
  tree_Node *Node
);

/*[ tree_CreateTree
 *[ action:  creates a new 'blank' tree trunk and pops it into a hash
 *[          table
 *[ objects: takes an interpreter and a name for the tree
 */

extern int tree_CreateTree(
  Tcl_Interp *interp,
  char *Name
);

/*[ tree_GetTree
 *[ action:  retrieves a tree pointer from a hash table
 *[ objects: takes an interpreter, name of a tree and returns a pointer
 */

extern int tree_GetTree(
  Tcl_Interp *interp,
  char *Name,
  tree_Node **Root
);

/*[ tree_DeleteTree
 *[ action:  removes the hash table entry and data from a tree
 *[ objects: takes a name
 */

extern int tree_DeleteTree(
  Tcl_Interp *interp,
  char *Name
);

/*[ tree_SetNodeSize
 *[ action:  set a tree node so that it is big enough to contain a whole
 *[          list of particles
 *[ objects: takes a tree node and a list of particles
 */

extern int tree_SetNodeSize(
  tree_Node *Node,
  mpsa_List *List
);

/*[ tree_LoadList
 *[ action:  load a list of particles into a tree
 *[ objects: takes a node and a list
 */

extern int tree_LoadList(
  tree_Node *Node,
  mpsa_List *List
);

/*[ tree_TreeCmd
 *[ action:  anything to do with trees
 *[ objects: probably takes trees and lists
 *[ syntax:  Tree ...stuff...
 */

extern int tree_TreeCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ tree_CalcCOM
 *[ action:  calculate the centres of mass of a tree
 *[ objects: takes a tree node
 */

extern int tree_CalcCOM(
  tree_Node *Node
);

/*[ tree_SetOption
 *[ action:  set one of the many flags in the tree code
 *[ objects: takes a name of a flag to set
 */

extern int tree_SetOption(
  char *Option
);

/*[ tree_PrintTree
 *[ action:  prints a tree to an interpreter
 *[ objects: takes an interpreter and a node
 */

extern int tree_PrintTree(
  Tcl_Interp *interp,
  tree_Node *Node
);

/*[ tree_WriteParameters
 *[ action:  write the values of the parameters to an interp
 *[ objects: takes an interp
 */

extern int tree_WriteParameters(
  Tcl_Interp *interp
);

/*[ tree_MergeParticles
 *[ action:  merges smaller particles
 *[ objects: takes a tree, simulation, radius and mass
 */

extern int tree_MergeParticles(
  tree_Node *Node,
  float Radius,
  float Mass
);

/*[ tree_GetParticle
 *[ action:  gets one particle from a tree
 *[ objects: takes a tree and a pointer to a pcl pointer
 */

extern int tree_GetParticle(
  tree_Node *Node,
  mpsa_Particle **Pcl
);

/*[ tree_DeleteParticles
 *[ action:  delete all particles in a tree
 *[ objects: takes a tree and a simulation
 */

extern int tree_DeleteParticles(
  tree_Node *Node
);

#endif
