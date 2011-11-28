/* gsimII mpsa file commands file v1.0
 * maintained by g.winter
 * 23rd august 2000
 * 
 * 
 */

#include "mpsa_private.h"

/*[ mpsa_WriteSimulationCmd
 *[ action:  write a simulation but not associated particles
 *[          to a tcl channel - different to gsim
 *[ objects: takes a tcl channel and a simulation
 *[ syntax:  CommandName SimName ChannelName
 */

int mpsa_WriteSimulationCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_Simulation *Simulation;
  Tcl_Channel chan;
  int mode;

  if(argc != 3) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetSim(interp, argv[1], &Simulation) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  if((chan = Tcl_GetChannel(interp, argv[2], &mode)) == (Tcl_Channel) NULL) {
    Tcl_AppendResult(interp, "Error getting channel", (char *) NULL);
    return TCL_ERROR;
  }

  if((mode & TCL_WRITABLE) == 0) {
    Tcl_AppendResult(interp, "Channel is not writeable", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_WriteSimulation(Simulation, chan) != MPSA_OKAY) {
    Tcl_AppendResult(interp, "Error writing simulation", (char *) NULL);
    return TCL_ERROR;
  }

  return TCL_OK;
}

/*[ mpsa_WritePclListCmd
 *[ action:  write the data from a list of particles to a binary 
 *[          tcl channel
 *[ objects: takes a list and a tcl channel
 *[ syntax:  CommandName ListName ChannelName
 */

int mpsa_WritePclListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_List *List;
  mpsa_Link *Link;
  Tcl_Channel chan;
  int mode;

  if(argc != 3) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetList(interp, argv[1], &List) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  if((chan = Tcl_GetChannel(interp, argv[2], &mode)) == (Tcl_Channel) NULL) {
    Tcl_AppendResult(interp, "Error getting channel", (char *) NULL);
    return TCL_ERROR;
  }

  if((mode & TCL_WRITABLE) == 0) {
    Tcl_AppendResult(interp, "Channel is not writeable", (char *) NULL);
    return TCL_ERROR;
  }

  for(Link = List->firstLink; Link != NULL; Link = Link->nextLink) {
    if(mpsa_WritePcl(Link->Pcl, chan) != MPSA_OKAY) {
      Tcl_AppendResult(interp, "Error writing particle", (char *) NULL);
      return TCL_ERROR;
    }
  }

  return TCL_OK;
}

/*[ mpsa_SetPlatformCmd
 *[ action:  set platform type and byte ordering
 *[ objects: takes a platform name
 *[ syntax:  CommandName PlatformName
 */

int mpsa_SetPlatformCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  if(argc != 2) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_SetByteOrder(argv[1]) != MPSA_OKAY) {
    Tcl_AppendResult(interp, "Platform type ", argv[1], " not recognised",
      (char *) NULL);
    return TCL_ERROR;
  }

  return TCL_OK;
}

/*[ mpsa_CreateConversionTableCmd
 *[ action:  create blank conversion table
 *[ objects: just takes a number of elements to make in the table
 *[ syntax:  CommandName NumberOfSpaces
 */

int mpsa_CreateConversionTableCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  int NumberOfElements;

  if(argc != 2) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(Tcl_GetInt(interp, argv[1], &NumberOfElements) != TCL_OK) {
    Tcl_AppendResult(interp, "Error getting number of elements", 
      (char *) NULL);
    return TCL_ERROR;
  }

  mpsa_CreateConversionTable(NumberOfElements);
  return TCL_OK;
}

/*[ mpsa_DeleteConversionTableCmd
 *[ action:  delete the type conversion table
 *[ objects: none
 *[ syntax:  CommandName
 */

int mpsa_DeleteConversionTableCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_DeleteConversionTable();
  return TCL_OK;
}

/*[ mpsa_WriteConversionTableElementCmd
 *[ action:  takes an old id, and a name, looks up the new name and 
 *[          obtains a new id, writing this all into a table
 *[ objects: takes an old ID and a type name
 *[ syntax:  CommandName OldID typeName
 */

