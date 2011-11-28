/* gsimII kernel initialisation file v1.0
 * maintained by g.winter
 * 15th july 2000
 * 
 * initialise mpsa commands and hash tables
 * 
 */

#include "mpsa_export.h"
#include "mpsa_private.h"

/*
 * hash tables - last enables dynamicly defined particle types
 */

Tcl_HashTable mpsa_SimHashTable;
Tcl_HashTable mpsa_ListHashTable;
Tcl_HashTable mpsa_PairListHashTable;
Tcl_HashTable mpsa_ParticletypeHashTable;
Tcl_HashTable mpsa_PiptypeHashTable;

int mpsa_Init(
  Tcl_Interp *interp
)
{
  ClientData dummy;
  int argc = 0;
  char **argv = NULL;
  char *InitScript;

  Tcl_InitHashTable(&mpsa_SimHashTable, TCL_STRING_KEYS);
  Tcl_InitHashTable(&mpsa_ListHashTable, TCL_STRING_KEYS);  
  Tcl_InitHashTable(&mpsa_PairListHashTable, TCL_STRING_KEYS);
  Tcl_InitHashTable(&mpsa_ParticletypeHashTable, TCL_STRING_KEYS);
  Tcl_InitHashTable(&mpsa_PiptypeHashTable, TCL_STRING_KEYS);

  /*
   * register external 'mpsa' commands. necessary since these are in a 
   * 'loadable module' format.
   */

  Tcl_SetVar2(interp, "Mpsa", "etc", MPSA_ETC_DIR, TCL_GLOBAL_ONLY);
  InitScript = "catch {source $Mpsa(etc)/Init.tcl}";
  Tcl_Eval(interp, InitScript);

  mpsa_InitCmd(dummy, interp, argc, argv);
  Tree_Init(interp);
  Cloud_Init(interp);
  Sf_Init(interp);
  Sn_Init(interp);
  
  return TCL_OK;
}

int mpsa_InitCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  Tcl_CreateCommand(interp, "::mpsa::ListCreate", mpsa_CreateListCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ListDelete", mpsa_DeleteListCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::SimCreate", mpsa_CreateSimulationCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::SimDelete", mpsa_DeleteSimulationCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ParticleCreate", mpsa_CreatePclCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ParticleRegister", mpsa_RegisterNewPcltypeCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ParticleDelete", mpsa_DeletePclCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ListAppendBasic", mpsa_AppendToListCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ListClear", mpsa_ListClearCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ListAppend", mpsa_FlexibleAppendToListCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ParticlePositionUpdate", mpsa_PclPosUpdateCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ParticleVelocityUpdate", mpsa_PclVelUpdateCmd,
    (ClientData) NULL, (void (*)()) NULL);

  /* non user commands -> `old-style' */

  Tcl_CreateCommand(interp, "::mpsa::ListWrite", mpsa_WritePclListCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ParticleRead", mpsa_ReadPclListCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::SimulationWrite", mpsa_WriteSimulationCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::PipCheck", mpsa_CheckPipDefinedCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::SetPlatform", mpsa_SetPlatformCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::IDConversionCreate", mpsa_CreateConversionTableCmd,
   (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::IDConversionDelete", mpsa_DeleteConversionTableCmd,
   (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::IDConversionWrite",
    mpsa_WriteConversionTableElementCmd, (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::PipNameWrite", mpsa_WritePipListCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ParticleNameWrite", mpsa_WriteParticleIDListCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ParticleDefnWrite", mpsa_WriteParticleDefinitionCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::ParticleDefnCheck", mpsa_CheckParticleDefinedCmd,
    (ClientData) NULL, (void (*)()) NULL);

  /* `new-style' user commands */

  Tcl_CreateCommand(interp, "::mpsa::pcl", mpsa_ParticleCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::lst", mpsa_ListCmd,
    (ClientData) NULL, (void (*)()) NULL);
  Tcl_CreateCommand(interp, "::mpsa::sim", mpsa_SimCmd,
    (ClientData) NULL, (void (*)()) NULL);

  return TCL_OK;
}
