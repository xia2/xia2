/* cloud module operations file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 11th september 2000
 * 
 * modified 26th october to change get random mass
 *
 * modified 2nd november to ensure that collisions are real
 *
 * modified 20th november to add proper cooling
 *
 * modified 21st november to give proper power spectrum fragmentation
 *
 * modified 12th december to add a cloud mass spectrum function
 * which will need the CloudMinimumMass etc. c/f mpsa_ParticleOps.c
 * 
 */

#include "cloud_export.h"
#include "mpsa_private.h"
#include "tree_private.h"
#include <stdlib.h>

int CloudHeatOff = 0;
int CloudExtractFlag = CLOUD_T;

/* This is established from kwan valdes */

float CloudRadiusFactor = 0.303;
float CloudTIndex = 0.33333;
float CloudMIndex = 0.33333;

float CloudTimeStep = 0.1;

/* these define the cloud fragmentation power spectrum */
float CloudMinimumMass = 0;
float CloudMaximumMass = 0;
float CloudPowerIndex = 0;

/*[ cloud_ChangeRadiusFactor
 *[ action:  to do exactly that
 *[ objects: takes the new value
 */

int cloud_ChangeRadiusFactor(
  float NewValue
)
{
  CloudRadiusFactor = NewValue;
  return CLOUD_OKAY;
}

/*[ cloud_Constructor
 *[ action:  create a cloud pip
 *[ objects: takes a pointer to a pointer to a pip!
 */

int cloud_Constructor(
  void **NewPip
)
{
  *NewPip = (cloud_Pip *) malloc (sizeof(cloud_Pip));
  ((cloud_Pip *) *NewPip)->T = 10;
  ((cloud_Pip *) *NewPip)->P = 0;
  ((cloud_Pip *) *NewPip)->radius = 0;
  ((cloud_Pip *) *NewPip)->metal = 0;
  ((cloud_Pip *) *NewPip)->rho = 0;
  ((cloud_Pip *) *NewPip)->shocked = 0;

  return MPSA_OKAY;
}

/*[ cloud_Destructor
 *[ action:  delete a cloud pip
 *[ objects: takes a void **pointer
 */

int cloud_Destructor(
  void **Pip
)
{
  free(*Pip);
  *Pip = NULL;

  return MPSA_OKAY;
}

/*[ cloud_SetDataEntry
 *[ action:  sets a data entry for list extraction
 *[ objects: takes a name of a data entry
 */

int cloud_SetDataEntry(
  char *Name
)
{
  if((strcmp(Name, "T") == 0) ||
     (strcmp(Name, "t") == 0)) {
    CloudExtractFlag = CLOUD_T;
  } else if((strcmp(Name, "P") == 0) || 
	    (strcmp(Name, "p") == 0)) {
    CloudExtractFlag = CLOUD_P;
  } else if((strcmp(Name, "Metal") == 0) ||
	    (strcmp(Name, "metal") == 0)) {
    CloudExtractFlag = CLOUD_METAL;
  } else if((strcmp(Name, "Radius") == 0) ||
	    (strcmp(Name, "radius") == 0)) {
    CloudExtractFlag = CLOUD_RADIUS;
  } else if((strcmp(Name, "Rho") == 0) ||
	    (strcmp(Name, "rho") == 0)) {
    CloudExtractFlag = CLOUD_RHO;
  } else if((strcmp(Name, "Shocked") == 0) || 
	    (strcmp(Name, "shocked") == 0)) {
    CloudExtractFlag = CLOUD_SHOCK;
  } else {
    return MPSA_FAIL;
  }

  return MPSA_OKAY;
}

/*[ cloud_GetIntDataEntry
 *[ action:  get an integer valued data entry from a cloud pip (redundant)
 *[ objects: takes a pointer to a pip of hopefully the right type!
 */

int cloud_GetIntDataEntry(
  void *Pip
)
{
  int value;
  if(CloudExtractFlag == CLOUD_SHOCK) {
    value = ((cloud_Pip *) Pip)->shocked;
  } else {
    value = 0;
  }
  return value;
}

/*[ cloud_GetFloatDataEntry
 *[ action:  get an float valued data entry from a cloud pip
 *[ objects: takes a pointer to a pip of hopefully the right type!
 */

