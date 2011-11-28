/* tree module operations file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 1st september 2000
 * 
 * modified 25th september:
 * made tree-setsize randomized to prevent symmetries building up and
 * affecting the physics. note that the same change must be applied to 
 * quadtree, and this will prevent them from being identical in their operation
 *
 * modified 29th september:
 * made tree setsize operate on the same premise as barnes did, removing
 * any randomness
 *
 * modified 2nd october:
 * modified tree to detect incest as a back up plan. this shouldn't happen
 * but just in case it does, have added this precaution
 * 
 * efficiency saving also implemented in gravity calculation so that if 
 * Node->Leaf == NULL no calculations are done
 *
 * modified 3rd october:
 * change to barnes root node size setting
 *
 * added switch function to parse all of the different switches which are 
 * necessary in order to maintain compatibility with barnes code and allow
 * a detailed analysis of the effects of different options
 * this will make greatest impact on the root node and opening criteria
 *
 * modified 5th october final
 * gravity now working correctly - previous errors due to incorrect setting 
 * of epsilon = theta by accident in the setting command. now fixed so all 
 * works well. now removing all excess checks
 */

#include "tree_private.h"
#include "mpsa_export.h"

float GravTheta = 0.5;
float GravEpsilonSQ = 0.01;
int TreeOpening = TREEOPENINGOFFSET;
int RootType = TREEROOTEXACT;
int TreeDist = TREEOPENCOM;
float BarnesSize = 1;

/*[ tree_SetGravParam
 *[ action:  set global gravity variables
 *[ objects: takes two floating variables
 */

int tree_SetGravParam(
  float theta,
  float eps
)
{
  GravTheta = theta;
  GravEpsilonSQ = eps * eps;
  return TREE_OKAY;
}

/*[ tree_PclInNode
 *[ action:  calculates whether a particle is within a node
 *[ objects: takes a particle and a node
 */

int tree_PclInNode(
  mpsa_Particle *Pcl,
  tree_Node *Node
)
{
  int i;
  float HalfSize;

  HalfSize = Node->size * 0.5;
  for(i = 0; i < 3; i++) {
    if(fabs(Pcl->x[i] - Node->centre[i]) > HalfSize) {
      return TREE_FAIL;
    }
  }
  return TREE_OKAY;
}

/*[ tree_WhichNode
 *[ action:  returns the number of the sub node which Pcl is in
 *[ objects: takes a node and a particle
 */

int tree_WhichNode(
  mpsa_Particle *Pcl,
  tree_Node *Node
)
{
  int ThisNode = 0;
  if(Pcl->x[0] > Node->centre[0]) {
    ThisNode += 1;
  }
  if(Pcl->x[1] > Node->centre[1]) {
    ThisNode += 2;
  }
  if(Pcl->x[2] > Node->centre[2]) {
    ThisNode += 4;
  }
  return ThisNode;
}

/*[ tree_OpenNode
 *[ action:  create eight sub nodes to the node being opened and
 *[          move the leaf to the appropriate one
 *[ objects: takes a node
 */

int tree_OpenNode(
  tree_Node *Node
)
{
  int i, j, x, y, z;
  float HalfSize;

  if(Node->Branch != NULL) {
    return TREE_FAIL;
  }

  HalfSize = 0.5 * Node->size;

  Node->Branch = (tree_Node *) malloc (sizeof(tree_Node) * 8);
  for(i = 0; i < 8; i++) {
    Node->Branch[i].Branch = NULL;
    Node->Branch[i].Leaf = NULL;
    for(j = 0; j < 3; j++) {
      Node->Branch[i].centre[j] = Node->centre[j];
      Node->Branch[i].com[j] = 0;
    }
    Node->Branch[i].size = HalfSize;
    Node->Branch[i].Trunk = Node;
    Node->Branch[i].mass = 0;
    Node->Branch[i].offset = 0;
  }

  for(x = 0; x < 2; x++) {
    for(y = 0; y < 2; y++) {
      for(z = 0; z < 2; z++) {
	i = 4 * z + 2 * y + x;
	Node->Branch[i].centre[0] += (x - 0.5) * HalfSize;
	Node->Branch[i].centre[1] += (y - 0.5) * HalfSize;
	Node->Branch[i].centre[2] += (z - 0.5) * HalfSize;
      }
    }
  }

  j = tree_WhichNode(Node->Leaf, Node);
  Node->Branch[j].Leaf = Node->Leaf;
  Node->Leaf = NULL;
  return TREE_OKAY;
}

