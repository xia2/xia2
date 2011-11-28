/* gsimII mpsa commands file v1.0
 * maintained by g.winter
 * 15th august 2000
 * 
 * basic book-keeping stuff
 * 
 */

#ifndef _MPSA_PRIV
#define _MPSA_PRIV

#include "mpsa_export.h"

#define BIG_END 0
#define LITTLE_END 1

#define PARTICLE_ENTRY_X 1
#define PARTICLE_ENTRY_Y 2
#define PARTICLE_ENTRY_Z 3
#define PARTICLE_ENTRY_VX 11
#define PARTICLE_ENTRY_VY 12
#define PARTICLE_ENTRY_VZ 13
#define PARTICLE_ENTRY_AX 21
#define PARTICLE_ENTRY_AY 22
#define PARTICLE_ENTRY_AZ 23
#define PARTICLE_ENTRY_MASS 30
#define PARTICLE_ENTRY_FLAG 31
#define PARTICLE_ENTRY_AGE 32
#define PARTICLE_ENTRY_TYPE 40
#define PARTICLE_ENTRY_EXTRACT 41
#define PARTICLE_ENTRY_ORIGIN 42

extern Tcl_HashTable mpsa_SimHashTable;
extern Tcl_HashTable mpsa_ListHashTable;
extern Tcl_HashTable mpsa_PairListHashTable;
extern Tcl_HashTable mpsa_ParticletypeHashTable;
extern Tcl_HashTable mpsa_PiptypeHashTable;

typedef struct mpsa_typeConversionTableElement{
  char *typeName;
  int NewID;
} mpsa_typeConversionTableElement;

/*[ mpsa_CreateListCmd
 *[ action:  create a new list structure, register with hash table and
 *[          simulation structure
 *[ objects: takes name of a simulation and name of new list structure
 */

