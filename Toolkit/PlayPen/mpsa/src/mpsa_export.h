/* gsimII kernel header file v1.0
 * maintained by g.winter
 * 15th august 2000
 * 
 * 
 */

#ifndef _MPSA
#define _MPSA

#define MPSA_OKAY 0
#define MPSA_FAIL 1

#include "tcl.h"
#include <string.h>
#include <stdlib.h>

typedef struct mpsa_Particle{      /* basic particle definition        */
  float x[3];                      /* position                         */
  float v[3];                      /* velocity                         */
  float a[3];                      /* acceleration                     */
  float mass;                      /* mass                             */
  float phi;                       /* gravitational potential          */
  float age;                       /* age of particle                  */
  int type;                        /* dynamically assigned type ID     */
  int origin;                      /* particle source                  */
  int index;                       /* describes particles position in sim */
  int extract;                     /* flags to determine whether       */
  int flag;                        /* operations should be performed   */ 
  struct mpsa_Particle *nextPcl;      /* next particle in sim     */
  struct mpsa_Particle *prevPcl;  /* previous particle in sim */
  void *Pip;                       /* current 'pip'                    */
  void **PipList;                  /* list of all 'pips'               */
} mpsa_Particle;

typedef struct mpsa_Simulation{        /* basic simulation definition  */
  struct mpsa_Particle *firstPcl; /* first particle in simulation */
  struct mpsa_Particle *lastPcl;  /* last particle in simulation  */
  struct mpsa_List **Lists;            /* list of lists associated with sim */
  int NPcls;                      /* number of particles in sim   */
  int NGalaxies;                       /* number of 'galaxies' in sim  */
  int NIterations;                     /* number of iterations passed  */
  int NLists;                          /* number of lists associated   */
  float dt;                            /* current size of global timestep */
  float age;                           /* current age of simulation    */
  float ScaleLength;                   /* scaling parameters to enable */
  float ScaleTime;                     /* output to be in SI units or  */
  float ScaleMass;                     /* equivelent                   */
} mpsa_Simulation;

typedef struct mpsa_List{              /* basic list definition        */
  struct mpsa_Simulation *Simulation;  /* pointer to home simulation   */
  struct mpsa_Link *firstLink;         /* first link in list           */
  struct mpsa_Link *lastLink;          /* last link in list            */
  int NElements;                       /* number of elements of list   */
  char *ListName;                      /* hash table name of list      */
} mpsa_List;

typedef struct mpsa_Link{              /* basic link definition        */
  struct mpsa_Particle *Pcl;      /* pointer to the particle      */
  struct mpsa_Link *nextLink;          /* pointer to next link in list */
} mpsa_Link;

typedef struct mpsa_PairLink{          /* basic pair link definition   */
  struct mpsa_Particle *Pcl_1;   /* pointer to the first particle  */
  struct mpsa_Particle *Pcl_2;   /* pointer to the second particle */
  struct mpsa_PairLink *nextLink;      /* pointer to next link in list */
} mpsa_PairLink;

typedef struct mpsa_Pip{               /* basic 'pip' structure definition */
  char *Name;                          /* hash table name                  */
  int DynamicID;                       /* dynamically assigned identifier  */
  int (*Constructor)(void **);         /* function to create a pip         */
  int (*Destructor)(void **);          /* function to destroy a pip        */
  int (*SetDataEntry)(char *);         /* function to set data entry to be */
  int (*GetIntDataEntry)(void *);      /* read in sorting, and to get either */
  float (*GetFloatDataEntry)(void *);  /* an integer or floating value     */
  int (*Writer)(Tcl_Channel, void *);  /* function to write data to a tcl channel */
  int (*Reader)(Tcl_Channel, void *);  /* function to read data from a tcl channel */
} mpsa_Pip;

typedef struct mpsa_ParticleDefn{ /* particle definition structure   */
  char *Name;                           /* hash table name                 */
  int DynamicID;                        /* dynamically assigned identifier */
  int NPips;                            /* number of pips this type has    */
  mpsa_Pip **Piptypes;                  /* and a list of their definitions */
} mpsa_ParticleDefn;

/*[ mpsa_GetPclDefn
 *[ action:  get a particle definition structure from the appropriate hash
 *[          table, returning it as *Pcl
 *[ objects: takes a tcl interpreter, the name (hash table key), returns
 *[          a pointer to a definition structure
 */

