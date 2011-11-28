/* gsimII mpsa particle extraction routines file v1.0
 * maintained by g.winter
 * 18th august 2000
 *  
 *
 */

#include "mpsa_private.h"

int PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_X;

/*[ mpsa_PclSetEntry
 *[ action:  set the entry which the list append command will compare
 *[          with the given value
 *[ objects: takes a name, returns MPSA_FAIL if this is not recognised
 */

int mpsa_PclSetEntry(
  char *Name
)
{
  if((strcmp(Name, "x") == 0) || (strcmp(Name, "X") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_X;
  } else if((strcmp(Name, "y") == 0) || (strcmp(Name, "Y") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_Y;
  } else if((strcmp(Name, "z") == 0) || (strcmp(Name, "Z") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_Z;
  } else if((strcmp(Name, "vx") == 0) || (strcmp(Name, "VX") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_VX;
  } else if((strcmp(Name, "vy") == 0) || (strcmp(Name, "VY") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_VY;
  } else if((strcmp(Name, "vz") == 0) || (strcmp(Name, "VZ") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_VZ;
  } else if((strcmp(Name, "ax") == 0) || (strcmp(Name, "AX") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_AX;
  } else if((strcmp(Name, "ay") == 0) || (strcmp(Name, "AY") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_AY;
  } else if((strcmp(Name, "az") == 0) || (strcmp(Name, "AZ") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_AZ;
  } else if ((strcmp(Name, "Mass") == 0) || (strcmp(Name, "mass") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_MASS;
  } else if ((strcmp(Name, "Age") == 0) || (strcmp(Name, "age") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_AGE;
  } else if ((strcmp(Name, "Type") == 0) || (strcmp(Name, "type") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_TYPE;
  } else if ((strcmp(Name, "Flag") == 0) || (strcmp(Name, "flag") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_FLAG;  
  } else if ((strcmp(Name, "Extract") == 0) || (strcmp(Name, "extract") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_EXTRACT;
  } else if ((strcmp(Name, "Origin") == 0) || (strcmp(Name, "origin") == 0)) {
    PARTICLE_ENTRY_VALUE = PARTICLE_ENTRY_ORIGIN;
  } else {
    return MPSA_FAIL;
  }

  return MPSA_OKAY;
}

/*[ mpsa_GetFloatEntry
 *[ action:  get entry of particle structure which was set above to compare
 *[          for list append command
 *[ objects: takes a particle, returns a floating value
 */

float mpsa_GetFloatEntry(
  mpsa_Particle *Pcl
)
{
  float Value;
  switch(PARTICLE_ENTRY_VALUE){
  case(PARTICLE_ENTRY_X):
    Value = Pcl->x[0];
    break;
  case(PARTICLE_ENTRY_Y):
    Value = Pcl->x[1];
    break;
  case(PARTICLE_ENTRY_Z):
    Value = Pcl->x[2];
    break;
  case(PARTICLE_ENTRY_VX):
    Value = Pcl->v[0];
    break;
  case(PARTICLE_ENTRY_VY):
    Value = Pcl->v[1];
    break;
  case(PARTICLE_ENTRY_VZ):
    Value = Pcl->v[2];
    break;
  case(PARTICLE_ENTRY_AX):
    Value = Pcl->a[0];
    break;
  case(PARTICLE_ENTRY_AY):
    Value = Pcl->a[1];
    break;
  case(PARTICLE_ENTRY_AZ):
    Value = Pcl->a[2];
    break;
  case(PARTICLE_ENTRY_MASS):
    Value = Pcl->mass;
    break;
  case(PARTICLE_ENTRY_AGE):
    Value = Pcl->age;
    break;
  default:
    Value = -100;
  }
  
  return Value;
}

/*[ mpsa_GetIntEntry
 *[ action:  get entry of particle structure which was set above to compare
 *[          for list append command
 *[ objects: takes a particle, returns a integer value
 */

int mpsa_GetIntEntry(
  mpsa_Particle *Pcl
)
{
  int Value;
  switch(PARTICLE_ENTRY_VALUE) {
  case(PARTICLE_ENTRY_TYPE):
    Value = Pcl->type;
    break;
  case(PARTICLE_ENTRY_FLAG):
    Value = Pcl->flag;
    break;
  case(PARTICLE_ENTRY_ORIGIN):
    Value = Pcl->origin;
    break;
  case(PARTICLE_ENTRY_EXTRACT):
    Value = Pcl->extract;
    break;
  default:
    Value = -100;
    break;
  }

  return Value;
}
