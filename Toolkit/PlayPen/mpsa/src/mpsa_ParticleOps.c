/* gsimII mpsa particle operations file v1.0
 * maintained by g.winter
 * 15th august 2000
 * 
 * 
 */

#include "mpsa_private.h"
#include <math.h>

mpsa_ParticleDefn *MostRecenttype = NULL;
mpsa_Pip *MostRecentPip = NULL;
int MostRecentAnswer = MPSA_FAIL;
int MostRecentPipNo = 0;

/*[ mpsa_PclCreate/PclCreateExact
 *[ action:  creates a particle and appropriate pips depending on type,
 *[          making use of pip constructors detailed in pip definition.
 *[          global variables prevent repeated definition searches
 *[ objects: takes a simulation, and appends a particle of given type
 */

int mpsa_PclCreate(
  mpsa_Simulation *Simulation,
  mpsa_ParticleDefn *type
)
{
  int i, NPips, typeID;
  mpsa_Pip **PipList;
  mpsa_Particle *NewPcl;
  MostRecenttype = type;
  typeID = type->DynamicID;
  NPips = type->NPips;
  PipList = type->Piptypes;

  NewPcl = (mpsa_Particle *) malloc (sizeof(mpsa_Particle));

  NewPcl->type = typeID;
  NewPcl->age = 0;
  NewPcl->flag = 0;
  NewPcl->extract = 0;
  NewPcl->origin = 0;

  if(NPips != 0) {
    NewPcl->PipList = (void **) malloc (sizeof(void *) * NPips);
    for(i = 0; i < NPips; i++) {
      PipList[i]->Constructor(&(NewPcl->PipList[i]));
    }
  } else {
    NewPcl->PipList = NULL;
  }

  mpsa_PclInitRnd(NewPcl);
  mpsa_AddPclToSimulation(Simulation, NewPcl);

  return MPSA_OKAY;
}

int mpsa_PclCreateExact(
  mpsa_Simulation *Simulation,
  mpsa_ParticleDefn *type,
  float m,
  float x[3],
  float v[3]
)
{
  int i, NPips, typeID;
  mpsa_Pip **PipList;
  mpsa_Particle *NewPcl;

  MostRecenttype = type;
  typeID = type->DynamicID;
  NPips = type->NPips;
  PipList = type->Piptypes;

  NewPcl = (mpsa_Particle *) malloc (sizeof(mpsa_Particle));

  NewPcl->type = typeID;

  if(NPips != 0) {
    NewPcl->PipList = (void **) malloc (sizeof(void *) * NPips);
    for(i = 0; i < NPips; i++) {
      PipList[i]->Constructor(&(NewPcl->PipList[i]));
    }
  } else {
    NewPcl->PipList = NULL;
  }

  NewPcl->Pip = NULL;

  for(i = 0; i < 3; i++) {
    NewPcl->x[i] = x[i];
    NewPcl->v[i] = v[i];
    NewPcl->a[i] = 0;
  }

  NewPcl->mass = m;
  NewPcl->age = 0;
  NewPcl->flag = 0;
  NewPcl->extract = 0;
  NewPcl->origin = 0;
  mpsa_AddPclToSimulation(Simulation, NewPcl);

  return MPSA_OKAY;
}

int mpsa_PclCreateExactAcc(
  mpsa_Simulation *Simulation,
  mpsa_ParticleDefn *type,
  float m,
  float x[3],
  float v[3],
  float a[3]
)
{
  int i, NPips, typeID;
  mpsa_Pip **PipList;
  mpsa_Particle *NewPcl;

  MostRecenttype = type;
  typeID = type->DynamicID;
  NPips = type->NPips;
  PipList = type->Piptypes;

  NewPcl = (mpsa_Particle *) malloc (sizeof(mpsa_Particle));

  NewPcl->type = typeID;

  if(NPips != 0) {
    NewPcl->PipList = (void **) malloc (sizeof(void *) * NPips);
    for(i = 0; i < NPips; i++) {
      PipList[i]->Constructor(&(NewPcl->PipList[i]));
    }
  } else {
    NewPcl->PipList = NULL;
  }

  for(i = 0; i < 3; i++) {
    NewPcl->x[i] = x[i];
    NewPcl->v[i] = v[i];
    NewPcl->a[i] = a[i];
  }

  NewPcl->mass = m;
  NewPcl->age = 0;
  NewPcl->flag = 0;
  NewPcl->extract = 0;
  NewPcl->origin = 0;
  mpsa_AddPclToSimulation(Simulation, NewPcl);

  return MPSA_OKAY;
}

/*[ mpsa_DeletePcl
 *[ action:  deletes a particle and all pips associated, calling the 
 *[          destructors of those pips. again uses global variables to
 *[          prevent repeated searches.
 *[ objects: takes a pointer to the particle to be deleted
 */ 