extern int mpsa_GetPclDefn(
  Tcl_Interp *interp,
  char *typeName,
  mpsa_ParticleDefn **Pcl
);

/*[ mpsa_GetPclDefnFromID
 *[ action:  get a particle definition structure from the appropriate hash
 *[          table, searching through the hash table
 *[ objects: takes a dynamic particle ID, returns a pointer to a definition 
 *[          structure
 */

extern int mpsa_GetPclDefnFromID(
  int ID,
  mpsa_ParticleDefn **type
);

/*[ mpsa_GetPipDefn
 *[ action:  get a pip definition structure from the appropriate hash table,
 *[          indexed by Label
 *[ objects: takes a tcl interpreter and a name, returns a pointer to a 
 *[          pip definition structure
 */

extern int mpsa_GetPipDefn(
  Tcl_Interp *interp,
  char *Label,
  mpsa_Pip **Pip
);

/*[ mpsa_GetMaxPclID
 *[ mpsa_IncrementMaxPclID
 *[ mpsa_GetMaxPipID
 *[ mpsa_IncrementMaxPipID
 *[ action:  set of wrapper functions to administer the allocation of 
 *[          dynamic type identifiers
 *[ objects: none
 */

extern int mpsa_GetMaxPclID();

extern int mpsa_IncrementMaxPclID();

extern int mpsa_GetMaxPipID();

extern int mpsa_IncrementMaxPipID();

/*[ mpsa_GetPclsWithPip
 *[ action:  get a list of particle definitions which include the 
 *[          given pip definition
 *[ objects: takes a pip definition, and returns an array of pointers to 
 *[          particle definitions and the number of elements of the array
 */

extern int mpsa_GetPclsWithPip(
  mpsa_Pip *Piptype,
  mpsa_ParticleDefn **typeList,
  int *NumberInList
);

/*[ mpsa_DoesPclHavePip
 *[ action:  test to see if a particle definition contains a given pip 
 *[          definition
 *[ objects: takes a pip definition and particle definition, returns yes/no
 */

extern int mpsa_DoesPclHavePip(
  mpsa_Pip *Piptype,
  mpsa_ParticleDefn *Pcltype
);

/*[ mpsa_AddPcltypeToList
 *[ action:  add a particle definition to a list of particle definitions,
 *[          used in mpsa_GetPclsWithPip
 *[ objects: takes new particle definition and old list, and number of elements
 *[          returns new list
 */

extern int mpsa_AddPcltypeToList(
  mpsa_ParticleDefn *NewEntry,
  mpsa_ParticleDefn **List,
  int NumberInList
);

/*[ mpsa_GetPipPosition
 *[ action:  takes a particle definition and a pip definition, and returns
 *[          the position of the pip within the particle if applicable
 *[ objects: takes particle definition and pip definition, returns *position
 *[          if returns MPSA_FAIL, particle does not have required pip
 */

extern int mpsa_GetPipPosition(
  mpsa_ParticleDefn *Pcltype,
  mpsa_Pip *Piptype,
  int *Position
);

/*[ mpsa_RegisterNewPip
 *[ action:  register a new pip definition structure with the hash table
 *[          this is an external "interface" function
 *[ objects: takes a pointer to a new pip definition structure
 */

extern int mpsa_RegisterNewPip(
  mpsa_Pip *NewPip
);

/*[ mpsa_PclCreate/PclCreateExact
 *[ action:  creates a particle and appropriate pips depending on type,
 *[          making use of pip constructors detailed in pip definition.
 *[          global variables prevent repeated definition searches
 *[ objects: takes a simulation, and appends a particle of given type
 */

extern int mpsa_PclCreate(
  mpsa_Simulation *Simulation,
  mpsa_ParticleDefn *type
);

extern int mpsa_PclCreateExact(
  mpsa_Simulation *Simulation,
  mpsa_ParticleDefn *type,
  float m,
  float x[3],
  float v[3]
);

extern int mpsa_PclCreateExactAcc(
  mpsa_Simulation *Simulation,
  mpsa_ParticleDefn *type,
  float m,
  float x[3],
  float v[3],
  float a[3]
);

