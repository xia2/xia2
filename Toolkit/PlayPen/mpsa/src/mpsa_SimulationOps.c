/* gsimII mpsa simulation operations file v1.0
 * maintained by g.winter
 * 15th august 2000
 * 
 * 
 */

#include "mpsa_export.h"
#include "mpsa_private.h"

/*[ mpsa_SimZero
 *[ action:  to set all of the elements of a newly created simulation 
 *[          to default values after creation
 *[ objects: takes a simulation structure
 */

int mpsa_SimZero(
  mpsa_Simulation *Sim
)
{
  if(Sim == NULL) {
    return MPSA_FAIL;
  }

  Sim->firstPcl = NULL;
  Sim->lastPcl = NULL;
  Sim->Lists = NULL;
  Sim->NPcls = 0;
  Sim->NGalaxies = 0;
  Sim->NIterations = 0;
  Sim->NLists = 0;
  Sim->dt = 1;
  Sim->age = 0;
  Sim->ScaleLength = 1;
  Sim->ScaleTime = 1;
  Sim->ScaleMass = 1;

  return MPSA_OKAY;
}
