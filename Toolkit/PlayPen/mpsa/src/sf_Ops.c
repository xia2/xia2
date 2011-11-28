/* star formation operations file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 21st september 2000
 * 
 * 2nd november - if snf > 1 sfe = 1 to prevent negative things...
 * also kill cloud
 */

#include "sf_export.h"
#include "mpsa_export.h"
#include <stdlib.h>

static float SFE_MASS_INDEX = 0;
static float SFE_METAL_INDEX = 0;
static float SFE_CONSTANT = 0;

/*[ sf_SetParam
 *[ action:  set parameters for star formation efficiency
 *[ objects: takes three values
 */

static float BIMODAL_IMF_INDEX = 0;
static float BIMODAL_LOWER = 0;
static float BIMODAL_INTERMED = 0;
static float BIMODAL_UPPER = 0;
static float BIMODAL_FRACTION_UPPER = 0;
static float BIMODAL_FRACTION_LOWER = 0;

int sf_SetParam(
  float Constant,
  float MassIndex,
  float MetalIndex
)
{
  SFE_MASS_INDEX = MassIndex;
  SFE_METAL_INDEX = MetalIndex;
  SFE_CONSTANT = Constant;

  return SF_OKAY;
}

/*[ sf_StarForm
 *[ action:  perform the actual star formation
 *[ objects: takes a parent particle and a type to form, thus enabling 
 *[          different types of cloud to be used. will be tied to a more
 *[          sophisticated routine at a later stage to setup the new star
 */

int sf_StarForm(
  mpsa_Particle *Pcl,
  mpsa_ParticleDefn *Type,
  mpsa_Simulation *Sim
)
{
  float sfe, r;
  float x[3], v[3];
  int i;

  r = ((cloud_Pip *) Pcl->Pip)->radius;

  sfe = sf_SFE(Pcl);

  for(i = 0; i < 3; i++) {
    x[i] = Pcl->x[i] + (gwrand48() - 0.5) * r;
    v[i] = Pcl->v[i];
  }

  if(sfe > 1) {
    sfe = 1;
    Pcl->flag = 1;
  }

  mpsa_PclCreateExact(Sim, Type, sfe * Pcl->mass, x, v);

  /* use up mass of formed star */

  Pcl->mass *= (1 - sfe);

  /* heat cloud to up to 10^4 K depending on amount of sf */

  if(sfe > 0.1) {
    ((cloud_Pip *) Pcl->Pip)->T = 10000;
  } else {
    ((cloud_Pip *) Pcl->Pip)->T = 10000 * sfe / 0.1;
  }

  return SF_OKAY;
}

/*[ sf_SFE
 *[ action:  determine a star formation efficiency
 *[ objects: takes a particle and returns a float, assuming that pcl has
 *[          cloud pip set, which it will be
 */

float sf_SFE(
  mpsa_Particle *Pcl
)
{
  float sfe;

  sfe = SFE_CONSTANT;

  /* warning - this is not normalised! - that is down to the user      */
  /* add another set sfe command which will perform the normalisation? */
  /* there are issues here with the powers - Pcl->mass is very small!  */

  if(SFE_MASS_INDEX != 0) {
    sfe *= pow(Pcl->mass, SFE_MASS_INDEX);
  }
  if(SFE_METAL_INDEX != 0) {
    sfe *= pow(((cloud_Pip *)Pcl->Pip)->metal, SFE_METAL_INDEX);
  }

  return sfe;
}

/*[ sf_BimodalSetup
 *[ action:  set the parameters for bimodal star formation
 *[ objects: takes four values
 */ 

int sf_BimodalSetup(
  Tcl_Interp *interp,
  float index,
  float lower,
  float inter,
  float upper
)
{
  char up[20], low[20];
  BIMODAL_IMF_INDEX = index;
  BIMODAL_LOWER = lower;
  BIMODAL_INTERMED = inter;
  BIMODAL_UPPER = upper;

  BIMODAL_FRACTION_LOWER = (pow(BIMODAL_INTERMED, BIMODAL_IMF_INDEX) -
    pow(BIMODAL_LOWER, BIMODAL_IMF_INDEX)) / (pow(BIMODAL_UPPER, 
    BIMODAL_IMF_INDEX) - pow(BIMODAL_LOWER, BIMODAL_IMF_INDEX));

  BIMODAL_FRACTION_UPPER = (pow(BIMODAL_UPPER, BIMODAL_IMF_INDEX) -
    pow(BIMODAL_INTERMED, BIMODAL_IMF_INDEX)) / (pow(BIMODAL_UPPER, 
    BIMODAL_IMF_INDEX) - pow(BIMODAL_LOWER, BIMODAL_IMF_INDEX));

  sprintf(up, "%e ", BIMODAL_FRACTION_UPPER);
  sprintf(low, "%e ", BIMODAL_FRACTION_LOWER);

  Tcl_AppendResult(interp, up, low, (char *) NULL);

  return SF_OKAY;
}

/*[ sf_BimodalStarForm
 *[ action:  form two different populations of stars within an IMF
 *[ objects: takes parent cloud, type1, type2, simulation
 */

int sf_BimodalStarForm(
  mpsa_Particle *cloud,
  mpsa_ParticleDefn *Type1,
  mpsa_ParticleDefn *Type2,
  mpsa_Simulation *Sim
)
{

  /* note attention to detail - the origins of the new star particles */
  /* have the correct origins now! */

  float sfe, r, available;
  float x1[3], x2[3], v[3];
  int i;

  sfe = sf_SFE(cloud);

  if(sfe > 1) {
    sfe = 1;
    cloud->flag = 1;
  }

  r = ((cloud_Pip *) cloud->Pip)->radius;

  for(i = 0; i < 3; i++) {
    x1[i] = cloud->x[i] + (gwrand48() - 0.5) * r;
    x2[i] = cloud->x[i] + (gwrand48() - 0.5) * r;
    v[i] = cloud->v[i];
  }

  available = cloud->mass * sfe;

  cloud->mass -= available;

  if(available * BIMODAL_FRACTION_UPPER > BIMODAL_INTERMED) {
    /* can definately form some largish stars */
    mpsa_PclCreateExact(Sim, Type2, available * BIMODAL_FRACTION_UPPER, x2, v);
    available *= (1 - BIMODAL_FRACTION_UPPER);
    Sim->lastPcl->origin = cloud->origin;
  } else {
    /* might not have enough mass */
    if(gwrand48() > (available * BIMODAL_FRACTION_UPPER / BIMODAL_INTERMED)) {
      /* do form a star */
      mpsa_PclCreateExact(Sim, Type2, available * BIMODAL_FRACTION_UPPER, 
        x2, v);
      Sim->lastPcl->origin = cloud->origin;
    available *= (1 - BIMODAL_FRACTION_UPPER);
    } else {
      /* don't do anything! */
    }
  }

  /* use up what's left */

  mpsa_PclCreateExact(Sim, Type1, available, x1, v);
  Sim->lastPcl->origin = cloud->origin;

  /* heat up the star THIS MIGHT BE CHANGED! */

  if(sfe > 0.1) {
    ((cloud_Pip *) cloud->Pip)->T = 10000;
  } else {
    ((cloud_Pip *) cloud->Pip)->T += 10000 * sfe / 0.1;
  }

  return SF_OKAY;
}
