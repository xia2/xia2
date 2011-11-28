/* star formation init file v1.0
 * maintained by g.winter
 * for loading into mpsa
 * 21st september 2000
 */

#include "sf_export.h"

int Sf_Init(
  Tcl_Interp *interp
)
{
  Tcl_CreateCommand(interp, "sf::sf", sf_SFCmd,
    (ClientData) NULL, (void (*)()) NULL);

  return TCL_OK;
}