/*[ mpsa_DeletePcl
 *[ action:  deletes a particle and all pips associated, calling the 
 *[          destructors of those pips. again uses global variables to
 *[          prevent repeated searches.
 *[ objects: takes a pointer to the particle to be deleted
 */ 

extern int mpsa_DeletePcl(
  mpsa_Particle *Pcl
);

/*[ mpsa_DeletePcls
 *[ action:  routine to delete all particles after a given one in a list
 *[          used when deleting simulation and calls mpsa_DeletePcl
 *[ objects: takes pointer to first particle to be deleted
 */

extern int mpsa_DeletePcls(
  mpsa_Particle *firstPcl
);

/*[ mpsa_PclInitRnd
 *[ action:  initialises particle structure values with random or default
 *[          values to prevent particles being created on top of each other
 *[ objects: takes a pointer to a particle
 */

extern int mpsa_PclInitRnd(
  mpsa_Particle *Pcl
);

/*[ mpsa_AddPclToSimulation
 *[ action:  adds a newly created particle to a simulation structure, 
 *[          performing the neseccary book keeping operations
 *[ objects: takes a pointer to a simulation and a pointer to a new particle
 */

extern int mpsa_AddPclToSimulation(
  mpsa_Simulation *Simulation,
  mpsa_Particle *Pcl
);

/*[ mpsa_GetType
 *[ action:  obtains the dynamicly allocated numerical ID of a given particle
 *[          type determined by it's name
 *[ objects: takes a tcl interpreter and a particle type name, returns dynamic 
 *[          identifier in *type
 */

extern int mpsa_GetType(
  Tcl_Interp *interp,
  char *Label,
  int *type
);

/*[ mpsa_GetPipData
 *[ action:  obtains the pip type listing for a given particle type determined
 *[          by it's name
 *[ objects: takes a tcl interpreter and a name, returns a list of pip 
 *[          definitions
 */

extern int mpsa_GetPipData(
  Tcl_Interp *interp,
  char *Label,
  mpsa_Pip ***PipData,
  int *NumberPips
);

/*[ mpsa_SetPipToPipType
 *[ action:  set the pip in a particle to point to the correct pip type
 *[          in the pip list, using global variables to prevent repeated 
 *[          searches
 *[ objects: takes a particle and a pip definition
 */

extern int mpsa_SetPipToPipType(
  mpsa_Particle *Pcl,
  mpsa_Pip *ThisPipType
);

/*[ mpsa_ParticleHavePip
 *[ action:  a routine to test if a particle has a given pip, again using 
 *[          global variables to prevent excessive lookups. used in list
 *[          append commands
 *[ objects: takes a particle and a pip, returns MPSA_OKAY/FAIL
 */

extern int mpsa_ParticleHavePip(
  mpsa_Particle *Pcl,
  mpsa_Pip *Pip
);

/*[ mpsa_GetList
 *[ action:  gets a list structure pointer from the appropriate hash table
 *[          and returns it in *List
 *[ objects: takes name and tcl interpreter, returns a list pointer
 */

extern int mpsa_GetList(
  Tcl_Interp *interp,
  char *Label,
  mpsa_List **List
);

/*[ mpsa_GetSim
 *[ action:  get a simulation structure pointer from the hash table and 
 *[          returns it in *Simulation
 *[ objects: takes tcl interpreter and name of the simulation, returns pointer
 */

extern int mpsa_GetSim(
  Tcl_Interp *interp,
  char *Label,
  mpsa_Simulation **Simulation
);

/*[ mpsa_RemoveListFromHash
 *[ action:  remove list hash entry with the key ListName
 *[          used when deleteing lists
 *[ objects: name of list
 */

extern int mpsa_RemoveListFromHash(
  char *ListName
);

/*[ mpsa_RemoveSimFromHash
 *[ action:  remove simulation hash entry with the key SimName
 *[          used when deleting simulations
 *[ objects: name of simulation
 */

extern int mpsa_RemoveSimFromHash(
  char *SimName
);

extern int mpsa_GetInt(
  Tcl_Interp *interp,
  char *name,
  int *value
);

extern int mpsa_GetFloat(
  Tcl_Interp *interp,
  char *name,
  float *value
);

extern int mpsa_GetDouble(
  Tcl_Interp *interp,
  char *name,
  double *value
);

extern int mpsa_CopyName(
  char *OldName,
  char **NewName
);

extern float gwrand48();

#endif

