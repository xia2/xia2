/* cloud module initialisation file v1.0
 * maintained by g.winter
 * for loading into mpsa
 * 11th september 2000
 * 
 */

#include "cloud_export.h"

int Cloud_Init(
  Tcl_Interp *interp
)
{
  mpsa_Pip *CloudDefn;

  CloudDefn = (mpsa_Pip *) malloc (sizeof(mpsa_Pip));
  CloudDefn->Name = "cloud";
  CloudDefn->Constructor = cloud_Constructor;
  CloudDefn->Destructor = cloud_Destructor;
  CloudDefn->SetDataEntry = cloud_SetDataEntry;
  CloudDefn->GetIntDataEntry = cloud_GetIntDataEntry;
  CloudDefn->GetFloatDataEntry = cloud_GetFloatDataEntry;
  CloudDefn->Writer = cloud_Writer;
  CloudDefn->Reader = cloud_Reader;

  if(mpsa_RegisterNewPip(CloudDefn) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  Tcl_CreateCommand(interp, "cloud::cloud", cloud_CloudCmd,
    (ClientData) NULL, (void (*)()) NULL);

  return TCL_OK;
}  
  