int mpsa_DeletePcl(
  mpsa_Particle *Pcl
)
{
  int i, n;

  if(Pcl->type != MostRecenttype->DynamicID) {
    mpsa_GetPclDefnFromID(Pcl->type, &MostRecenttype);
  }

  if((n = MostRecenttype->NPips) != 0) {
    for(i = 0; i < n; i++) {
      MostRecenttype->Piptypes[i]->Destructor(&(Pcl->PipList[i]));
    }
  }

  if(Pcl->prevPcl != NULL) {
    Pcl->prevPcl->nextPcl = Pcl->nextPcl;
  }

  if(Pcl->nextPcl != NULL) {
    Pcl->nextPcl->prevPcl = Pcl->prevPcl;
  }

  free(Pcl);

  return MPSA_OKAY;
}

/*[ mpsa_DeletePcls
 *[ action:  routine to delete all particles after a given one in a list
 *[          used when deleting simulation and calls mpsa_DeletePcl
 *[ objects: takes pointer to first particle to be deleted
 */

int mpsa_DeletePcls(
  mpsa_Particle *firstPcl
)
{
  mpsa_Particle *PlaceHolder, *Pcl;

  for(Pcl = firstPcl; Pcl != NULL; Pcl = PlaceHolder) {
    PlaceHolder = Pcl->nextPcl;
    mpsa_DeletePcl(Pcl);
  }

  return MPSA_OKAY;
}

/*[ mpsa_PclInitRnd
 *[ action:  initialises particle structure values with random or default
 *[          values to prevent particles being created on top of each other
 *[ objects: takes a pointer to a particle
 */

int mpsa_PclInitRnd(
  mpsa_Particle *Pcl
)
{
  int i;

  for(i = 0; i < 3; i++) {
    Pcl->x[i] = gwrand48();
    Pcl->v[i] = 0;
    Pcl->a[i] = 0;
  }
  Pcl->mass = .0001;
  Pcl->phi = 0;
  Pcl->origin = 0;
  Pcl->extract = 0;
  Pcl->flag = 0;
  Pcl->Pip = NULL;

  return MPSA_OKAY;
}

/*[ mpsa_AddPclToSimulation
 *[ action:  adds a newly created particle to a simulation structure, 
 *[          performing the neseccary book keeping operations
 *[ objects: takes a pointer to a simulation and a pointer to a new particle
 */

int mpsa_AddPclToSimulation(
  mpsa_Simulation *Simulation,
  mpsa_Particle *Pcl
)
{
  int n;

  n = Simulation->NPcls;

  Pcl->index = n;

  if(Simulation->firstPcl == NULL) {
    Simulation->firstPcl = Pcl;
    Simulation->lastPcl = Pcl;
    Pcl->nextPcl = NULL;
    Pcl->prevPcl = NULL;
  } else { 
    Pcl->nextPcl = NULL;
    Pcl->prevPcl = Simulation->lastPcl;
    Simulation->lastPcl->nextPcl = Pcl;
    Simulation->lastPcl = Pcl;
  }
  Simulation->NPcls ++;

  return MPSA_OKAY;
}

/*[ mpsa_GetType
 *[ action:  obtains the dynamicly allocated numerical ID of a given particle
 *[          type determined by it's name
 *[ objects: takes a tcl interpreter and a particle type name, returns dynamic 
 *[          identifier in *type
 */