/*[ tree_CloseNode
 *[ action:  reverse of open node!
 *[ objects: takes a node
 */

int tree_CloseNode(
  tree_Node *Node
)
{
  int i;
  Node->Leaf = NULL;
  if(Node->Branch == NULL) {
    return TREE_OKAY;
  } else {
    for(i = 0; i < 8; i++) {
      tree_CloseNode(&(Node->Branch[i]));
    }
    free(Node->Branch);
    Node->Branch = NULL;
  } 
  return TREE_OKAY;
}

/*[ tree_IsNodeOpen
 *[ action:  does exactly what it ways on the tin
 *[ objects: takes a node
 */

int tree_IsNodeOpen(
  tree_Node *Node
)
{
  if(Node->Branch == NULL) {
    return TREE_FAIL;
  } else {
    return TREE_OKAY;
  }
}

/*[ tree_SetNodeSize
 *[ action:  set a tree node so that it is big enough to contain a whole
 *[          list of particles
 *[ objects: takes a tree node and a list of particles
 */

int tree_SetNodeSize(
  tree_Node *Node,
  mpsa_List *List
)
{
  mpsa_Link *Link;
  int i;
  float upper[3], lower[3], x, size = 0;

  /* change 29th september see if position of root node is important */
  /* if it is, will have to formulate a proper way of setting the    */
  /* position.                                                       */
  /* changed to barnes method - commented out the old for the moment */
  /* no put back with an option! */
 
  if(RootType == TREEROOTEXACT) {
    for(i = 0; i < 3; i++) {
      lower[i] = List->firstLink->Pcl->x[i];
      upper[i] = List->firstLink->Pcl->x[i];
    }
    
    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      for(i = 0; i < 3; i++) {
	x = Link->Pcl->x[i];
	if(x < lower[i]) {
	  lower[i] = x;
	}
	if(x > upper[i]) {
	  upper[i] = x;
	}
      }
    }
    
    for(i = 0; i < 3; i++) {
      Node->centre[i] = 0.5 * (upper[i] + lower[i]);
      if((x = upper[i] - lower[i]) > size) {
	size = x;
      }
    }
    
    Node->size = size;
    
    return TREE_OKAY;

  } else {
    
    size = BarnesSize;
    
    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    for(i = 0; i < 3; i++) {
      if(fabs(Link->Pcl->x[i]) > size) {
	size *= 2;
      }
    }
    }
    
    for(i = 0; i < 3; i++) {
      Node->centre[i] = 0;
    }  
    
  Node->size = 2 * size;
  
  BarnesSize = size;

  return TREE_OKAY;
  }
}

/*[ tree_LoadList
 *[ action:  load a list of particles into a tree
 *[ objects: takes a node and a list
 */

int tree_LoadList(
  tree_Node *Node,
  mpsa_List *List
)
{
  mpsa_Link *Link;
  mpsa_Particle *Pcl;
  tree_Node *ThisNode;
  int i;

  tree_SetNodeSize(Node, List);

  for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    ThisNode = Node;
    Pcl = Link->Pcl;

    while(tree_IsNodeOpen(ThisNode) == TREE_OKAY) {
      i = tree_WhichNode(Pcl, ThisNode);
      ThisNode = &(ThisNode->Branch[i]);
    }

    while(ThisNode->Leaf != NULL) {
      if(tree_OpenNode(ThisNode) != TREE_OKAY) {
	return TREE_FAIL;
      }

      i = tree_WhichNode(Pcl, ThisNode);
      ThisNode = &(ThisNode->Branch[i]);
    }

    ThisNode->Leaf = Pcl;
  }

  return TREE_OKAY;

}

/*[ tree_CalcCOM
 *[ action:  calculate the centres of mass of a tree
 *[ objects: takes a tree node
 */

