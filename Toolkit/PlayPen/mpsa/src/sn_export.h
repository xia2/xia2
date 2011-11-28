/* sn - supernova module for MPSA v1.0
 * maintained by g.winter
 * 9th october 2000
 * 
 * 
 */

#ifndef _SN
#define _SN

#include "tcl.h"
#include "mpsa_export.h"
#include "tree_export.h"
#include "cloud_export.h"

typedef struct sn_Pip{
  float radius;
  float speed;
} sn_Pip;

/*
  comment:
  action of supernova is at this moment just to push clouds out of the way - 
  this will implement a `heating' effect. can also at a later stage implement 
  proper temperature monitoring, so that the cloud temperatures can be modelled
  accurately. this is being done now too...

  sn will be created from a list of candidate `stars'. note that at the moment
  this refers to minimal data stars, not the multi modal versions
*/

#define SN_OKAY 0
#define SN_FAIL 1

#define SN_RAD 100
#define SN_SPEED 101


/*[ sn_SetParam
 *[ action:  set parameters which are used to determine lifetime of large star
 *[ objects: takes two floating point values
 */

extern int sn_SetParam(
  float NewLife,
  float NewMass
);

/*[ sn_StarLife
 *[ action:  determine the lifetime of a large star from it's mass
 *[ objects: takes a floating point mass and returns a lifetime
 */

extern float sn_StarLife(
  float Mass
);

/*[ sn_SNForm
 *[ action:  form a SN particle from a Star particle and delete the star
 *[ objects: takes a particle, a particle definition and a simulation
 */

extern int sn_SNForm(
  mpsa_Particle *Particle,
  mpsa_ParticleDefn *Type,
  mpsa_Simulation *Sim
);

/*[ sn_UpdateRadius
 *[ action:  update the radius of a supernova
 *[ objects: takes a supernova particle, pip and a timestep
 */

extern int sn_UpdateRadius(
  mpsa_Particle *Pcl,
  sn_Pip *Pip,
  float dt
);

/*[ sn_Constructor
 *[ action:  create a new SN pip
 *[ objects: takes a pointer to a void * pointer
 */

extern int sn_Constructor(
  void **NewPip
);

/*[ sn_Destructor
 *[ action:  destroy a supernova pip
 *[ objects: takes a pointer to a void * pointer
 */

extern int sn_Destructor(
  void **NewPip
);

/*[ sn_SetDataEntry
 *[ action:  set a data entry to be retrieved
 *[ objects: takes the name of a data entry
 */

extern int sn_SetDataEntry(
  char *Name
);

/*[ sn_GetFloat/IntDataEntry
 *[ action:  get a float or integer data entry
 *[ objects: takes a pointer to a pip
 */

extern int sn_GetIntDataEntry(
  void *Pip
);
     
extern float sn_GetFloatDataEntry(
  void *Pip
);

/*[ sn_Reader/Writer
 *[ action:  read/write sn data from a Tcl Channel
 *[ objects: takes a pointer to a pip and a tcl chanel
 */

extern int sn_Reader(
  Tcl_Channel chan,
  void *Pip
);

extern int sn_Writer(
  Tcl_Channel chan,
  void *Pip
);

/*[ sn_SNovaCmd.c
 *[ action:  catch all function implementing supernova physics
 *[ objects: can take almost anything
 */

extern int sn_SNovaCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ sn_CloudInteractionFind
 *[ action:  find clouds to be shocked in a tree of clouds
 *[ objects: takes two radii, a sn particle and a tree of clouds
 *[          which have their cloud pips selected
 */

extern int sn_CloudInteractionFind(
  float rmin,
  float rmax,
  mpsa_Particle *SNPcl,
  tree_Node *Root
);

/*[ sn_ShockCloud
 *[ action:  shock/cloud interaction physics
 *[ objects: takes a sn particle and a cloud particle
 */

extern int sn_ShockCloud(
  mpsa_Particle *SNPcl,
  mpsa_Particle *Cloud
);

extern int sn_HeatSet(
  int heatval
);

#endif
