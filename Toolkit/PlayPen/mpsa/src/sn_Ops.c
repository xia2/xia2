/* sn - supernova operations file v1.0
 * for loading into MPSA
 * maintained by g.winter
 * 9th october 2000
 * 
 * a profusion of modifications to 1st december 2000
 * so that the intended physics is actually here
 * 
 * 4th dec. further modifications to ensure that the collisions are found
 * correctly
 * 
 * 13th dec. further modifications: this time to ensure that the strength 
 * of the supernova is interpolated
 *
 */

#include "mpsa_private.h"
#include "tree_export.h"
#include "tree_private.h"
#include "sn_export.h"

static int heat_off = 0;

static float SNLife0 = 0;
static float SNMass0 = 0;

static int SnExtraction = SN_RAD;

/*[ sn_SetParam
 *[ action:  set parameters which are used to determine lifetime of large star
 *[ objects: takes two floating point values
 */

int sn_SetParam(
  float NewLife,
  float NewMass
)
{
  SNLife0 = NewLife;
  SNMass0 = NewMass;

  return SN_OKAY;
}

/*[ sn_StarLife
 *[ action:  determine the lifetime of a large star from it's mass
 *[ objects: takes a floating point mass and returns a lifetime
 */

float sn_StarLife(
  float Mass
)
{
  float Life;

  if(Mass > 0) {
    Life = SNLife0 * SNMass0 / Mass;
  } else {
    Life = 10e10;
  }
  return Life;
}

/*[ sn_SNForm
 *[ action:  form a SN particle from a Star particle and delete the star
 *[ objects: takes a particle, a particle definition and a simulation
 */

int sn_SNForm(
  mpsa_Particle *Particle,
  mpsa_ParticleDefn *Type,
  mpsa_Simulation *Sim
)
{


  /* modified 30th november 2000

  if(Particle->age > sn_StarLife(Particle->mass)) {
    mpsa_PclCreateExact(Sim, Type, Particle->mass, Particle->x, Particle->v);
    mpsa_DeletePcl(Particle);
  }

  */

  if(Particle->age > 1.0) {
    mpsa_PclCreateExact(Sim, Type, Particle->mass, Particle->x, Particle->v);

    /* must check on the status of Particle */
    
    if(Particle == Sim->lastPcl) {
      Sim->lastPcl = Sim->lastPcl->prevPcl;
      Sim->lastPcl->nextPcl = NULL;
    } else if(Particle == Sim->firstPcl) {
      Sim->firstPcl = Sim->firstPcl->nextPcl;
      Sim->firstPcl->prevPcl = NULL;
    }
    
    mpsa_DeletePcl(Particle);
  }

  return SN_OKAY;
}

/*[ sn_UpdateRadius
 *[ action:  update the radius of a supernova
 *[ objects: takes a supernova particle, pip and a timestep
 */

int sn_UpdateRadius(
  mpsa_Particle *Pcl,
  sn_Pip *Pip,
  float dt
)
{
  /* constant EoverRho5 calculated from initial E = 10^44 J and rho = */
  /* 1.4e-22 kgm^-3                                                   */

  float EoverRho5 = 0.0963;

  /* modification 30th november 2000 - e0 = k M0 - therefore have  */
  /* to choose a value for m0  = 20 m_solar                        */
  /* ie for the purposes of the supernova calculations, all        */
  /* clusters are assumed to be formed from 20 solar mass stars    */
  /* note - change 26th october 2000 - this changes speed too in a */
  /* leapfrog scheme -> prevents initial singular velocity worry   */

  Pip->radius = EoverRho5 * pow(Pcl->age, 0.4) * 
    pow(Pcl->mass / 3.57e-10, 0.2);
  Pip->speed = 0.4 * EoverRho5 * pow((Pcl->age + 0.05), -0.6) * 
    pow(Pcl->mass / 3.57e-10, 0.2);
  
  return SN_OKAY;
}

/*[ sn_Constructor
 *[ action:  create a new SN pip
 *[ objects: takes a pointer to a void * pointer
 */

int sn_Constructor(
  void **NewPip
)
{
  *NewPip = (sn_Pip *) malloc (sizeof(sn_Pip));
  ((sn_Pip *) *NewPip)->radius = 0;

  /* initial speed calculated at t = 0.05 so as to avoid singularity */

  ((sn_Pip *) *NewPip)->speed = 0.232;
  return SN_OKAY;
}

/*[ sn_Destructor
 *[ action:  destroy a supernova pip
 *[ objects: takes a pointer to a void * pointer
 */

int sn_Destructor(
  void **Pip
)
{
  free(*Pip);
  *Pip = NULL;
  return SN_OKAY;
}

/*[ sn_SetDataEntry
 *[ action:  set a data entry to be retrieved
 *[ objects: takes the name of a data entry
 */

int sn_SetDataEntry(
  char *Name
)
{
  if((strcmp(Name, "Radius") == 0) || 
     (strcmp(Name, "radius") == 0)) {
    SnExtraction = SN_RAD;
  } else if((strcmp(Name, "Speed") == 0) ||
	    (strcmp(Name, "speed") == 0)) {
    SnExtraction = SN_SPEED;
  } else {
    return SN_FAIL;
  }
  return SN_OKAY;
}

/*[ sn_GetFloat/IntDataEntry
 *[ action:  get a float or integer data entry
 *[ objects: takes a pointer to a SN pip
 */

