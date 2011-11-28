/* tree module command file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 1st september 2000
 * 
 * 
 */

#include "tree_private.h"

/*[ tree_TreeCmd
 *[ action:  anything to do with trees
 *[ objects: probably takes trees and lists
 *[ syntax:  Tree ...stuff...
 */

int tree_TreeCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  if(argc < 2) {
    Tcl_AppendResult(interp, "Expecting one of create/delete/load/clear/setup",
      (char *) NULL);
    return TCL_ERROR;
  }

  if((strcmp(argv[1], "Create") == 0) ||
     (strcmp(argv[1], "create") == 0)) {
    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires name of a tree to make", 
        (char *) NULL);
      return TCL_ERROR;
    }
    if(tree_CreateTree(interp, argv[2]) != TREE_OKAY) {
      return TCL_ERROR;
    }

    return TCL_OK;
  } else if((strcmp(argv[1], "Delete") == 0) ||
	    (strcmp(argv[1], "delete") == 0)) {
    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires name of a tree to delete", 
	(char *) NULL);
      return TCL_ERROR;
    }
    if(tree_DeleteTree(interp, argv[2]) != TREE_OKAY) {
      return TCL_ERROR;
    }
    return TCL_OK;
  } else if((strcmp(argv[1], "Load") == 0) ||
	    (strcmp(argv[1], "load") == 0)) {
    mpsa_List *List;
    tree_Node *Node;

    if(argc < 4) {
      Tcl_AppendResult(interp, argv[1], "requires a tree and a list", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(tree_GetTree(interp, argv[2], &Node) != TREE_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[3], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(tree_LoadList(Node, List) != TREE_OKAY) {
      Tcl_AppendResult(interp, "Error loading list", (char *) NULL);
      return TCL_ERROR;
    }

    return TCL_OK;
  } else if((strcmp(argv[1], "Clear") == 0) ||
	    (strcmp(argv[1], "clear") == 0)) {
    tree_Node *Node;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires a tree", (char * ) NULL);
      return TCL_ERROR;
    }
  
    if(tree_GetTree(interp, argv[2], &Node) != TREE_OKAY) {
      return TCL_ERROR;
    }

    if(tree_CloseNode(Node) != TREE_OKAY) {
      Tcl_AppendResult(interp, "Error clearing tree", (char *) NULL);
      return TCL_ERROR;
    }

    return TCL_OK;
  } else if((strcmp(argv[1], "CalcCOM") == 0) ||
	    (strcmp(argv[1], "calccom") == 0)) {
    tree_Node *Node;
    char result_mass[15];

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " needs a tree", (char *) NULL);
      return TCL_ERROR;
    }

    if(tree_GetTree(interp, argv[2], &Node) != TREE_OKAY) {
      return TCL_ERROR;
    }

    if(tree_CalcCOM(Node) != TREE_OKAY) {
      Tcl_AppendResult(interp, "Error calculating centre of mass of tree", 
	(char *) NULL);
      return TCL_ERROR;
    }

    sprintf(result_mass, "%f", Node->mass);
    Tcl_AppendResult(interp, result_mass, (char *) NULL);

    return TCL_OK;

  } else if((strcmp(argv[1], "CalcGrav") == 0) || 
	    (strcmp(argv[1], "calcgrav") == 0)) {
    tree_Node *Node;
    mpsa_List *List;
    mpsa_Link *Link;

    if(argc < 4) {
      Tcl_AppendResult(interp, argv[1], " needs a tree and a list", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(tree_GetTree(interp, argv[2], &Node) != TREE_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[3], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink){
      if(tree_CalcGrav(Link->Pcl, Node) != TREE_OKAY) {
	Tcl_AppendResult(interp, "Error calculating gravitational force", 
          (char *) NULL);
	return TCL_ERROR;
      }
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Setup") == 0) || 
	    (strcmp(argv[1], "setup") == 0)) {
    float theta, epsilon;
    if(argc != 4) {
      Tcl_AppendResult(interp, argv[1], " requires theta and epsilon",
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[2], &theta) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &epsilon) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    tree_SetGravParam(theta, epsilon);

    return TCL_OK;

  } else if((strcmp(argv[1], "DirectGrav") == 0) ||
	    (strcmp(argv[1], "directgrav") == 0)) {
    mpsa_List *List;
    mpsa_Link *Link;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(tree_DirectGravCalc(Link->Pcl, List) != TREE_OKAY) {
	Tcl_AppendResult(interp, "Error calculating gravity", (char *) NULL);
	return TCL_ERROR;
      }
    }
  } else if((strcmp(argv[1], "Switch") == 0) ||
	    (strcmp(argv[1], "switch") == 0)) {
    if(argc != 3) {
      Tcl_AppendResult(interp, argv[1], " requires an option to set",
        (char *) NULL);
      return TCL_ERROR;
    }

    if(tree_SetOption(argv[2]) != TREE_OKAY) {
      Tcl_AppendResult(interp, "Error setting criterion ", argv[2], 
        (char *) NULL);
      return TCL_ERROR;
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Print") == 0) || 
	    (strcmp(argv[1], "print") == 0)) {
    tree_Node *Node;

    if(argc != 3) {
      Tcl_AppendResult(interp, argv[1], " requires a node", (char *) NULL);
      return TCL_ERROR;
    }

    if(tree_GetTree(interp, argv[2], &Node) != TREE_OKAY) {
      return TCL_ERROR;
    }

    if(tree_PrintTree(interp, Node) != TREE_OKAY) {
      Tcl_AppendResult(interp, "Error printing tree", (char *) NULL);
      return TCL_ERROR;
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Parameters") == 0) ||
	    (strcmp(argv[1], "parameters") == 0)) {

    tree_WriteParameters(interp);
    return TCL_OK;

  } else if((strcmp(argv[1], "Merge") == 0) ||
	    (strcmp(argv[1], "merge") == 0)) {
    tree_Node *Node;
    float MergeRadius, MergeMass;

    if(argc != 5) {
      Tcl_AppendResult(interp, argv[1], " takes a tree, a length and a mass", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(tree_GetTree(interp, argv[2], &Node) != TREE_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &MergeRadius) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &MergeMass) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(tree_CalcCOM(Node) != TREE_OKAY) {
      Tcl_AppendResult(interp, " Something wrong with ", argv[2],
        (char *) NULL);
      return TCL_ERROR;
    }

    tree_MergeParticles(Node, MergeRadius, MergeMass);

    return TCL_OK;

  } else {
    Tcl_AppendResult(interp, "Option not recognised", (char *) NULL);
    return TCL_ERROR;
  }

  return TCL_OK;
}