int mpsa_WriteConversionTableElementCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{

  int OldID;
  mpsa_ParticleDefn *type;

  if(argc != 3) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(Tcl_GetInt(interp, argv[1], &OldID) != TCL_OK) {
    Tcl_AppendResult(interp, "Error getting old particle ID", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetPclDefn(interp, argv[2], &type) != MPSA_OKAY) {
    Tcl_AppendResult(interp, "Error getting old particle type", (char *) NULL);
    return TCL_ERROR;
  }

  mpsa_WriteConversionTableElement(OldID, argv[2], type->DynamicID);

  return TCL_OK;
}

/*[ mpsa_ReadPclListCmd
 *[ action:  read in particle properties from a tcl channel and 
 *[          create particles in a given simulation
 *[ objects: takes a simulation structure and a tcl channel
 *[ syntax:  CommandName SimName ChannelName
 */

int mpsa_ReadPclListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_Simulation *Simulation;
  Tcl_Channel chan;
  int mode;

  if(argc != 3) {
    Tcl_AppendResult(interp, "Error - insufficient arguments", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetSim(interp, argv[1], &Simulation) != MPSA_OKAY) {
    return TCL_ERROR;
  }

  if((chan = Tcl_GetChannel(interp, argv[2], &mode)) == (Tcl_Channel) NULL) {
    Tcl_AppendResult(interp, "Error getting channel", (char *) NULL);
    return TCL_ERROR;
  }

  if((mode & TCL_READABLE) == 0) {
    Tcl_AppendResult(interp, "Channel is not readable", (char *) NULL);
    return TCL_ERROR;
  }

  while(Tcl_Eof(chan) == 0) {
    mpsa_ReadPcl(Simulation, chan);
  }

/*
 * the loader always makes one false particle, so here we go deleting it
 */

  Simulation->lastPcl = Simulation->lastPcl->prevPcl;
  mpsa_DeletePcl(Simulation->lastPcl->nextPcl);

  return TCL_OK;
}

/*[ mpsa_WritePipListCmd 
 *[ action:  write out the list of defined pips
 *[ objects: takes nothing, returns a tcl list
 *[ syntax:  PipNameWrite
 */

int mpsa_WritePipListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  Tcl_HashEntry *Entry;
  Tcl_HashSearch Search;
  mpsa_Pip *Pip;

  for(Entry = Tcl_FirstHashEntry(&mpsa_PiptypeHashTable, &Search); 
    Entry != NULL; Entry = Tcl_NextHashEntry(&Search)) {
    Pip = (mpsa_Pip *) Tcl_GetHashValue(Entry);
    Tcl_AppendElement(interp, Pip->Name);
  }

  return TCL_OK;
}

/*[ mpsa_WriteParticleIDListCmd
 *[ action:  write a list of particle ID's and names for the use of
 *[          writing a conversion table
 *[ objects: none
 *[ syntax:  ParticleNameWrite
 */

int mpsa_WriteParticleIDListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  Tcl_HashEntry *Entry;
  Tcl_HashSearch Search;
  mpsa_ParticleDefn *Type;
  char ID[3];

  /* some wrappers to allow this to be parsed as a proper list */

  for(Entry = Tcl_FirstHashEntry(&mpsa_ParticletypeHashTable, &Search);
    Entry != NULL; Entry = Tcl_NextHashEntry(&Search)) {
    Type = (mpsa_ParticleDefn *) Tcl_GetHashValue(Entry);
    sprintf(ID, "%d", Type->DynamicID);
    Tcl_AppendResult(interp, "{", ID, " ", Type->Name, "} ", (char *) NULL);
  }

  return TCL_OK;
}

/*[ mpsa_WriteParticleDefinitionCmd
 *[ action:  write out the particle definitions so that they are suited to 
 *[          being redefined at a later stage using load
 *[ objects: takes the name of a particle definition
 *[ syntax:  ParticleDefnWrite ParticleName
 */

int mpsa_WriteParticleDefinitionCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_ParticleDefn *Type;
  char NPips[3];
  int N, i;

  if(argc < 2) {
    Tcl_AppendResult(interp, "Error in command usage\n", 
      "must supply particle type name", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetPclDefn(interp, argv[1], &Type) != MPSA_OKAY) {
    Tcl_AppendResult(interp, "Error getting particle type", (char *) NULL);
    return TCL_ERROR;
  }

  N = Type->NPips;

  sprintf(NPips, "%d", N);
  
  Tcl_AppendElement(interp, Type->Name);
  Tcl_AppendElement(interp, NPips);

  for(i = 0; i < N; i++) {
    Tcl_AppendElement(interp, Type->Piptypes[i]->Name);
  }

  return TCL_OK;
}

/*[ mpsa_CheckParticleDefinedCmd
 *[ action:  check that a particle name is defined
 *[          used in loading a list of particles
 *[ objects: takes the name of the particle type
 *[ syntax:  ParticleDefnCheck Name
 */

int mpsa_CheckParticleDefinedCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
)
{
  mpsa_ParticleDefn *Type;
  if(argc < 2) {
    Tcl_AppendResult(interp, "Error - need a name to test", (char *) NULL);
    return TCL_ERROR;
  }

  if(mpsa_GetPclDefn(interp, argv[1], &Type) != MPSA_OKAY) {
    Tcl_AppendResult(interp, "no", (char *) NULL);
    return TCL_OK;
  } else {
    Tcl_AppendResult(interp, "yes", (char *) NULL);
    return TCL_OK;
  }
}