int tree_CalcCOM(
  tree_Node *Node
)
{
  float mass = 0;
  float drmax = 0;
  float x[3], drtemp;
  int i, j;

  for(i = 0; i < 3; i++) {
    x[i] = 0;
  }

  if(tree_IsNodeOpen(Node) == TREE_OKAY) {
    for(i = 0; i < 8; i++) {
      if(tree_CalcCOM(&(Node->Branch[i])) != TREE_OKAY) {
	return TREE_FAIL;
      }
      mass += Node->Branch[i].mass;
      for(j = 0; j < 3; j++) {
	x[j] += Node->Branch[i].mass * Node->Branch[i].com[j];
      }
    }
    for(j = 0; j < 3; j++) {
      Node->com[j] = x[j] / mass;
    }
    Node->mass = mass;
    drmax = 0;
    for(j = 0; j < 3; j++) {
      drtemp = Node->com[j] - Node->centre[j] + 0.5 * Node->size;
      if(drtemp > (Node->size - drtemp)) {
	drmax += drtemp * drtemp;
      } else {
	drmax += (Node->size - drtemp) * (Node->size - drtemp);
      }
    }
    Node->offset = sqrt(drmax);
  } else if(Node->Leaf != NULL) {
    Node->mass = Node->Leaf->mass;
    for(j = 0; j < 3; j++) {
      Node->com[j] = Node->Leaf->x[j];
    }
  } else {
    Node->mass = 0;
    for(j = 0; j < 3; j++) {
      Node->com[j] = 0;
    }
  }
  return TREE_OKAY;
}

/*[ tree_CalcGrav
 *[ action:  calculate the force of gravity from a tree to one particle
 *[ objects: takes a particle and a tree
 */

int tree_CalcGrav(
  mpsa_Particle *Particle,
  tree_Node *Node
)
{
  int i;
  float dsq, dr, dx[3], compare, dsqtwo;
  float force, PNDistSQ;

  if(Node->mass == 0) {
    return TREE_OKAY;
  }

  if(Node->Leaf == Particle) {
    /* prevent self interaction in the obvious case */
    return TREE_OKAY;
  }

  dsq = 0;
  for(i = 0; i < 3; i++) {
    dx[i] = (Particle->x[i] - Node->com[i]);
    dsq += dx[i] * dx[i];
  }

  if(TreeOpening == TREEOPENINGBASIC) {
    compare = Node->size;
  } else if(TreeOpening == TREEOPENINGOFFSET) {
    compare = Node->offset;
  } else {
    compare = Node->size;
  }

  if(TreeDist == TREEOPENCOM) {
    PNDistSQ = dsq;
  } else if(TreeDist == TREEOPENGEOM) {
    PNDistSQ = 0;
    for(i = 0; i < 3; i++) {
      PNDistSQ += (Particle->x[i] - Node->centre[i]) * (
        Particle->x[i] - Node->centre[i]);
    }
  } else {
    PNDistSQ = dsq;
  }

  /* two versions of this, to enable theta > 1 for the foolhardy */
  if(GravTheta >= 1) {
    if((GravTheta * GravTheta * PNDistSQ) < (compare * compare)) {
      
      /* node too close - open it! */
      
      if(tree_IsNodeOpen(Node) == TREE_OKAY) {
	for(i = 0; i < 8; i++) {
	  tree_CalcGrav(Particle, &(Node->Branch[i]));
	}
      } else {
	
	/* no subnodes so just use the centre of mass ie the particle */
	/* note - Node->Leaf != Pcl from above check */
	
	dsqtwo = dsq + GravEpsilonSQ;
	dr = sqrt(dsqtwo);
	force = Node->mass / dsqtwo;
	for(i = 0; i < 3; i++) {
	  Particle->a[i] -= force * dx[i] / dr;
	}
	
	Particle->phi -= Node->mass / dr;
      }
    } else if(tree_PclInNode(Particle, Node) != TREE_OKAY) {
      
      /* if the node is far enough away and the particle is not in it then..*/
      
      dsqtwo = dsq + GravEpsilonSQ;
      dr = sqrt(dsqtwo);
      force = Node->mass / dsqtwo;
      for(i = 0; i < 3; i++) {
	Particle->a[i] -= force * dx[i] / dr;
      }
      
      Particle->phi -= Node->mass / dr;
      
    } else {
      
      /* else force the node to open anyway */
      
      if(tree_IsNodeOpen(Node) == TREE_OKAY) {
	for(i = 0; i < 8; i++) {
	  tree_CalcGrav(Particle, &(Node->Branch[i]));
	}
      } else {
	
	/* at this stage, Node->Leaf still can't be Pcl */
	
	dsqtwo = dsq + GravEpsilonSQ;
	dr = sqrt(dsqtwo);
	force = Node->mass / dsqtwo;
	for(i = 0; i < 3; i++) {
	  Particle->a[i] -= force * dx[i] / dr;
	}
	
	Particle->phi -= Node->mass / dr;
      }
    }
  } else {

    /* ie, we're being sensible here and having theta reasonable */

    if((GravTheta * GravTheta * PNDistSQ) < (compare * compare)) {
      
      /* node too close - open it! */
      
      if(tree_IsNodeOpen(Node) == TREE_OKAY) {
	for(i = 0; i < 8; i++) {
	  tree_CalcGrav(Particle, &(Node->Branch[i]));
	}
      } else {
	
	/* no subnodes so just use the centre of mass ie the particle */
	/* note - Node->Leaf != Pcl from above check */
	
	dsqtwo = dsq + GravEpsilonSQ;
	dr = sqrt(dsqtwo);
	force = Node->mass / dsqtwo;
	for(i = 0; i < 3; i++) {
	  Particle->a[i] -= force * dx[i] / dr;
	}
	
	Particle->phi -= Node->mass / dr;
      }

    } else {
      
      /* if the node is far enough away and the particle is not in it then..*/
      
      dsqtwo = dsq + GravEpsilonSQ;
      dr = sqrt(dsqtwo);
      force = Node->mass / dsqtwo;
      for(i = 0; i < 3; i++) {
	Particle->a[i] -= force * dx[i] / dr;
      }
      
      Particle->phi -= Node->mass / dr;
      
    }
  }

  return TREE_OKAY;
}

