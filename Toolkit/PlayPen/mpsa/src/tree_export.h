/* tree module header file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 1st september 2000
 * 
 */

#ifndef _TREE
#define _TREE

#define TREE_OKAY 0
#define TREE_FAIL 1

#include "tcl.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>
#include "mpsa_export.h"

typedef struct tree_Node{
  struct tree_Node *Trunk;
  struct tree_Node *Branch;
  struct mpsa_Particle *Leaf;
  float size;
  float centre[3];
  float mass;
  float com[3];
  float offset;
} tree_Node;

/*[ tree_CalcGrav
 *[ action:  calculate the force of gravity from a tree to one particle
 *[ objects: takes a particle and a tree
 */

extern int tree_CalcGrav(
  mpsa_Particle *Particle,
  tree_Node *Node
);

/*[ tree_DirectGravCalc
 *[ action:  calculate force directly using n^2 formulation
 *[ objects: takes a particle and a list of particles
 */

extern int tree_DirectGravCalc(
  mpsa_Particle *Pcl,
  mpsa_List *List
);

#endif
