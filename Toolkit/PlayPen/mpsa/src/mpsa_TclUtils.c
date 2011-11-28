/* mpsa_TclUtils v1.0
 * wrapper functions for tcl functionality
 * 
 * 
 * 
 */

#include "mpsa_export.h"

int mpsa_GetInt(
  Tcl_Interp *interp,
  char *name,
  int *value
)
{
  if(Tcl_GetInt(interp, name, value) != TCL_OK) {
    Tcl_AppendResult(interp, "Error getting integer value from ", name,
      (char *) NULL);
    return MPSA_FAIL;
  } else {
    return MPSA_OKAY;
  }
}

int mpsa_GetFloat(
  Tcl_Interp *interp,
  char *name,
  float *value
)
{
  double DoubleValue;
  if(Tcl_GetDouble(interp, name, &DoubleValue) != TCL_OK) {
    Tcl_AppendResult(interp, "Error getting floating value from ", name,
      (char *) NULL);
    return MPSA_FAIL;
  } else {
    *value = DoubleValue;
    return MPSA_OKAY;
  }
}

int mpsa_GetDouble(
  Tcl_Interp *interp,
  char *name,
  double *value
)
{
  if(Tcl_GetDouble(interp, name, value) != TCL_OK) {
    Tcl_AppendResult(interp, "Error getting double value from ", name,
      (char *) NULL);
    return MPSA_FAIL;
  } else {
    return MPSA_OKAY;
  }
}

int mpsa_CopyName(
  char *OldName,
  char **NewName
)
{
  int length;

  length = strlen(OldName);
  *NewName = (char *) malloc (length * sizeof(char));
  *NewName = strcpy(*NewName, OldName);
  return MPSA_OKAY;
}

