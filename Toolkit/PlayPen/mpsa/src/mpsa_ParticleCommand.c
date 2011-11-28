/* gsimII mpsa particle command v1.1
 * maintained by g.winter
 * 29th august 2000
 *
 * modification 12th september to add functionality - read in positions from 
 * ascii text file - gw
 */

#include "mpsa_private.h"
#include <math.h>
#include <stdlib.h>

/*[ mpsa_ParticleCmd
 *[ action:  anything to do with particles
 *[ objects: lists, simulations and types
 *[ syntax:  too big to explain here
 */

int mpsa_ParticleCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  int i;

  if(argc < 2) {
    Tcl_AppendResult(interp, "Error - need an option for this command", 
      (char *) NULL);
    return TCL_ERROR;
  }

  if((strcmp(argv[1], "Create") == 0) || 
     (strcmp(argv[1], "create") == 0)) {

    /* create particles of a well defined type in a simulation - random */

    mpsa_Simulation *Simulation;
    mpsa_ParticleDefn *type;
    int PclCount;
    
    if(argc < 5) {
      Tcl_AppendResult(interp, "Error in usage of Create option\n",
        "should take ", argv[0], " Create SimName TypeName Number\n", 
        (char *) NULL);
      return TCL_ERROR;
    }
    if(mpsa_GetSim(interp, argv[2], &Simulation) != MPSA_OKAY) {
      return TCL_ERROR;
    } 
    
    if(mpsa_GetPclDefn(interp, argv[3], &type) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error getting type ", argv[3], (char *) NULL);
      return TCL_ERROR;
    }
    
    if(Tcl_GetInt(interp, argv[4], &PclCount) != TCL_OK) {
      Tcl_AppendResult(interp, "Error getting number to make", (char *) NULL);
      return TCL_ERROR;
    }
    
    Tcl_AppendResult(interp, argv[4], (char *) NULL);
    
    for(i = 0; i < PclCount; i++) {
      if(mpsa_PclCreate(Simulation, type) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error creating particle", (char *) NULL);
	return TCL_ERROR;
      }
    }
    return TCL_OK;

  } else if((strcmp(argv[1], "CreateFromFile") == 0) ||
	    (strcmp(argv[1], "createfromfile") == 0)) {

    /* create particles of a well defined type in a simulation - from file */

    FILE *FileStream;
    float m;
    float x[3];
    float v[3];
    mpsa_Simulation *Simulation;
    mpsa_ParticleDefn *type;
    int PclCount;

    if(argc < 6) {
      Tcl_AppendResult(interp, "Error in usage of command option ", argv[1],
        "\nshould take SimName TypeName Number File", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetSim(interp, argv[2], &Simulation) != MPSA_OKAY) {
      return TCL_ERROR;
    } 
    
    if(mpsa_GetPclDefn(interp, argv[3], &type) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error getting type ", argv[3], (char *) NULL);
      return TCL_ERROR;
    }
    
    if(Tcl_GetInt(interp, argv[4], &PclCount) != TCL_OK) {
      Tcl_AppendResult(interp, "Error getting number to make", (char *) NULL);
      return TCL_ERROR;
    }
    
    FileStream = fopen(argv[5], "r");

    if(FileStream == NULL) {
      Tcl_AppendResult(interp, "Error opening file", (char *) NULL);
      return TCL_ERROR;
    }

    Tcl_AppendResult(interp, argv[4], (char *) NULL);

    for(i = 0; i < PclCount; i++) {
      fscanf(FileStream, "%e %e %e %e %e %e %e\n", &m, &x[0], &x[1], &x[2],
        &v[0], &v[1], &v[2]);
      if(mpsa_PclCreateExact(Simulation, type, m, x, v) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error creating particle", (char *) NULL);
	return TCL_ERROR;
      }
    }
    fclose(FileStream);

    return TCL_OK;

  } else if((strcmp(argv[1], "CFF") == 0) ||
	    (strcmp(argv[1], "cff") == 0)) {
    
    /* create particles of a well defined type in a simulation - from file */

    FILE *FileStream;
    float m;
    float x[3];
    float v[3];
    float a[3];
    mpsa_Simulation *Simulation;
    mpsa_ParticleDefn *type;
    int PclCount;

    if(argc < 6) {
      Tcl_AppendResult(interp, "Error in usage of command option ", argv[1],
        "\nshould take SimName TypeName Number File", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetSim(interp, argv[2], &Simulation) != MPSA_OKAY) {
      return TCL_ERROR;
    } 
    
    if(mpsa_GetPclDefn(interp, argv[3], &type) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error getting type ", argv[3], (char *) NULL);
      return TCL_ERROR;
    }
    
    if(Tcl_GetInt(interp, argv[4], &PclCount) != TCL_OK) {
      Tcl_AppendResult(interp, "Error getting number to make", (char *) NULL);
      return TCL_ERROR;
    }
    
    FileStream = fopen(argv[5], "r");

    if(FileStream == NULL) {
      Tcl_AppendResult(interp, "Error opening file", (char *) NULL);
      return TCL_ERROR;
    }

    Tcl_AppendResult(interp, argv[4], (char *) NULL);

    for(i = 0; i < PclCount; i++) {
      fscanf(FileStream, "%e %e %e %e %e %e %e %e %e %e\n", &m, &x[0], 
        &x[1], &x[2], &v[0], &v[1], &v[2], &a[0], &a[1], &a[2]);
      if(mpsa_PclCreateExactAcc(Simulation, type, m, x, v, a) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error creating particle", (char *) NULL);
	return TCL_ERROR;
      }
    }
    fclose(FileStream);

    return TCL_OK;

  } else if((strcmp(argv[1], "CreateFromGS") == 0) ||
	    (strcmp(argv[1], "createfromgs") == 0)) {

    /* create particles of a well defined type in a simulation - gsim file */

    FILE *FileStream;
    float m;
    float x[3];
    float v[3];
    mpsa_Simulation *Simulation;
    mpsa_ParticleDefn *type;
    int PclCount;

    if(argc < 6) {
      Tcl_AppendResult(interp, "Error in usage of command option ", argv[1],
        "\nshould take SimName TypeName Number File", (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetSim(interp, argv[2], &Simulation) != MPSA_OKAY) {
      return TCL_ERROR;
    } 
    
    if(mpsa_GetPclDefn(interp, argv[3], &type) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error getting type ", argv[3], (char *) NULL);
      return TCL_ERROR;
    }
    
    if(Tcl_GetInt(interp, argv[4], &PclCount) != TCL_OK) {
      Tcl_AppendResult(interp, "Error getting number to make", (char *) NULL);
      return TCL_ERROR;
    }
    
    FileStream = fopen(argv[5], "r");

    if(FileStream == NULL) {
      Tcl_AppendResult(interp, "Error opening file", (char *) NULL);
      return TCL_ERROR;
    }

    Tcl_AppendResult(interp, argv[4], (char *) NULL);

    for(i = 0; i < PclCount; i++) {
      fscanf(FileStream, "%e %e %e %e %e %e %e\n", &x[0], &x[1], &x[2],
        &v[0], &v[1], &v[2], &m);
      if(mpsa_PclCreateExact(Simulation, type, m, x, v) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error creating particle", (char *) NULL);
	return TCL_ERROR;
      }
    }
    fclose(FileStream);

    return TCL_OK;

  } else if ((strcmp(argv[1], "Delete") == 0) || 
	     (strcmp(argv[1], "delete")== 0)) {

    /* delete all particles in list */

    mpsa_List *List;
    mpsa_Simulation *Simulation;
    mpsa_Particle *First, *Last;
    mpsa_Link *Link;
    int NumberToDelete;
    char Number[9];
    
    if(argc < 3) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n",
        "wanted something like ", argv[0], " delete ListName", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    Simulation = List->Simulation;
    NumberToDelete = List->NElements;
    First = Simulation->firstPcl;
    Last = Simulation->lastPcl;
    
    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(Link->Pcl == First) {
	Simulation->firstPcl = First->nextPcl;
	First = Simulation->firstPcl;
      }
      if(Link->Pcl == Last) {
	Simulation->lastPcl = Last->prevPcl;
	Last = Simulation->lastPcl;
      }
      if(mpsa_DeletePcl(Link->Pcl) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error deleting particles", (char *) NULL);
	return TCL_ERROR;
      }
    }
    
    sprintf(Number, "%d", NumberToDelete);
    
    Tcl_AppendResult(interp, Number, (char *) NULL);
    
    List->Simulation->NPcls -= NumberToDelete;
    
    if(mpsa_ListClear(List) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error clearing list", (char *) NULL);
      return TCL_ERROR;
    }
    
    return TCL_OK;

  } else if ((strcmp(argv[1], "Register") == 0) ||
	     (strcmp(argv[1], "register") == 0 )) {

    /* register a new particle type with a list of pips */
    
    Tcl_HashEntry *Entry;
    mpsa_ParticleDefn *NewDefn;
    int PipCount;
    mpsa_Pip **PipList, *Pip;
    int new, i, NameLength;
    
    if(argc < 4) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n",
        "was expecting something like ", argv[0], "register type npips pip1..",
	(char *) NULL);
      return TCL_ERROR;
    }
    
    NewDefn = (mpsa_ParticleDefn *) malloc (sizeof(mpsa_ParticleDefn));
    NewDefn->DynamicID = mpsa_GetMaxPclID();
    NameLength = strlen(argv[2]);
    NewDefn->Name = (char *) malloc ((NameLength + 1) * (sizeof(char)));
    NewDefn->Name = strcpy(NewDefn->Name, argv[2]);
    
    if(Tcl_GetInt(interp, argv[3], &PipCount) != TCL_OK) {
      Tcl_AppendResult(interp, "Error obtaining number of pips", 
        (char *) NULL);
      free(NewDefn->Name);
      free(NewDefn);
      return TCL_ERROR;
    }

    Entry = Tcl_CreateHashEntry(&mpsa_ParticletypeHashTable, argv[2], &new);
    if(new) {
      Tcl_SetHashValue(Entry, NewDefn);
    } else {
      Tcl_AppendResult(interp, "Error registering particle type", 
        (char *) NULL);
      free(NewDefn->Name);
      free(NewDefn);
      return TCL_ERROR;
    }

    NewDefn->NPips = PipCount;

    if(PipCount != (argc - 4)) {
      Tcl_AppendResult(interp, "Error obtaining pip names", (char *) NULL);
      free(NewDefn->Name);
      free(NewDefn);
      return TCL_ERROR;
    }

    if(PipCount == 0) {
      PipList = NULL;
    } else {
      PipList = (mpsa_Pip **) malloc (sizeof(mpsa_Pip *) * PipCount);
    }
    
    for(i = 0; i < PipCount; i++) {
      if(mpsa_GetPipDefn(interp, argv[4 + i], &Pip) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error obtaining pip definition", 
          (char *) NULL);
	free(NewDefn->Name);
	free(PipList);
	free(NewDefn);
	return TCL_ERROR;
      }
      PipList[i] = Pip;
    }
    
    NewDefn->Piptypes = PipList;
    
    mpsa_IncrementMaxPclID();
    
    return TCL_OK;
    
  } else if ((strcmp(argv[1], "PositionUpdate") == 0) ||
	     (strcmp(argv[1], "positionUpdate") == 0)) {

    /* update position */

    mpsa_List *List;
    mpsa_Link *Link;
    double TempDouble;
    float dt;
    
    if(argc != 4) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n",
      "expecting ", argv[0], "move ListName TimeStep", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    if(Tcl_GetDouble(interp, argv[3], &TempDouble) != TCL_OK) {
      Tcl_AppendResult(interp, "Error getting timestep", (char *) NULL);
      return TCL_ERROR;
    }
    
    dt = TempDouble;
    
    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      mpsa_PclPosUpdate(Link->Pcl, dt);
    }
    
    return TCL_OK;
    
  } else if ((strcmp(argv[1], "VelocityUpdate") == 0) ||
	     (strcmp(argv[1], "velocityUpdate") == 0)) {

    /* update velocity */

    mpsa_List *List;
    mpsa_Link *Link;
    double TempDouble;
    float dt;
    
    if(argc != 4) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n",
      "expecting ", argv[0], "move ListName TimeStep", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    if(Tcl_GetDouble(interp, argv[3], &TempDouble) != TCL_OK) {
      Tcl_AppendResult(interp, "Error getting timestep", (char *) NULL);
      return TCL_ERROR;
    }
    
    dt = TempDouble;
    
    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      mpsa_PclVelUpdate(Link->Pcl, dt);
    }
    
    return TCL_OK;
    
  } else if ((strcmp(argv[1], "Write") == 0) ||
	     (strcmp(argv[1], "write") == 0)) {

    /* write binary output of particle data */

    mpsa_List *List;
    mpsa_Link *Link;
    Tcl_Channel chan;
    int mode;
    
    if(argc != 4) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n", 
	"expected something like ", argv[0], " write ListName channelID",
        (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    if((chan = Tcl_GetChannel(interp, argv[3], &mode)) == (Tcl_Channel) NULL) {
      Tcl_AppendResult(interp, "Error getting channel", (char *) NULL);
      return TCL_ERROR;
    }
    
    if((mode & TCL_WRITABLE) == 0) {
      Tcl_AppendResult(interp, "Channel is not writeable", (char *) NULL);
      return TCL_ERROR;
    }
    
    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      if(mpsa_WritePcl(Link->Pcl, chan) != MPSA_OKAY) {
	Tcl_AppendResult(interp, "Error writing particle", (char *) NULL);
	return TCL_ERROR;
      }
    }
    
    return TCL_OK; 
    
  } else if((strcmp(argv[1], "Read") == 0) ||
	    (strcmp(argv[1], "read") == 0)) {

    /* read particle input of particle data */

    mpsa_Simulation *Simulation;
    Tcl_Channel chan;
    int mode;
    
    if(argc != 3) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n",
        "expecting something along the lines of \n",
        argv[0], " read SimName channelID", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_GetSim(interp, argv[2], &Simulation) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    if((chan = Tcl_GetChannel(interp, argv[3], &mode)) == (Tcl_Channel) NULL) {
      Tcl_AppendResult(interp, "Error getting channel", (char *) NULL);
      return TCL_ERROR;
    }
    
    if((mode & TCL_WRITABLE) == 0) {
      Tcl_AppendResult(interp, "Channel is not writeable", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_WriteSimulation(Simulation, chan) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error writing simulation", (char *) NULL);
      return TCL_ERROR;
    }
    
    return TCL_OK;
    
  } else if(strcmp(argv[1], "dx") == 0) {

    /* update position */

    mpsa_List *List;
    mpsa_Link *Link;
    float dt;

    if(argc != 4) {
      Tcl_AppendResult(interp, argv[1], " requires a list and a timestep",
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &dt) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      mpsa_PclPosUpdate(Link->Pcl, dt);
    }

    return TCL_OK;

  } else if(strcmp(argv[1], "dv") == 0) {

    /* update velocity */

    mpsa_List *List;
    mpsa_Link *Link;
    float dt;

    if(argc != 4) {
      Tcl_AppendResult(interp, argv[1], " requires a list and a timestep",
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &dt) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      mpsa_PclVelUpdate(Link->Pcl, dt);
    }

    return TCL_OK;

  } else if ((strcmp(argv[1], "Zero") == 0) || 
	     (strcmp(argv[1], "zero")== 0)) {

    /* set to zero one of the administration flags */

    mpsa_List *List;
    mpsa_Link *Link;
    
    if(argc < 4) {
      Tcl_AppendResult(interp, "Error - insufficient arguments\n",
        "wanted ", argv[1], " flag/extract ListName", (char *) NULL);
      return TCL_ERROR;
    }
    
    if(mpsa_GetList(interp, argv[3], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    if((strcmp(argv[2], "Flag") == 0) || 
       (strcmp(argv[2], "flag") == 0)) {
      for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
	Link->Pcl->flag = 0;
      }
    } else if ((strcmp(argv[2], "Extract") == 0) || 
	       (strcmp(argv[2], "extract") == 0)) {
      for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
	Link->Pcl->extract = 0;
      }
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "SetCircular") == 0) || 
	    (strcmp(argv[1], "setcircular") == 0)){

    /* routine to set a list of particles into circular orbits, assuming
       that the gravitational force has already been calculated on them.
       sigma is the velocity dispersion. this should really be encapsulated.
    */
    long seed = 1010;
    float r, sigma, v, a, theta;
    float vx, vy, vz, rsq, asq;
    mpsa_List *List;
    mpsa_Link *Link;
    int i, direction;
    if(argc < 5) {
      Tcl_AppendResult(interp, argv[1], " takes a list, direction and ",
        "velocity dispersion", (char *) NULL);
      return TCL_ERROR;
    }

    if((strcmp(argv[2], "CW") == 0) || 
       (strcmp(argv[2], "cw") == 0)) {
      direction = -1;
    } else if((strcmp(argv[2], "ACW") == 0) || 
	      (strcmp(argv[2], "acw") == 0)) {
      direction = 1;
    } else {
      Tcl_AppendResult(interp, argv[2], " should have been cw/acw",
	(char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[3], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &sigma) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    seed += List->NElements * List->firstLink->Pcl->index;

    srand48(seed);

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
      rsq = 0;
      asq = 0;
      for(i = 0; i < 2; i++) {
	rsq += Link->Pcl->x[i] * Link->Pcl->x[i];
	asq += Link->Pcl->a[i] * Link->Pcl->a[i];
      }

      r = sqrt(rsq);
      a = sqrt(asq);

      v = sqrt(r * a);

      theta = atan(Link->Pcl->x[1] / Link->Pcl->x[0]);

      if(Link->Pcl->x[0] < 0) {
	theta += 3.1415927;
      }

      vx = cos(theta + 1.570796 * direction) * v + sigma * (gwrand48() - 0.5);
      vy = sin(theta + 1.570796 * direction) * v + sigma * (gwrand48() - 0.5);
      vz = sigma * (gwrand48() - 0.5);

      Link->Pcl->v[0] = vx;
      Link->Pcl->v[1] = vy;
      Link->Pcl->v[2] = vz;
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Translate") == 0) ||
	    (strcmp(argv[1], "translate") == 0)) {

    /* move in position or velocity space entire list by same amount */

    float dx, dy, dz;
    mpsa_List *List;
    mpsa_Link *Link;

    if(argc != 7) {
      Tcl_AppendResult(interp, argv[1], " requires list r/v dx dy dz", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &dx) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    if(mpsa_GetFloat(interp, argv[5], &dy) != MPSA_OKAY) {
      return TCL_ERROR;
    }
      
    if(mpsa_GetFloat(interp, argv[6], &dz) != MPSA_OKAY) {
      return TCL_ERROR;
    }
    
    if((strcmp(argv[3], "R") == 0) ||
       (strcmp(argv[3], "r") == 0)) {

      for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
	Link->Pcl->x[0] += dx;
	Link->Pcl->x[1] += dy;
	Link->Pcl->x[2] += dz;
      }

    } else if((strcmp(argv[3], "V") == 0) ||
	      (strcmp(argv[3], "v") == 0)) {
      for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
	Link->Pcl->v[0] += dx;
	Link->Pcl->v[1] += dy;
	Link->Pcl->v[2] += dz;
      }
    }
    
    return TCL_OK;

  } else if((strcmp(argv[1], "Rotate") == 0) ||
	    (strcmp(argv[1], "rotate") == 0)) {

    /* rotate the entire list about the origin by given amounts */
    /* determined by the three axis of rotation */

    float thetaX, thetaY, thetaZ;
    float tempX, tempY, tempZ;
    mpsa_List *List;
    mpsa_Link *Link;

    if(argc != 6) {
      Tcl_AppendResult(interp, argv[1], " requires a list and three angles",
	(char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[3], &thetaX) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[4], &thetaY) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_GetFloat(interp, argv[5], &thetaZ) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {

      /* rotate x */
      tempY = Link->Pcl->x[1];
      tempZ = Link->Pcl->x[2];
      Link->Pcl->x[1] = tempY * cos(thetaX) + tempZ * sin(thetaX);
      Link->Pcl->x[2] = - tempY * sin(thetaX) + tempZ * cos(thetaX);
      tempY = Link->Pcl->v[1];
      tempZ = Link->Pcl->v[2];
      Link->Pcl->v[1] = tempY * cos(thetaX) + tempZ * sin(thetaX);
      Link->Pcl->v[2] = - tempY * sin(thetaX) + tempZ * cos(thetaX);

      /* rotate y */
      tempX = Link->Pcl->x[0];
      tempZ = Link->Pcl->x[2];
      Link->Pcl->x[0] = tempX * cos(thetaY) + tempZ * sin(thetaY);
      Link->Pcl->x[2] = - tempX * sin(thetaY) + tempZ * cos(thetaY);
      tempX = Link->Pcl->v[0];
      tempZ = Link->Pcl->v[2];
      Link->Pcl->v[0] = tempX * cos(thetaY) + tempZ * sin(thetaY);
      Link->Pcl->v[2] = - tempX * sin(thetaY) + tempZ * cos(thetaY);

      /* rotate z */
      tempX = Link->Pcl->x[0];
      tempY = Link->Pcl->x[1];
      Link->Pcl->x[0] = tempX * cos(thetaZ) + tempY * sin(thetaZ);
      Link->Pcl->x[1] = - tempX * sin(thetaZ) + tempY * cos(thetaZ);
      tempX = Link->Pcl->v[0];
      tempY = Link->Pcl->v[1];
      Link->Pcl->v[0] = tempX * cos(thetaZ) + tempY * sin(thetaZ);
      Link->Pcl->v[1] = - tempX * sin(thetaZ) + tempY * cos(thetaZ);
    }

    return TCL_OK;

  } else if((strcmp(argv[1], "Set") == 0) ||
	    (strcmp(argv[1], "set") == 0)) {

    /* set an administration flag to a new value */

    mpsa_List *List;
    mpsa_Link *Link;
    int NewValue;

    if(argc != 5) {
      Tcl_AppendResult(interp, argv[1], " requires a list, option and value", 
        (char *) NULL);
      return TCL_ERROR;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if((strcmp(argv[3], "Origin") == 0) ||
       (strcmp(argv[3], "origin") == 0)) {
      if(mpsa_GetInt(interp, argv[4], &NewValue) != MPSA_OKAY) {
	return TCL_ERROR;
      }
      for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
	Link->Pcl->origin = NewValue;
      }
    } else {
      Tcl_AppendResult(interp, argv[3], " unrecognised", (char *) NULL);
      return TCL_ERROR;
    }
    return TCL_OK;

  } else if((strcmp(argv[1], "MSpec") == 0) ||
	    (strcmp(argv[1], "mspec") == 0)) {

    /* estimate the mass spectrum of the list of particles */

    int print;
    mpsa_List *List;

    if(argc < 3) {
      Tcl_AppendResult(interp, argv[1], " requires a list", (char *) NULL);
      return TCL_ERROR;
    }

    if(argc == 4) {
      if((strcmp(argv[3], "Print") == 0) ||
	 (strcmp(argv[3], "print") == 0)) {
	/* do nothing, this option is fine */
	print = 1;
      } else {
	print = 0;
	Tcl_AppendResult(interp, argv[3], " should be print", (char *) NULL);
	return TCL_ERROR;
      }
    } else {
      print = 0;
    }

    if(mpsa_GetList(interp, argv[2], &List) != MPSA_OKAY) {
      return TCL_ERROR;
    }

    if(mpsa_MassSpectrum(interp, List, print) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error in mass spectrum calculation", 
        (char *) NULL);
      return TCL_ERROR;
    }
    
    return TCL_OK;

  } else {
    Tcl_AppendResult(interp, "Option ", argv [1], " unrecognised", 
      (char *) NULL);
    return TCL_ERROR;
  }
}
