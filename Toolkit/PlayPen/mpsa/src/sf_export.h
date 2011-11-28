/* star formation v1.0
 * module for mpsa
 * maintained by g.winter
 * 21st september 2000
 * 
 */

#ifndef _SF
#define _SF

#include "mpsa_export.h"
#include "cloud_export.h"
#include "tcl.h"

#define SF_OKAY 0
#define SF_FAIL 1

/* notes:
   description of module.
   implementation of star formation for mpsa using most basic principles, to
   enable stars of any type or description to be created. uses `rules' which
   can be added to with time, and these work in a similar way to the extraction
   rules, with a few functions which determine the amount of star formation and
   whether it should take place at all. more sophisticated inheritance, for
   example propogating metallicities into the newly born stars.

   watch this space.
*/

/*[ sf_SFCmd
 *[ action:  perform all star formation actions at the simplest level
 *[ objects: will take list of clouds and a rule
 */

extern int sf_SFCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ sf_StarForm
 *[ action:  perform the actual star formation
 *[ objects: takes a parent particle and a type to form, thus enabling 
 *[          different types of cloud to be used. will be tied to a more
 *[          sophisticated routine at a later stage to setup the new star
 */

extern int sf_StarForm(
  mpsa_Particle *Pcl,
  mpsa_ParticleDefn *Type,
  mpsa_Simulation *Sim
);

/*[ sf_SFE
 *[ action:  determine a star formation efficiency
 *[ objects: takes a particle and returns a float, assuming that pcl has
 *[          cloud pip set, which it will be
 */

extern float sf_SFE(
  mpsa_Particle *Pcl
);

/*[ sf_SetParam
 *[ action:  set parameters for star formation efficiency
 *[ objects: takes three values
 */

extern int sf_SetParam(
  float Constant,
  float MassIndex,
  float MetalIndex
);

/*[ sf_BimodalSetup
 *[ action:  set the parameters for bimodal star formation
 *[ objects: takes four values
 */ 

extern int sf_BimodalSetup(
  Tcl_Interp *interp,
  float index,
  float lower,
  float inter,
  float upper
);

/*[ sf_BimodalStarForm
 *[ action:  form two different populations of stars within an IMF
 *[ objects: takes parent cloud, type1, type2, simulation
 */

int sf_BimodalStarForm(
  mpsa_Particle *cloud,
  mpsa_ParticleDefn *Type1,
  mpsa_ParticleDefn *Type2,
  mpsa_Simulation *Sim
);

#endif