int mpsa_GetType(
  Tcl_Interp *interp,
  char *Label,
  int *type
)
{
  mpsa_ParticleDefn *Defn;

  if(mpsa_GetPclDefn(interp, Label, &Defn) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  *type = Defn->DynamicID;

  return MPSA_OKAY;
}

/*[ mpsa_GetPipData
 *[ action:  obtains the pip type listing for a given particle type determined
 *[          by it's name
 *[ objects: takes a tcl interpreter and a name, returns a list of pip 
 *[          definitions
 */

int mpsa_GetPipData(
  Tcl_Interp *interp,
  char *Label,
  mpsa_Pip ***PipData,
  int *NPips
)
{
  mpsa_ParticleDefn *Defn;

  if(mpsa_GetPclDefn(interp, Label, &Defn) != MPSA_OKAY) {
    return MPSA_FAIL;
  }

  *NPips = Defn->NPips;
  *PipData = Defn->Piptypes;

  return MPSA_OKAY;
}

/*[ mpsa_SetPipToPipType
 *[ action:  set the pip in a particle to point to the correct pip type
 *[          in the pip list, using global variables to prevent repeated 
 *[          searches
 *[ objects: takes a particle and a pip definition
 */

int mpsa_SetPipToPipType(
  mpsa_Particle *Pcl,
  mpsa_Pip *ThisPiptype
)
{
  if(Pcl->type != MostRecenttype->DynamicID) {
    mpsa_GetPclDefnFromID(Pcl->type, &MostRecenttype);
  }

  if(MostRecenttype->Piptypes[MostRecentPipNo] != ThisPiptype) {
    if(mpsa_GetPipPosition(MostRecenttype, ThisPiptype, &MostRecentPipNo) !=
      MPSA_OKAY) {
      return MPSA_FAIL;
    }
  }

  Pcl->Pip = Pcl->PipList[MostRecentPipNo];
  return MPSA_OKAY;
}

/*[ mpsa_ParticleHavePip
 *[ action:  a routine to test if a particle has a given pip, again using 
 *[          global variables to prevent excessive lookups. used in list
 *[          append commands
 *[ objects: takes a particle and a pip, returns MPSA_OKAY/FAIL
 */

int mpsa_ParticleHavePip(
  mpsa_Particle *Pcl,
  mpsa_Pip *Pip
)
{
  if(Pcl->type == MostRecenttype->DynamicID) {
    if(Pip == MostRecentPip) {
      return MostRecentAnswer;
    } else {
      MostRecentPip = Pip;
      MostRecentAnswer = mpsa_DoesPclHavePip(MostRecentPip, 
        MostRecenttype);
      return MostRecentAnswer;
    }
  } else {
    if(mpsa_GetPclDefnFromID(Pcl->type, &MostRecenttype) != 
      MPSA_OKAY) {
      return MPSA_FAIL;
    }
    MostRecentPip = Pip;
    MostRecentAnswer = mpsa_DoesPclHavePip(MostRecentPip, MostRecenttype);
    return MostRecentAnswer;
  }
}

/*[ mpsa_MassSpectrum
 *[ action:  calculate mass spectrum information from a list of particles
 *[ objects: takes a tcl interpreter, a list and a flag
 */

int mpsa_MassSpectrum(
  Tcl_Interp *interp,
  mpsa_List *List,
  int print
)
{
  float Mass[21], Bin[21], Mlow = 0, Mhigh = 0;
  float Range;
  int i, nbins;
  mpsa_Link *Link;
  float pow, meanx, meany, sumxx, sumxy;
  char out[20], outbin[20], outmass[20];

  if(List->firstLink == NULL) {
    /* list is empty! */
    sprintf(out, "%e", Mlow);
    Tcl_AppendResult(interp, out, (char *) NULL);
    return MPSA_OKAY;
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


  Range = log10(Mhigh) - log10(Mlow);
  
  if(Range == 0) {
    /* this will happen at first! */
    sprintf(out, "%e", Range);
    Tcl_AppendResult(interp, out, (char *) NULL);
    return TCL_OK;
  }

  for(i = 0; i < 21; i++) {
    Mass[i] = Mlow + i * (Range / 20);
    Bin[i] = 0;
  }

  for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    i = 20 * (log10(Link->Pcl->mass/Mlow) / Range);
    Bin[i] += Link->Pcl->mass;
  }
  
  for(i = 0; i < 21; i++) {
    if(Bin[i] != 0) {
      /* must divide by the bin size! */
      /* so will output mn(m)         */
      Bin[i] = log10(Bin[i]) / (((Range / 20) - 1) * Mass[i]);
    }
  }
  
  meanx = 0;
  meany = 0;
  
  nbins = 0;

  for(i = 1; i < 20; i++) {
    if(Bin[i] != 0) {
      meanx += Mass[i];
      meany += Bin[i];
      nbins ++;
    }
  }
  
  if(nbins != 0) {
    meanx = meanx / nbins;
    meany = meany / nbins;
  } else {
    Tcl_AppendResult(interp, "0", (char *) NULL);
    return TCL_OK;
  }

  sumxx = 0;
  sumxy = 0;
  
  for(i = 1; i < 20; i++) {
    if(Bin[i] != 0) {
      sumxx += (Mass[i] - meanx) * (Mass[i] - meanx);
      sumxy += (Mass[i] - meanx) * (Bin[i] - meany);
    }
  }
  
  pow = sumxy / sumxx;
  
  if(print == 0) {
    
    /* mass spectrum index to be printed */
    
    sprintf(out, "%e", pow);
    Tcl_AppendResult(interp, out, (char *) NULL);
  } else {
    
    /* mass spectrum data wanted for output */
    
    for(i = 0; i < 21; i++) {
      sprintf(outmass, "%e", Mass[i]);
      sprintf(outbin, "%e", Bin[i]);
      Tcl_AppendResult(interp, outmass, " ", outbin, "\n", (char *) NULL);
    }
  }
      
  return MPSA_OKAY;
}
