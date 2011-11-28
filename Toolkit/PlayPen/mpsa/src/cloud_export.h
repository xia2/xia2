/* cloud module header file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 11th september 2000
 * 
 * 
 */

#ifndef _CLOUD
#define _CLOUD

#define CLOUD_OKAY 0
#define CLOUD_FAIL 1

#define CLOUD_T 0
#define CLOUD_P 1
#define CLOUD_METAL 2
#define CLOUD_RADIUS 3
#define CLOUD_RHO 4
#define CLOUD_SHOCK 5

#include "tcl.h"
#include "mpsa_export.h"
#include "tree_export.h"

typedef struct cloud_Pip{
  float T;           /* temperature */
  float P;           /* pressure    */
  float radius;      /* collision radius */
  float metal;       /* metallicity */
  float rho;         /* density */
  int   shocked;     /* has the cloud been shocked? */
} cloud_Pip;

/*[ cloud_ChangeRadiusFactor
 *[ action:  to do exactly that
 *[ objects: takes the new value
 */

extern int cloud_ChangeRadiusFactor(
  float NewValue
);

/*[ cloud_Constructor
 *[ action:  create a cloud pip
 *[ objects: takes a pointer to a pointer to a pip!
 */

extern int cloud_Constructor(
  void **NewPip
);

/*[ cloud_Destructor
 *[ action:  delete a cloud pip
 *[ objects: takes a void **pointer
 */

extern int cloud_Destructor(
  void **Pip
);

/*[ cloud_SetDataEntry
 *[ action:  sets a data entry for list extraction
 *[ objects: takes a name of a data entry
 */

extern int cloud_SetDataEntry(
  char *Name
);

/*[ cloud_GetIntDataEntry
 *[ action:  get an integer valued data entry from a cloud pip (redundant)
 *[ objects: takes a pointer to a pip of hopefully the right type!
 */

extern int cloud_GetIntDataEntry(
  void *Pip
);

/*[ cloud_GetFloatDataEntry
 *[ action:  get an float valued data entry from a cloud pip
 *[ objects: takes a pointer to a pip of hopefully the right type!
 */

extern float cloud_GetFloatDataEntry(
  void *Pip
);

/*[ cloud_Reader
 *[ action:  read data into a cloud from a tcl channel
 *[ objects: takes a pointer to a pip and a tcl channel
 */

extern int cloud_Reader(
  Tcl_Channel chan,
  void *Pip
);

/*[ cloud_Writer
 *[ action:  write data from a cloud pip to a tcl channel
 *[ objects: takes a pointer to a pip and a tcl channel
 */

extern int cloud_Writer(
  Tcl_Channel chan,
  void *Pip
);

/*[ cloud_SetRadius
 *[ action:  set radius of a cloud assuming constant density
 *[ objects: takes a pointer to a cloud
 */

extern int cloud_SetRadius(
  mpsa_Particle *Pcl
);

/*[ cloud_CloudCmd
 *[ action:  anything to do with clouds, will control physics etc.
 *[ objects: cloud particles, lists and trees for a variety
 *[          of different tasks
 */

extern int cloud_CloudCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ cloud_TreeCollisionSearch
 *[ action:  searches tree for clouds to merge and merges them
 *[ objects: takes a cloud particle and a tree, and a search radius
 */

extern int cloud_TreeCollisionSearch(
  float Radius,
  mpsa_Particle *Pcl,
  tree_Node *Node
);

/*[ cloud_TreeCollisionSearch2
 *[ action:  searches tree for clouds to merge and merges them
 *[ objects: takes a cloud particle and a tree, and a search radius
 */

extern int cloud_TreeCollisionSearch2(
  float Radius,
  float dt,
  mpsa_Particle *Pcl,
  tree_Node *Node
);

/*[ cloud_CollideClouds
 *[ action:  perform the task of colliding two clouds
 *[ objects: takes two cloud particles
 *[ notes:   here is the place to put the cloud cloud collision physics
 */

extern int cloud_CollideClouds(
  mpsa_Particle *PclA,
  mpsa_Particle *PclB
);

/*[ cloud_SetFragParam
 *[ action:  sets the fragmentation parameters
 *[ objects: takes three integers, minimum and maximum mass and power
 *[          spectrum index
 */

extern int cloud_SetFragParam(
  float MMin,
  float MMax,
  float index
);

/*[ cloud_GetRandomMass
 *[ action:  get a random mass from the distribution detailed above
 *[ objects: returns a float, takes nothing
 */

extern float cloud_GetRandomMass();

/*[ cloud_FragmentCloud
 *[ action:  fragment cloud into many smaller clouds
 *[ objects: takes a cloud particle and a pointer to a simulation
 */

extern int cloud_FragmentCloud(
  mpsa_Particle *CloudPcl,
  mpsa_Simulation *Sim,
  mpsa_Pip *CloudPip
);

/*[ cloud_CoolCloud
 *[ action:  cool a cloud particle
 *[ objects: takes a pointer to a particle with a cloud pip
 */

extern int cloud_CoolCloud(
  mpsa_Particle *Cloud,
  float dt
);


extern int cloud_SetHeat(
  int NewVal
);

extern int cloud_SetIndices(
  float newMindex,
  float newTindex
);

/*[ cloud_MassSpectrum
 *[ action:  calculate mass spectrum information from a list of particles
 *[ objects: takes a tcl interpreter, a list and a flag
 */

extern int cloud_MassSpectrum(
  Tcl_Interp *interp,
  mpsa_List *List,
  int print
);

#endif