/*[ tree_DirectGravCalc
 *[ action:  calculate force directly using n^2 formulation
 *[ objects: takes a particle and a list of particles
 */

int tree_DirectGravCalc(
  mpsa_Particle *Pcl,
  mpsa_List *List
)
{
  int i;
  float dsq, dr, dx[3], force;
  mpsa_Link *Link;

  for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    if(Link->Pcl == Pcl) {
      /* do nothing */
    } else {
      dsq = 0;
      for(i = 0; i < 3; i++) {
	dx[i] = Pcl->x[i] - Link->Pcl->x[i];
	dsq += dx[i] * dx[i];
      }
      dsq += GravEpsilonSQ;
      dr = sqrt(dsq);
      force = Link->Pcl->mass / dsq;
      for(i = 0; i < 3; i++) {
	Pcl->a[i] -= force * dx[i] / dr;
      }
    }
  }

  return TREE_OKAY;
}
      
/*[ tree_SetOption
 *[ action:  set one of the many flags in the tree code
 *[ objects: takes a name of a flag to set
 */

extern int tree_SetOption(
  char *Option
)
{
  if((strcmp(Option, "OpenBasic") == 0) ||
     (strcmp(Option, "openbasic") == 0)) {
    TreeOpening = TREEOPENINGBASIC;
  } else if((strcmp(Option, "OpenSW") == 0) ||
	    (strcmp(Option, "opensw") == 0)) {
    TreeOpening = TREEOPENINGOFFSET;
  } else if((strcmp(Option, "DistGeom") == 0) ||
	    (strcmp(Option, "distgeom") == 0)) {
    TreeDist = TREEOPENGEOM;
  } else if((strcmp(Option, "DistCOM") == 0) ||
	    (strcmp(Option, "distcom") == 0)) {
    TreeDist = TREEOPENCOM;
  } else if((strcmp(Option, "RootBarnes") == 0) ||
	    (strcmp(Option, "rootbarnes") == 0)) {
    RootType = TREEROOTBARNES;
  } else if((strcmp(Option, "RootExact") == 0) ||
	    (strcmp(Option, "rootexact") == 0)) {
    RootType = TREEROOTEXACT;
  } else {
    return TREE_FAIL;
  }

  return TREE_OKAY;
}


/*[ tree_PrintTree
 *[ action:  prints a tree to an interpreter
 *[ objects: takes an interpreter and a node
 */