extern int mpsa_CreateListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_DeleteListCmd
 *[ action:  fetch and delete list structure from hash table, delete hash
 *[          table entry and pointer to list within simulation structure
 *[ objects: takes name of list structure to be deleted
 */

extern int mpsa_DeleteListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_CreateSimulationCmd
 *[ action:  creates simulation structure and creates a hash entry 
 *[          to access it.
 *[ objects: name of new simulation structure
 */

extern int mpsa_CreateSimulationCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_DeleteSimulationCmd
 *[ action:  fetch and delete simulation structure, as well as all lists and
 *[          particles associated with it, deleteing hash entry
 *[ objects: simulation name
 */

extern int mpsa_DeleteSimulationCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_RegisterNewPcltypeCmd
 *[ action:  create a new particle definition according to users specification
 *[          using predefined pip types
 *[ objects: type name, number of pips and list of pip names
 */

extern int mpsa_RegisterNewPcltypeCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_CheckPipDefinedCmd
 *[ action:  determine whether a certain pip has been defined
 *[ objects: name of a pip, returns TCL_OK or TCL_ERROR
 */

extern int mpsa_CheckPipDefinedCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_WritePipListCmd 
 *[ action:  write out the list of defined pips
 *[ objects: takes nothing, returns a tcl list
 *[ syntax:  PipNameWrite
 */

extern int mpsa_WritePipListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_WriteParticleDefinitionCmd
 *[ action:  write out the particle definitions so that they are suited to 
 *[          being redefined at a later stage using load
 *[ objects: takes the name of a particle definition
 *[ syntax:  ParticleDefinitionWrite ParticleName
 */

extern int mpsa_WriteParticleDefinitionCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_WriteParticleIDListCmd
 *[ action:  write a list of particle ID's and names for the use of
 *[          writing a conversion table
 *[ objects: none
 *[ syntax:  ParticleNameWrite
 */

extern int mpsa_WriteParticleIDListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_WriteSimulationCmd
 *[ action:  write a simulation but not associated particles
 *[          to a tcl channel - different to gsim
 *[ objects: takes a tcl channel and a simulation
 */

/*[ mpsa_CheckParticleDefinedCmd
 *[ action:  check that a particle name is defined
 *[          used in loading a list of particles
 *[ objects: takes the name of the particle type
 *[ syntax:  ParticleDefnCheck Name
 */

extern int mpsa_CheckParticleDefinedCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

extern int mpsa_WriteSimulationCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_WritePclListCmd
 *[ action:  write the data from a list of particles to a binary 
 *[          tcl channel
 *[ objects: takes a list and a tcl channel
 */

extern int mpsa_WritePclListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_SetPlatformCmd
 *[ action:  set platform type and byte ordering
 *[ objects: takes a platform name
 */

extern int mpsa_SetPlatformCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_CreateConversionTableCmd
 *[ action:  create blank conversion table
 *[ objects: just takes a number of elements to make in the table
 */

extern int mpsa_CreateConversionTableCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_DeleteConversionTableCmd
 *[ action:  delete the type conversion table
 *[ objects: none
 */

extern int mpsa_DeleteConversionTableCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_WriteConversionTableElementCmd
 *[ action:  takes an old id, and a name, looks up the new name and 
 *[          obtains a new id, writing this all into a table
 *[ objects: takes an old ID and a type name
 */

extern int mpsa_WriteConversionTableElementCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_ReadPclListCmd
 *[ action:  read in particle properties from a tcl channel and 
 *[          create particles in a given simulation
 *[ objects: takes a simulation structure and a tcl channel
 */

extern int mpsa_ReadPclListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_WriteSimulation
 *[ action:  write a simulation structure to a binary tcl channel
 *[          swapping bytes as necessary
 *[ objects: takes a simulation and a tcl channel
 */

extern int mpsa_WriteSimulation(
  mpsa_Simulation *Simulation,
  Tcl_Channel chan
);

/*[ mpsa_WritePcl
 *[ action:  write all of the data from a particle structure, including
 *[          pip information, to a tcl channel
 *[ objects: 
 */

extern int mpsa_WritePcl(
  mpsa_Particle *Pcl,
  Tcl_Channel chan
);

/*[ mpsa_WriteFloat/Integer
 *[ action:  write value to tcl channel, making appropriate byte swapping
 *[          action
 *[ objects: takes a value and a tcl channel
 */

extern int mpsa_WriteFloat(
  float Value,
  Tcl_Channel chan
);

extern int mpsa_WriteInteger(
  int Value,
  Tcl_Channel chan
);

/*[ mpsa_SetByteOrder
 *[ action:  sets the correct byte ordering for machine type
 *[ objects: name
 */

extern int mpsa_SetByteOrder(
  char *Platform
);

/*[ mpsa_CreateConversionTable
 *[ action:  creates a type conversion table of predefined size
 *[ objects: takes a number of elements to make space for
 */

extern int mpsa_CreateConversionTable(
  int NumberOfElements
);

/*[ mpsa_DeleteConversionTable
 *[ action:  delete the conversion table including all names;
 *[ objects: none
 */

extern int mpsa_DeleteConversionTable();

/*[ mpsa_WriteConversionTableElement
 *[ action:  writes an element of the conversion table from the old id,
 *[          the name and the new id
 *[ objects: takes the old id, the name and the new id of a particle type
 */

extern int mpsa_WriteConversionTableElement(
  int OldID,
  char *Name,
  int NewID
);

/*[ mpsa_GetNewTabulatedID
 *[ action:  gets new dynamic ID from old dynamic ID
 *[ objects: takes an integer ID and returns another
 */

extern int mpsa_GetNewTabulatedID(
  int OldID
);

/*[ mpsa_ReadFloat/Integer
 *[ action:  read value from a tcl channel, performing appropriate byte
 *[          swapping actions
 *[ objects: a tcl channel from which to read and returns *Value
 */

extern int mpsa_ReadFloat(
  float *Value,
  Tcl_Channel chan
);

extern int mpsa_ReadInteger(
  int *Value,
  Tcl_Channel chan
);

/*[ mpsa_ReadPcl
 *[ action:  create a new blank particle in a simulation and set 
 *[          all of it's values to those stored in the data file, including pip
 *[          data
 *[ objects: takes a simulation and a tcl channel
 */

extern int mpsa_ReadPcl(
  mpsa_Simulation *Simulation,
  Tcl_Channel chan
);

/*[ mpsa_ListClearCmd
 *[ action:  empty a list structure of pointers to particles
 *[ objects: name of list structure
 */

extern int mpsa_ListClearCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_AppendToListCmd
 *[ action:  append particles from simulation structure to a list structure
 *[          according to basic (ie type) criteria
 *[ objects: takes list structure name and particle definition name
 */

extern int mpsa_AppendToListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_DeletePclCmd
 *[ action:  delete all particles extracted into a list from simulation 
 *[          structure and clear the list
 *[ objects: name of list of extracted particles
 */

extern int mpsa_DeletePclCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_FlexibleAppendToListCmd
 *[ action:  append particles from simulation structure to list according to
 *[          a flexible set of criteria defined by user, or criteria included
 *[          within mpsa base
 *[ objects: name of list, name of group (ie pip type or particle), criterion
 *[          within group, operator (described elsewhere) and a value
 */

extern int mpsa_FlexibleAppendToListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_AddListToSimulation
 *[ action:  add a newly defined list structure to a simulation structure
 *[ objects: takes a pointer to a simulation and a pointer to the list
 */

extern int mpsa_AddListToSimulation(
  mpsa_Simulation *Simulation,
  mpsa_List *List
);

/*[ mpsa_RemoveListFromSimulation
 *[ action:  remove list pointer from list within simulation structure
 *[          in the process of deleteing the list
 *[ objects: takes a pointer to a simulation and a pointer to the list
 */

extern int mpsa_RemoveListFromSimulation(
  mpsa_Simulation *Simulation,
  mpsa_List *List
);

/*[ mpsa_IsListInSim
 *[ action:  tests to see if a given list pointer is associated with a
 *[          simulation, returning either MPSA_OKAY = yes or MPSA_FAIL = no
 *[ objects: takes a pointer to a simulation and a pointer to the list
 */

extern int mpsa_IsListInSim(
  mpsa_Simulation *Simulation,
  mpsa_List *List
);

/*[ mpsa_ListClear
 *[ action:  clear all pointer entries in list structure
 *[ objects: takes pointer to list structure
 */

extern int mpsa_ListClear(
  mpsa_List *List
);

/*[ mpsa_ListCreate
 *[ action:  create a list of given name and attatch it to a simulation
 *[ objects: simulation pointer, name and pointer to list pointer
 */

extern int mpsa_ListCreate(
  mpsa_Simulation *Simulation,
  char *ListName,
  mpsa_List **NewList
);

/*[ mpsa_extractSimToList
 *[ action:  extract all particles of a given type from a simulation 
 *[          to a list, counting them as it goes        
 *[ objects: takes pointer to a simulation and pointer to a list, a type 
 *[          described by an integer and returns the number of extractions
 */

extern int mpsa_extractSimToList(
  mpsa_Simulation *Simulation,
  mpsa_List *List,
  int *InList,
  int type
);

/*[ mpsa_extractAllToList
 *[ action:  extract all particles associated with a simulation structure
 *[          to a list
 *[ objects: takes a pointer to a simulation and a pointer to a list, returning
 *[          number of extractions
 */

extern int mpsa_extractAllToList(
  mpsa_Simulation *Simulation,
  mpsa_List *List,
  int *InList
);

/*[ mpsa_AppendToList
 *[ action:  add a particle pointer to a list structure
 *[ objects: a pointer to a list, and a pointer to the particle to be added
 */

extern int mpsa_AppendToList(
  mpsa_List *List,
  mpsa_Particle *Pcl
);

/*[ mpsa_PclPosUpdateCmd
 *[ action:  move all of the particles in a list by their velocity
 *[          multiplied by dt
 *[ objects: takes a name of a list and dt (a floating point value)
 */

extern int mpsa_PclPosUpdateCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_PclVelUpdateCmd
 *[ action:  updates the velolity of all of the particles in the list
 *[          by their acceleration multiplied by dt
 *[ objects: takes a name of a list and dt (a floating point value)
 */

extern int mpsa_PclVelUpdateCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ int mpsa_ParticleCmd
 *[ action:  all bets
 *[ objects: are
 *[ syntax:  off
 */

extern int mpsa_ParticleCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_ListCmd
 *[ action:  anything to do with lists
 *[ objects: lists, simulations, types and particles
 *[ syntax:  too big to explain here
 */

extern int mpsa_ListCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_SimCmd
 *[ action:  creates/destroys simulation structure and hash entry to access it.
 *[ objects: name of simulation structure
 *[ syntax:  CommandName option SimName
 */

extern int mpsa_SimCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_PclPosUpdate
 *[ action:  function to update the position of a particle by velocity
 *[          multiplied by global dt value set in mpsa_SetMovementTimeStep
 *[ objects: takes a pointer to a particle
 */

extern int mpsa_PclPosUpdate(
  mpsa_Particle *Pcl,
  float dt
);

/*[ mpsa_PclVelUpdate
 *[ action:  function to update the velocity of a particle by acceleration
 *[          multiplied by global dt value set in mpsa_SetMovementTimeStep
 *[ objects: takes a pointer to a particle
 */

extern int mpsa_PclVelUpdate(
  mpsa_Particle *Pcl,
  float dt
);

/*[ mpsa_SetOperator
 *[ action:  set appropriate operator for use with list append command
 *[          uses global variables for sake of efficiency
 *[ objects: takes name of operator, eg >=
 */

extern int mpsa_SetOperator(
  char *OperatorName
);

/*[ mpsa_BinaryOperators
 *[ action:  act as wrapper functions to binary operators to enable faster
 *[          action in list appending command, as pointers to functions can
 *[          be set, as set above and used below
 *[ objects: all take two variables and return MPSA_OKAY = true, MPSA_FAIL =
 *[          false
 */

extern int mpsa_IntGreater(
  int a,
  int b
);

extern int mpsa_FloatGreater(
  float a,
  float b
);

extern int mpsa_IntLess(
  int a,
  int b
);

extern int mpsa_FloatLess(
  float a,
  float b
);

extern int mpsa_IntEqual(
  int a,
  int b
);

extern int mpsa_FloatEqual(
  float a,
  float b
);

extern int mpsa_IntNotEqual(
  int a,
  int b
);

extern int mpsa_FloatNotEqual(
  float a,
  float b
);

extern int mpsa_IntGreaterEqual(
  int a,
  int b
);

extern int mpsa_FloatGreaterEqual(
  float a,
  float b
);

extern int mpsa_IntLessEqual(
  int a,
  int b
);

extern int mpsa_FloatLessEqual(
  float a,
  float b
);

/*[ mpsa_Int/Float Operator
 *[ action:  generic operator as set above, returns value of operator acting
 *[          on two variables
 *[ objects: takes two variables, returns MPSA_OKAY = true, MPSA_FAIL = false
 */

extern int mpsa_IntOperator(
  int a,
  int b
);

extern int mpsa_FloatOperator(
  float a,
  float b
);

/*[ mpsa_CreatePclCmd
 *[ action:  create a number of particles as described at command line, 
 *[          associating them with a given simulation
 *[ objects: takes a simulation name, a particle type name and an integer
 *[          describing the number to be created
 */

extern int mpsa_CreatePclCmd(
  ClientData dummy,
  Tcl_Interp *interp,
  int argc,
  char **argv
);

/*[ mpsa_PclSetEntry
 *[ action:  set the entry which the list append command will compare
 *[          with the given value
 *[ objects: takes a name, returns MPSA_FAIL if this is not recognised
 */

extern int mpsa_PclSetEntry(
  char *Name
);

/*[ mpsa_GetFloatEntry
 *[ action:  get entry of particle structure which was set above to compare
 *[          for list append command
 *[ objects: takes a particle, returns a floating value
 */

extern float mpsa_GetFloatEntry(
  mpsa_Particle *Pcl
);

/*[ mpsa_GetIntEntry
 *[ action:  get entry of particle structure which was set above to compare
 *[          for list append command
 *[ objects: takes a particle, returns a integer value
 */

extern int mpsa_GetIntEntry(
  mpsa_Particle *Pcl
);

/*[ mpsa_SimZero
 *[ action:  to set all of the elements of a newly created simulation 
 *[          to default values after creation
 *[ objects: takes a simulation structure
 */

extern int mpsa_SimZero(
  mpsa_Simulation *Sim
);

/*[ mpsa_ListHashEntryCreate
 *[ action:  create a hash entry in the list hash table
 *[ objects: takes the name of a list and a pointer to that list
 */ 

extern int mpsa_ListHashEntryCreate(
  char *Name,
  mpsa_List *List
);

/*[ mpsa_ListDelete
 *[ action:  deletes all trace of a list
 *[ objects: takes a pointer to a simulation
 */

extern int mpsa_ListDelete(
  mpsa_List *List
);

/*[ mpsa_MassSpectrum
 *[ action:  calculate mass spectrum information from a list of particles
 *[ objects: takes a tcl interpreter, a list and a flag
 */

extern int mpsa_MassSpectrum(
  Tcl_Interp *interp,
  mpsa_List *List,
  int printflag
);

#endif
