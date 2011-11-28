/* sn - supernova initialisation file v1.0
 * for loading into mpsa
 * maintained by g.winter
 * 6th october 2000
 * 
 */

#include "tcl.h"
#include "sn_export.h"

int Sn_Init(
  Tcl_Interp *interp
)
{
  mpsa_Pip *SNDefn;

  SNDefn = (mpsa_Pip *) malloc (sizeof(mpsa_Pip));
  SNDefn->Name = "sn";
  SNDefn->Constructor = sn_Constructor;
  SNDefn->Destructor = sn_Destructor;
  SNDefn->Reader = sn_Reader;
  SNDefn->Writer = sn_Writer;
  SNDefn->SetDataEntry = sn_SetDataEntry;
  SNDefn->GetIntDataEntry = sn_GetIntDataEntry;
  SNDefn->GetFloatDataEntry = sn_GetFloatDataEntry;

  if(mpsa_RegisterNewPip(SNDefn) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  Tcl_CreateCommand(interp, "sn::sn", sn_SNovaCmd,
    (ClientData) NULL, (void (*)()) NULL);

  return TCL_OK;
}