int tree_PrintTree(
  Tcl_Interp *interp,
  tree_Node *Node
)
{
  int i;
  char size[15], mass[15], px[15], py[15], pz[15];
  char cx[15], cy[15], cz[15], address[15], count[4];

  sprintf(address, "%d ", (int) Node);

  sprintf(size, "%e ", Node->size);
  sprintf(mass, "%e ", Node->mass);
  
  sprintf(cx, "%e ", Node->centre[0]);
  sprintf(cy, "%e ", Node->centre[1]);
  sprintf(cz, "%e ", Node->centre[2]);
  
  sprintf(px, "%e ", Node->com[0]);
  sprintf(py, "%e ", Node->com[1]);
  sprintf(pz, "%e ", Node->com[2]);

  Tcl_AppendResult(interp, address, size, mass, cx, cy, cz, px, py, pz, 
    (char *) NULL);

  if(tree_IsNodeOpen(Node) == TREE_OKAY) {
    for(i = 0; i < 8; i++) {
      sprintf(count, "%d ", i);
      Tcl_AppendResult(interp, count, (char *) NULL);
      if(tree_PrintTree(interp, &(Node->Branch[i]))!= TREE_OKAY) {
	return TREE_FAIL;
      }
      Tcl_AppendResult(interp, "\n", (char *) NULL);
    }
  } else if(Node->Leaf != NULL) {
    sprintf(px, "%e ", Node->Leaf->x[0]);
    sprintf(py, "%e ", Node->Leaf->x[1]);
    sprintf(pz, "%e ", Node->Leaf->x[2]);
    sprintf(mass, "%e ", Node->Leaf->mass);
    Tcl_AppendResult(interp, mass, px, py, pz, (char *) NULL);
  }

  return TREE_OKAY;
}

/*[ tree_WriteParameters
 *[ action:  write the values of the parameters to an interp
 *[ objects: takes an interp
 */

int tree_WriteParameters(
  Tcl_Interp *interp
)
{
  char OutTheta[15], OutEpsSQ[15];

  sprintf(OutTheta, "%e", GravTheta);
  sprintf(OutEpsSQ, "%e", GravEpsilonSQ);

  Tcl_AppendResult(interp, OutTheta, " ", OutEpsSQ, (char *) NULL);
  return TREE_OKAY;
}

/*[ tree_MergeParticles
 *[ action:  merges smaller particles
 *[ objects: takes a tree, simulation, radius and mass
 */

int tree_MergeParticles(
  tree_Node *Node,
  float Radius,
  float Mass
)
{
  if((Node->size < Radius) && 
     (Node->mass < Mass)) {

    if(Node->Branch == NULL) {
      /* only one particle anyhow */
      return TREE_OKAY;
    } else {
      int i;
      mpsa_Particle *Particle = NULL;

      /* getting a particle removes it from the tree */

      tree_GetParticle(Node, &Particle);
      for(i = 0; i < 3; i++) {
	Particle->x[i] = Node->com[i];
      }
      Particle->mass = Node->mass;

      /* so that it is not deleted here */

      tree_DeleteParticles(Node);
      return TREE_OKAY;
    }
  } else {
    int i;
    for(i = 0; i < 8; i++) {
      if(Node->Branch != NULL) {
	tree_MergeParticles(&(Node->Branch[i]), Radius, Mass);
      }
    }
  }

  return TREE_OKAY;
}

/*[ tree_GetParticle
 *[ action:  gets one particle from a tree
 *[ objects: takes a tree and a pointer to a pcl pointer
 */

int tree_GetParticle(
  tree_Node *Node,
  mpsa_Particle **Pcl
)
{
  if(Node->Leaf != NULL) {
    *Pcl = Node->Leaf;
    Node->Leaf = NULL;
    return TREE_OKAY;
  } else if(Node->Branch != NULL) {
    int i;
    for(i = 0; i < 8; i++) {
      if(tree_GetParticle(&(Node->Branch[i]), Pcl) != TREE_OKAY) {
	/* keep going */
      } else {
	return TREE_OKAY;
      }
    }
  } else {
    return TREE_FAIL;
  }

  return TREE_OKAY;
}

/*[ tree_DeleteParticles
 *[ action:  delete all particles in a tree
 *[ objects: takes a tree and a simulation
 */

int tree_DeleteParticles(
  tree_Node *Node
)
{

  /* this is nasty because it will mangle the internal particle structure */
  /* in the simulation structure */

  if(Node->Leaf != NULL) {
    Node->Leaf->flag = 1;
  } else if(Node->Branch != NULL) {
    int i;
    for(i = 0; i < 8; i++) {
      tree_DeleteParticles(&(Node->Branch[i]));
    }
  }

  return TREE_OKAY;
}
