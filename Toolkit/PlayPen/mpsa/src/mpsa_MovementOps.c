/* gsimII mpsa particle movement operations file v1.0
 * maintained by g.winter
 * 21st august 2000
 *
 *
 */

#include "mpsa_private.h"

/*[ mpsa_PclPosUpdate
 *[ action:  function to update the position of a particle by velocity
 *[          multiplied by global dt value set in mpsa_SetMovementTimeStep
 *[ objects: takes a pointer to a particle
 */

int mpsa_PclPosUpdate(
  mpsa_Particle *Pcl,
  float dt
)
{
  int i;

  for(i = 0; i < 3; i++) {
    Pcl->x[i] += Pcl->v[i] * dt;
  }

  return MPSA_OKAY;
}

/*[ mpsa_PclVelUpdate
 *[ action:  function to update the velocity of a particle by acceleration
 *[          multiplied by global dt value set in mpsa_SetMovementTimeStep
 *[ objects: takes a pointer to a particle
 */

int mpsa_PclVelUpdate(
  mpsa_Particle *Pcl,
  float dt
)
{
  int i;

  for(i = 0; i < 3; i++) {
    Pcl->v[i] += Pcl->a[i] * dt;
  }

  return MPSA_OKAY;
}