int sn_GetIntDataEntry(
  void *Pip
)
{
  return SN_OKAY;
}

float sn_GetFloatDataEntry(
  void *Pip
)
{
  float value;
  switch(SnExtraction){
  case(SN_RAD):
    value = ((sn_Pip *) Pip)->radius;
    break;
  case(SN_SPEED):
    value = ((sn_Pip *) Pip)->speed;
    break;
  default:
    value = ((sn_Pip *) Pip)->radius;
    break;
  }
  return value;
}

/*[ sn_Reader/Writer
 *[ action:  read/write sn data from a Tcl Channel
 *[ objects: takes a pointer to a pip and a tcl chanel
 */

int sn_Reader(
  Tcl_Channel chan,
  void *Pip
)
{
  if(mpsa_ReadFloat(&(((sn_Pip *)Pip)->radius), chan) != MPSA_OKAY) {
    return SN_FAIL;
  }

  if(mpsa_ReadFloat(&(((sn_Pip *)Pip)->speed), chan) != MPSA_OKAY) {
    return SN_FAIL;
  }

  return SN_OKAY;
}

int sn_Writer(
  Tcl_Channel chan,
  void *Pip
)
{
  if(mpsa_WriteFloat(((sn_Pip *)Pip)->radius, chan) != MPSA_OKAY) {
    return SN_FAIL;
  }

  if(mpsa_WriteFloat(((sn_Pip *)Pip)->speed, chan) != MPSA_OKAY) {
    return SN_FAIL;
  }

  return SN_OKAY;
}

/*[ sn_CloudInteractionFind
 *[ action:  find clouds to be shocked in a tree of clouds
 *[ objects: takes two radii, a sn particle and a tree of clouds
 *[          which have their cloud pips selected
 */

int sn_CloudInteractionFind(
  float rmin,
  float rmax,
  mpsa_Particle *SNPcl,
  tree_Node *Root
)
{
  mpsa_Particle *Cloud;
  float dxsq = 0;
  int i;

  for(i = 0; i < 3; i++) {
    dxsq += (SNPcl->x[i] - Root->centre[i]) * (SNPcl->x[i] - Root->centre[i]);
  }

  if(dxsq > ((rmax + Root->size) * (rmax + Root->size))) {
    /* ignore node - too far away! */
  } else {
    if(tree_IsNodeOpen(Root) == TREE_OKAY) {
      for(i = 0; i < 8; i++) {
	 sn_CloudInteractionFind(rmin, rmax, SNPcl, &(Root->Branch[i]));
      } 
    } else {
      if((Cloud = Root->Leaf) != NULL) {
	dxsq = 0;
	for(i = 0; i < 3; i++) {
	  dxsq += (SNPcl->x[i] - Cloud->x[i]) * (SNPcl->x[i] - Cloud->x[i]);
	}
	if((dxsq > rmin * rmin) && (dxsq < rmax * rmax)) {
	  sn_ShockCloud(SNPcl, Cloud);
	}
      }
    }
  }

  return SN_OKAY;
} 

/*[ sn_ShockCloud
 *[ action:  shock/cloud interaction physics
 *[ objects: takes a sn particle and a cloud particle
 */

int sn_ShockCloud(
  mpsa_Particle *SNPcl,
  mpsa_Particle *Cloud
)
{
  float Mach, dv, dx;
  int i;

  dv = 0;
  dx = 0;

  for(i = 0; i < 3; i++) {
    dx += (SNPcl->x[i] - Cloud->x[i]) * (SNPcl->x[i] - Cloud->x[i]);
    dv += (SNPcl->v[i] - Cloud->v[i]) * (SNPcl->v[i] - Cloud->v[i]);
  }

  dx = sqrt(dx);
  dv = sqrt(dv);

  /* shock speed needs to be added to dv 1st december modification! */
  /* query: in fact, is the relative dv even vaguely relevent? i    */
  /* suppose that it is a frame of reference thing....              */


  /* this is obsolete dv += ((sn_Pip *) SNPcl->Pip)->speed; */

  dv += 0.4 * 0.3103 * pow(SNPcl->mass / 3.57e-10, 0.1) * pow(dx, -1.5);

  /* all values are assuming that the supernova is in the sedov phase and
     that the density surrounding the explosion is ~8.4e4 m-3 */

  Mach = 0.0067 * pow(dx, -1.5);

  if(Mach > 10) {
    /* kill the cloud */
    Cloud->extract = 1;

    /* and accelerate it */
    for(i = 0; i < 3; i++) {
      Cloud->v[i] += 0.75 * (Cloud->x[i] - SNPcl->x[i]) * dv / dx;
    }

    if(heat_off == 0) {
      /* and heat it by an appropriate amount */
      ((cloud_Pip *)Cloud->Pip)->T *= 5 * Mach * Mach / 16;
    }
  } else {
    /* accelerate the cloud */
    for(i = 0; i < 3; i++) {
      Cloud->v[i] += 0.75 * (Cloud->x[i] - SNPcl->x[i]) * dv / dx;
    }

    if(heat_off == 0) {
      /* and heat it by an appropriate amount */
      ((cloud_Pip *)Cloud->Pip)->T *= 5 * Mach * Mach / 16;
    }
  }

  return SN_OKAY;
}

int sn_HeatSet(
  int heatval
)
{
  heat_off = heatval;
  return SN_OKAY;
}