float cloud_GetFloatDataEntry(
  void *Pip
)
{
  float value;
  if(CloudExtractFlag == CLOUD_T) {
    value = ((cloud_Pip *) Pip)->T;
  } else if(CloudExtractFlag == CLOUD_P) {
    value = ((cloud_Pip *) Pip)->P;
  } else if(CloudExtractFlag == CLOUD_METAL) {
    value = ((cloud_Pip *) Pip)->metal;
  } else if(CloudExtractFlag == CLOUD_RADIUS) {
    value = ((cloud_Pip *) Pip)->radius;
  } else if(CloudExtractFlag == CLOUD_RHO) {
    value = ((cloud_Pip *) Pip)->rho;
  } else {
    value = 0;
  }

  return value;
}

/*[ cloud_Reader
 *[ action:  read data into a cloud from a tcl channel
 *[ objects: takes a pointer to a pip and a tcl channel
 */

int cloud_Reader(
  Tcl_Channel chan,
  void *Pip
)
{
  if(mpsa_ReadFloat(&(((cloud_Pip *)Pip)->T), chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_ReadFloat(&(((cloud_Pip *)Pip)->P), chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_ReadFloat(&(((cloud_Pip *)Pip)->metal), chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_ReadFloat(&(((cloud_Pip *)Pip)->radius), chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_ReadFloat(&(((cloud_Pip *)Pip)->rho), chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_ReadInteger(&(((cloud_Pip *)Pip)->shocked), chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  return MPSA_OKAY;
}

/*[ cloud_Writer
 *[ action:  write data from a cloud pip to a tcl channel
 *[ objects: takes a pointer to a pip and a tcl channel
 */

int cloud_Writer(
  Tcl_Channel chan,
  void *Pip
)
{
  if(mpsa_WriteFloat(((cloud_Pip *)Pip)->T, chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_WriteFloat(((cloud_Pip *)Pip)->P, chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_WriteFloat(((cloud_Pip *)Pip)->metal, chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_WriteFloat(((cloud_Pip *)Pip)->radius, chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_WriteFloat(((cloud_Pip *)Pip)->rho, chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  if(mpsa_WriteInteger(((cloud_Pip *)Pip)->shocked, chan) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  return MPSA_OKAY;
}

/*[ cloud_SetRadius
 *[ action:  set radius of a cloud assuming constant density
 *[ objects: takes a pointer to a cloud
 */

int cloud_SetRadius(
  mpsa_Particle *Pcl
)
{
  float r;

  /* r = k (m T) ^ 0.333 */
  /* nominal T = 10K */

  r = CloudRadiusFactor * pow(Pcl->mass, CloudMIndex) * 
    pow(((cloud_Pip *) Pcl->Pip)->T / 10, CloudTIndex);

  ((cloud_Pip *) Pcl->Pip)->radius = r;

  return CLOUD_OKAY;
}

/*[ cloud_TreeCollisionSearch
 *[ action:  searches tree for clouds to merge and merges them
 *[ objects: takes a cloud particle and a tree, and a search radius
 */

int cloud_TreeCollisionSearch(
  float Radius,
  mpsa_Particle *Pcl,
  tree_Node *Node
)
{
  mpsa_Particle *Leaf;
  float dxsq = 0;
  int i;

  for(i = 0; i < 3; i++) {
    dxsq += (Pcl->x[i] - Node->centre[i]) * (Pcl->x[i] - Node->centre[i]);
  }

  if(dxsq > ((Radius + Node->size) * (Radius + Node->size))) {
    /* ignore node - too far away! */
  } else {
    if(tree_IsNodeOpen(Node) == TREE_OKAY) {

      for(i = 0; i < 8; i++) {
	cloud_TreeCollisionSearch(Radius, Pcl, &(Node->Branch[i]));
      } 

    } else {

      /* lots of conditions on the particles to see if they have indeed */
      /* collided */

      if(((Leaf = Node->Leaf) != NULL) && (Leaf->type == Pcl->type) &&
        (Leaf->flag != CLOUD_FAIL) && (Pcl != Leaf)) {

	/* candidates for collision, but must check! */

	dxsq = 0;

	for(i = 0; i < 3; i++) {
	  dxsq += (Pcl->x[i] - Leaf->x[i]) * (Pcl->x[i] - Leaf->x[i]);
	}

	if(dxsq < Radius * Radius) {
	  cloud_CollideClouds(Pcl, Leaf);
	}
      }
    }
  }

  return CLOUD_OKAY;
}

/*[ cloud_CollideClouds
 *[ action:  perform the task of colliding two clouds
 *[ objects: takes two cloud particles
 *[ notes:   here is the place to put the cloud cloud collision physics
 */

/* notes:
   added new - if the clouds collide but are of vastly different temperatures
   then one will pass through the other accreting a small amount of material

   1st november 2000
   cloud collisions now define origin as where most of the mass came from. 
   this'll be more realistic i think - gw

   put limit on ratio of temperatures of ~10
*/

int cloud_CollideClouds(
  mpsa_Particle *PclA,
  mpsa_Particle *PclB
)
{
  float NewMass, NewT, NewMetal;
  float T1, T2, P, rho;
  float v, rad, newv[3];
  int i;
  float ELost;
  cloud_Pip *PipA, *PipB;

  PipA = (cloud_Pip *) PclA->Pip;
  PipB = (cloud_Pip *) PclB->Pip;

  T1 = PipA->T;
  T2 = PipA->T;

  v = 0;

  for(i = 0; i < 3; i++) {
    v += (PclA->v[i] - PclB->v[i]) * (PclA->v[i] - PclB->v[i]);
  }

  if(((T1/T2) > 0.1) && ((T1/T2) < 10)) {

    NewMass = PclA->mass + PclB->mass;
    
    NewT = (PipA->T * PclA->mass + PipB->T * PclB->mass) / NewMass;
    NewMetal = (PipA->metal * PclA->mass + PipB->metal * PclB->mass) / NewMass;
    P = (PipA->P * PclA->mass + PipB->P * PclB->mass) / NewMass;
    rho = (PipA->rho * PclA->mass + PipB->rho * PclB->mass) / NewMass;

    for(i = 0; i < 3; i++) {
      newv[i] = (PclA->v[i] * PclA->mass + PclB->v[i] * PclB->mass) / NewMass;
    }

    /* mark PclB as dead, and set mass = 0, for belt and braces */
    /* but first determine which origin the cloud should belong to */

    if(PclA->mass > PclB->mass) {
      /* do nothing - preserve ownership */
    } else {
      /* change cloud ownership according to mass */
      PclA->origin = PclB->origin;
    }

    /* and the amount of kinetic energy lost to the collision, in the */
    /* frame of particle A */

    ELost = 0.5 * PclB->mass * v;

    PclB->flag = CLOUD_FAIL;
    PclB->mass = 0;
    PclA->mass = NewMass;

    PipA->metal = NewMetal;
    PipA->T = NewT;

    /* note that v here is v squared */

    if(v > (5 * P / (3 * rho))) {
      /* incoming velocity greater than sound speed */
      PipA->shocked = 1;
    }

    /* value here calculated from cv = 1.2e4 J/K/kg */

    if(CloudHeatOff == 0) {
      PipA->T += ELost * 1.08e7;
    }

    /* conserve momentum! */

    for(i = 0; i < 3; i++) {
      PclA->v[i] = newv[i];
    }

  } else {

    /* have high density difference situation */
    /* so transfer some mass from the warm cloud to the cool one */
    /* in proportion to r/v */

    v = sqrt(v);

    if(v == 0) {
      v = 0.03;
    }

    if(T1 > T2) {
      float TransMass;
      rad = PipA->radius;
      TransMass = 0.5 * CloudTimeStep * (rad / v) * PclA->mass;
      if(PclA->mass > TransMass) {
	PclB->mass += TransMass;
	PclA->mass -= TransMass;
      } else {
	PclB->mass += PclA->mass;
	PclA->mass = 0;
	PclA->flag = CLOUD_FAIL;
      }
    } else {
      float TransMass;
      rad = PipB->radius;
      TransMass = 0.5 * CloudTimeStep * (rad / v) * PclB->mass;
      if(PclB->mass > TransMass) {
	PclA->mass += TransMass;
	PclB->mass -= TransMass;
      } else {
	PclA->mass += PclB->mass;
	PclB->mass = 0;
	PclB->flag = CLOUD_FAIL;
      }
    }
  }

  return CLOUD_OKAY;
}
  
/*[ cloud_SetFragParam
 *[ action:  sets the fragmentation parameters
 *[ objects: takes three integers, minimum and maximum mass and power
 *[          spectrum index
 */

int cloud_SetFragParam(
  float MMin,
  float MMax,
  float index
)
{
  CloudMinimumMass = MMin;
  CloudMaximumMass = MMax;
  CloudPowerIndex = index;
  return CLOUD_OKAY;
}

/*[ cloud_GetRandomMass
 *[ action:  get a random mass from the distribution detailed above
 *[ objects: returns a float, takes nothing although uses global variables
 */

float cloud_GetRandomMass() {

  /* 2nd november 2000 modification, no longer works in the same way   */
  /* as that can be very nasty sometimes if the spectrum is high index */
  /* and the limits are far apart - however, will leave it for a mo    */

  float rnd, m;

  /* this is the old way...

  m = gwrand48() * (CloudMaximumMass - CloudMinimumMass) + CloudMinimumMass;
  rnd = gwrand48();

  if(CloudPowerIndex < 0) {
    if(rnd > (pow((m / CloudMinimumMass), CloudPowerIndex))) {
      m = cloud_GetRandomMass();
    } else {
      return m;
    }
  } else {
    if(rnd > (pow((m / CloudMaximumMass), CloudPowerIndex))) {
      m = cloud_GetRandomMass();
    } else {
      return m;
    }
  }

  */

  rnd = gwrand48();
  m = pow((rnd * (pow(CloudMaximumMass, CloudPowerIndex + 1) - 
    pow(CloudMinimumMass, CloudPowerIndex + 1)) + 
    pow(CloudMinimumMass, CloudPowerIndex + 1)), 1 / (CloudPowerIndex + 1));

  return m;

}
    
/*[ cloud_FragmentCloud
 *[ action:  fragment cloud into many smaller clouds
 *[ objects: takes a cloud particle and a pointer to a simulation
 */

int cloud_FragmentCloud(
  mpsa_Particle *CloudPcl,
  mpsa_Simulation *Sim,
  mpsa_Pip *CloudPip
)
{
  mpsa_ParticleDefn *CloudDefn;
  float NewCloudMass;
  float dx[3], dv[3];
  int i;

  if(CloudMaximumMass == 0) {
    return CLOUD_FAIL;
  }

  if(mpsa_GetPclDefnFromID(CloudPcl->type, &CloudDefn) != MPSA_OKAY) {
    return CLOUD_FAIL;
  }

  while(CloudPcl->mass > CloudMinimumMass) {
    NewCloudMass = cloud_GetRandomMass();
    if(NewCloudMass > CloudPcl->mass) {
      /* ignore this one and start again!     */
      /* in fact, our work here must be done! */
      return CLOUD_OKAY;
    } else {
      CloudPcl->mass -= NewCloudMass;
      for(i = 0; i < 3; i++) {
	dx[i] = (gwrand48() - 0.5) * ((cloud_Pip *) CloudPcl->Pip)->radius + 
          CloudPcl->x[i];
	/* v. dispersion from kv */
	dv[i] = (gwrand48() - 0.5) * 0.03 + CloudPcl->v[i];
      }
      if(mpsa_PclCreateExact(Sim, CloudDefn, NewCloudMass, dx, dv) != 
        MPSA_OKAY) {
	return CLOUD_FAIL;
      }

      /* note that the cloud pip is necessary to get the new cloud */
      /* initialised */

      if(mpsa_SetPipToPipType(Sim->lastPcl, CloudPip) != MPSA_OKAY) {
	return CLOUD_FAIL;
      }

      ((cloud_Pip *) Sim->lastPcl->Pip)->T = ((cloud_Pip *) CloudPcl->Pip)->T;
      ((cloud_Pip *) Sim->lastPcl->Pip)->metal = 
        ((cloud_Pip *) CloudPcl->Pip)->metal;
    }
  }

  return CLOUD_OKAY;
}

/*[ cloud_CoolCloud
 *[ action:  cool a cloud particle
 *[ objects: takes a pointer to a particle with a cloud pip
 */

int cloud_CoolCloud(
  mpsa_Particle *Cloud,
  float dt
)
{
  float Tnew, T;

  /* cooling now calculated by analytical function              */ 
  /* t(n+1) = (1 / t(n) + k dt) ^ -1                            */
  /* the parameter k is determined to be the total cooling rate */

  float k = 0.1;

  T = ((cloud_Pip *) Cloud->Pip)->T;

  Tnew = 1 / ((1 / T) + k * dt);

  if(Tnew < 10) {
    Tnew = 10;
  }

  ((cloud_Pip *) Cloud->Pip)->T = Tnew;

  return CLOUD_OKAY;
}

int cloud_SetHeat(
  int NewVal
)
{
  CloudHeatOff = NewVal;
  return CLOUD_OKAY;
}

int cloud_SetIndices(
  float newMindex,
  float newTindex
)
{
  CloudMIndex = newMindex;
  CloudTIndex = newTindex;
  return CLOUD_OKAY;
}

/*[ cloud_TreeCollisionSearch2
 *[ action:  searches tree for clouds to merge and merges them
 *[ objects: takes a cloud particle and a tree, and a search radius
 */

int cloud_TreeCollisionSearch2(
  float Radius,
  float dt,
  mpsa_Particle *Pcl,
  tree_Node *Node
)
{
  mpsa_Particle *Leaf;
  float dxsq = 0, ta, tb, v = 0;
  int i;
  float dvsq = 0, dvdx = 0;
  float r1, r2;

  for(i = 0; i < 3; i++) {
    dxsq += (Pcl->x[i] - Node->centre[i]) * (Pcl->x[i] - Node->centre[i]);
  }

  if(dxsq > ((Radius + Node->size) * (Radius + Node->size))) {
    /* ignore node - too far away! */
  } else {
    if(tree_IsNodeOpen(Node) == TREE_OKAY) {

      for(i = 0; i < 8; i++) {
	cloud_TreeCollisionSearch(Radius, Pcl, &(Node->Branch[i]));
      } 

    } else {

      /* lots of conditions on the particles to see if they have indeed */
      /* collided */

      if(((Leaf = Node->Leaf) != NULL) && (Leaf->type == Pcl->type) &&
        (Leaf->flag != CLOUD_FAIL) && (Pcl != Leaf)) {

	/* candidates for collision, but must check! */

	dxsq = 0;

	for(i = 0; i < 3; i++) {
	  dxsq += (Pcl->x[i] - Leaf->x[i]) * (Pcl->x[i] - Leaf->x[i]);
	}

	if(dxsq < Radius * Radius) {
	  /* might be a collision in the next timestep - so check! */
	  
	  /* old and faulty method...

	  for(i = 0; i < 3; i++) {
	    dvsq += (Pcl->v[i] - Leaf->v[i]) * (Pcl->v[i] - Leaf->v[i]);
	    dvdx += (Pcl->v[i] - Leaf->v[i]) * (Pcl->x[i] - Leaf->x[i]);
	  }
	  ta = (-dvdx - (((cloud_Pip *) Pcl->Pip)->radius + 
	    ((cloud_Pip *) Leaf->Pip)->radius) * sqrt(dvsq)) / dvsq;
	  tb = (-dvdx + (((cloud_Pip *) Pcl->Pip)->radius + 
	    ((cloud_Pip *) Leaf->Pip)->radius) * sqrt(dvsq)) / dvsq;
	  if((ta > 0 && ta < dt) || (tb > 0 && tb < dt)) {
	    cloud_CollideClouds(Pcl, Leaf);
	  }
	 
  	  */

	  /* new and shiny method  */
	  /* now old and tarnished 
	  for(i = 0; i < 3; i++) {
	    dvsq += (Pcl->v[i] - Leaf->v[i]) * (Pcl->v[i] - Leaf->v[i]);
	    dvdx += (Pcl->v[i] - Leaf->v[i]) * (Pcl->x[i] - Leaf->x[i]);
	  }
	  if((dvdx * dvdx / dvsq) >= ((sqrt(dxsq) - 
            ((cloud_Pip *) Pcl->Pip)->radius - 
            ((cloud_Pip *) Leaf->Pip)->radius) * (sqrt(dxsq) - 
            ((cloud_Pip *) Pcl->Pip)->radius -
            ((cloud_Pip *) Leaf->Pip)->radius))) {
	    ta = sqrt(dxsq / dvsq);
	    if(ta < dt && ta > 0) {
       	      cloud_CollideClouds(Pcl, Leaf);
	    }  
	  }
          */

          /* so an even newer and shinier method is employed */

          for(i = 0; i < 3; i++) {
	    dvsq += (Pcl->v[i] - Leaf->v[i]) * (Pcl->v[i] - Leaf->v[i]);
	    dvdx += (Pcl->v[i] - Leaf->v[i]) * (Pcl->x[i] - Leaf->x[i]);
	  }
          
	  ta = - dvdx / dvsq;
	  if(ta < 0) {
	    ta = 0;
	  } else if(ta > dt) {
	    ta = dt;
	  }

	  r1 = ((cloud_Pip *) Pcl->Pip)->radius;
	  r2 = ((cloud_Pip *) Leaf->Pip)->radius;

	  if(dxsq + 2 * ta * dvdx + ta * ta * dvsq < (r1 + r2) * (r1 + r2)) {
	    /* then collide the clouds */
	    cloud_CollideClouds(Pcl, Leaf);
	  }  
        }
      }   
    }
  }

  return CLOUD_OKAY;
}

/*[ cloud_MassSpectrum
 *[ action:  calculate mass spectrum information from a list of particles
 *[ objects: takes a tcl interpreter, a list and a flag
 */

int cloud_MassSpectrum(
  Tcl_Interp *interp,
  mpsa_List *List,
  int print
)
{
  float Mass[101], Bin[101], Mlow = 0, Mhigh = 0;
  float LogMass[101], LogBin[101], LogMlow = 0, LogMhigh = 0;
  float Range, LogRange, k, ChiSq, ChiMin, Expected;
  int i, nbinsA, nbinsB, lowest, Break, KeepBreak;
  float KeepIndexA, KeepIndexB;
  mpsa_Link *Link;
  float powerA, meanxA, meanyA, sumxxA, sumxyA, interceptA;
  float powerB, meanxB, meanyB, sumxxB, sumxyB, interceptB;
  char out[20], outbin[20], outmass[20];
  char outA[20], outB[20], outBreak[20];

  /* initialise arrays */

  for(i = 0; i < 101; i++) {
    Mass[i] = 0;
    LogMass[i] = 0;
    Bin[i] = 0;
    LogBin[i] = 0;
  }

  if(List->firstLink == NULL) {
    /* list is empty! */
    sprintf(out, "%e", Mlow);
    Tcl_AppendResult(interp, out, (char *) NULL);
    return CLOUD_OKAY;
  }

  Mlow = List->firstLink->Pcl->mass;
  Mhigh = List->firstLink->Pcl->mass;
  
  for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    if(Link->Pcl->mass < Mlow) {
      Mlow = Link->Pcl->mass;
    }
    if(Link->Pcl->mass > Mhigh) {
      Mhigh = Link->Pcl->mass;
    }
  }

  /* Mass now stores the logs of the bin values */

  Range = Mhigh - Mlow;
  LogRange = log10(Mhigh / Mlow);
  
  k = pow(10, 0.01 * LogRange);

  LogMhigh = log10(Mhigh);
  LogMlow = log10(Mlow);

  if(Range == 0) {
    /* this will happen at first! */
    sprintf(out, "%e", Range);
    Tcl_AppendResult(interp, out, (char *) NULL);
    return TCL_OK;
  }

  for(i = 0; i < 101; i++) {
    LogMass[i] = LogMlow + i * (LogRange / 100);
    Bin[i] = 0;
  }

  for(i = 0; i < 101; i++) {
    Mass[i] = pow(10, LogMass[i]);
  }

  for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    i = 100.0 * (log10(Link->Pcl->mass/Mlow) / LogRange);
    Bin[i] += Link->Pcl->mass;
  }
  
  /* determine the lower limit of the useful bins          */
  /* since there will be the detritus of clouds below this */

  if(CloudMinimumMass == 0) {
    Tcl_AppendResult(interp, "Need to setup frag. parameters", (char *) NULL);
    return CLOUD_OKAY;
  }

  if(Mlow < CloudMinimumMass) {
    lowest = 100 * (log10(CloudMinimumMass/Mlow) / LogRange);
  } else {
    lowest = 0;
  }

  for(i = 0; i < 101; i++) {
    if(Bin[i] != 0) {
      /* must divide by the bin size! */
      /* so will output mn(m)         */
      Bin[i] = Bin[i] / ((k - 1) * Mass[i]);
      LogBin[i] = log10(Bin[i]);
    }
  }
  
  /* chi squared test to find the break point in the power spectrum */

  ChiMin = 1e4;

  for(Break = lowest + 3; Break < 97; Break++) {
    /* fit lower section - `A' */
    meanxA = 0;
    meanyA = 0;
    nbinsA = 0;

    for(i = lowest; i <= Break; i++) {
      if(Bin[i] != 0) {
	meanxA += LogMass[i];
	meanyA += LogBin[i];
	nbinsA ++;
      }
    }
  
    if(nbinsA != 0) {
      meanxA = meanxA / nbinsA;
      meanyA = meanyA / nbinsA;
    }

    sumxxA = 0;
    sumxyA = 0;
  
    for(i = lowest; i <= Break; i++) {
      if(Bin[i] != 0) {
	sumxxA += (LogMass[i] - meanxA) * (LogMass[i] - meanxA);
	sumxyA += (LogMass[i] - meanxA) * (LogBin[i] - meanyA);
      }
    }
  
    powerA = sumxyA / sumxxA;
    interceptA = meanyA - meanxA * powerA;

    /* fit upper section - `B' */
    meanxB = 0;
    meanyB = 0;
    nbinsB = 0;

    for(i = Break; i <= 100; i++) {
      if(Bin[i] != 0) {
	meanxB += LogMass[i];
	meanyB += LogBin[i];
	nbinsB ++;
      }
    }
  
    if(nbinsB != 0) {
      meanxB = meanxB / nbinsB;
      meanyB = meanyB / nbinsB;
    }

    sumxxB = 0;
    sumxyB = 0;
  
    for(i = Break; i <= 100; i++) {
      if(Bin[i] != 0) {
	sumxxB += (LogMass[i] - meanxB) * (LogMass[i] - meanxB);
	sumxyB += (LogMass[i] - meanxB) * (LogBin[i] - meanyB);
      }
    }
  
    powerB = sumxyB / sumxxB;
    interceptB = meanyB - meanxB * powerB;

    /* now calculate the quality of the fit */

    ChiSq = 0;

    for(i = lowest; i <= Break; i++) {
      Expected = LogMass[i] * powerA + interceptA;
      if(Expected != 0) {
	ChiSq += (LogBin[i] - Expected) * (LogBin[i] - Expected) / Expected;
      } else {
	ChiSq += LogBin[i] * LogBin[i];
      }
    }

    for(i = Break; i <= 100; i++) {
      Expected = LogMass[i] * powerB + interceptB;
      if(Expected != 0) {
	ChiSq += (LogBin[i] - Expected) * (LogBin[i] - Expected) / Expected;
      } else {
	ChiSq += LogBin[i] * LogBin[i];
      }
    }

    if(ChiSq < ChiMin) {
      KeepBreak = Break;
      KeepIndexA = powerA;
      KeepIndexB = powerB;
      ChiMin = ChiSq;
    }
  }

  if(print == 0) {
    
    /* mass spectrum index to be printed */
    
    sprintf(outA, "%e ", KeepIndexA);
    sprintf(outB, "%e ", KeepIndexB);
    sprintf(out, "%e ", Mass[KeepBreak]);

    Tcl_AppendResult(interp, outA, outB, out, (char *) NULL);

  } else {
    
    /* mass spectrum data wanted for output */
    
    for(i = 0; i < 101; i++) {
      sprintf(outmass, "%e", LogMass[i]);
      sprintf(outbin, "%e", LogBin[i]);
      Tcl_AppendResult(interp, outmass, " ", outbin, "\n", (char *) NULL);
    }
  }
 
  return CLOUD_OKAY;
}
