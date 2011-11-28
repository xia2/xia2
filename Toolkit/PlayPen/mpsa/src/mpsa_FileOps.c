/* gsimII mpsa file operations file v1.0
 * maintained by g.winter
 * 23rd august 2000
 * 
 * 
 */

#include "mpsa_private.h"

mpsa_typeConversionTableElement **TranslationTable = NULL;
int NumberOfTableElements = 0;
int ByteOrder = BIG_END;
mpsa_ParticleDefn *MostRecentDefn = NULL;
int MostRecentID = -1;
int FloatSize = 4;
int IntSize = 4;

/*[ mpsa_WriteSimulation
 *[ action:  write a simulation structure to a binary tcl channel
 *[          swapping bytes as necessary
 *[ objects: takes a simulation and a tcl channel
 */

int mpsa_WriteSimulation(
  mpsa_Simulation *Simulation,
  Tcl_Channel chan
)
{
  FloatSize = sizeof(float);
  IntSize = sizeof(int);
  mpsa_WriteFloat(Simulation->dt, chan);
  mpsa_WriteFloat(Simulation->age, chan);
  mpsa_WriteFloat(Simulation->ScaleLength, chan);
  mpsa_WriteFloat(Simulation->ScaleTime, chan);
  mpsa_WriteFloat(Simulation->ScaleMass, chan);
  return MPSA_OKAY;
}

/*[ mpsa_WritePcl
 *[ action:  write all of the data from a particle structure, including
 *[          pip information, to a tcl channel
 *[ objects: 
 */

int mpsa_WritePcl(
  mpsa_Particle *Pcl,
  Tcl_Channel chan
)
{
  int i;
  if(Pcl->type != MostRecentID) {
    mpsa_GetPclDefnFromID(Pcl->type, &MostRecentDefn);
    MostRecentID = MostRecentDefn->DynamicID;
  }

  for(i = 0; i < 3; i++) {
    mpsa_WriteFloat(Pcl->x[i], chan);
  }
  for(i = 0; i < 3; i++) {
    mpsa_WriteFloat(Pcl->v[i], chan);
  }
  for(i = 0; i < 3; i++) {
    mpsa_WriteFloat(Pcl->a[i], chan);
  }
  mpsa_WriteFloat(Pcl->mass, chan);
  mpsa_WriteInteger(Pcl->type, chan);
  mpsa_WriteInteger(Pcl->origin, chan);

  for(i = 0; i < (MostRecentDefn->NPips); i++) {
    (*(MostRecentDefn->Piptypes[i]->Writer))(chan, Pcl->PipList[i]);
  }

  return MPSA_OKAY;
}

/*[ mpsa_WriteFloat/Integer
 *[ action:  write value to tcl channel, making appropriate byte swapping
 *[          action
 *[ objects: takes a value and a tcl channel
 */

int mpsa_WriteFloat(
  float Value,
  Tcl_Channel chan
)
{
  char *Byte;
  char Temp;

  if(ByteOrder == BIG_END) {
    Byte = (char *) &Value;
    Tcl_Write(chan, Byte, FloatSize);
  } else {
    Byte = (char *) &Value;
    Temp = Byte[0];
    Byte[0] = Byte[3];
    Byte[3] = Temp;
    Temp = Byte[1];
    Byte[1] = Byte[2];
    Byte[2] = Temp;
    Tcl_Write(chan, Byte, FloatSize);
  }

  return MPSA_OKAY;
}

int mpsa_WriteInteger(
  int Value,
  Tcl_Channel chan
)
{
  char *Byte;
  char Temp;

  if(ByteOrder == BIG_END) {
    Byte = (char *) &Value;
    Tcl_Write(chan, Byte, IntSize);
  } else {
    Byte = (char *) &Value;
    Temp = Byte[0];
    Byte[0] = Byte[3];
    Byte[3] = Temp;
    Temp = Byte[1];
    Byte[1] = Byte[2];
    Byte[2] = Temp;
    Tcl_Write(chan, Byte, IntSize);
  }

  return MPSA_OKAY;
}

/*[ mpsa_SetByteOrder
 *[ action:  sets the correct byte ordering for machine type
 *[ objects: name
 */

int mpsa_SetByteOrder(
  char *Platform
)
{
  if((strcmp(Platform, "Intel") == 0) || (strcmp(Platform, "intel") == 0)) {
    ByteOrder = LITTLE_END;
  } else if ((strcmp(Platform, "Alpha") == 0) || (strcmp(Platform, "alpha")
    == 0)) {
    ByteOrder = LITTLE_END;
  } else if ((strcmp(Platform, "Sun") == 0) || (strcmp(Platform, "sun")
    == 0)) {
    ByteOrder = BIG_END;
  } else if ((strcmp(Platform, "Sgi") == 0) || (strcmp(Platform, "sgi")
    == 0)) {
    ByteOrder = BIG_END;
  } else {
    return MPSA_FAIL;
  }

  return MPSA_OKAY;
}

/*[ mpsa_CreateConversionTable
 *[ action:  creates a type conversion table of predefined size
 *[ objects: takes a number of elements to make space for
 */

int mpsa_CreateConversionTable(
  int NumberOfElements
)
{
  int i;

  if(TranslationTable != NULL) {
    mpsa_DeleteConversionTable();
  }
  NumberOfTableElements = NumberOfElements;
  TranslationTable = (mpsa_typeConversionTableElement **) malloc (
    sizeof(mpsa_typeConversionTableElement *) * NumberOfElements);
  for(i = 0; i < NumberOfElements; i++) {
    TranslationTable[i] = (mpsa_typeConversionTableElement *) malloc
      (sizeof(mpsa_typeConversionTableElement));
    TranslationTable[i]->typeName = NULL;
  }

  return MPSA_OKAY;
}

/*[ mpsa_DeleteConversionTable
 *[ action:  delete the conversion table including all names;
 *[ objects: none
 */

int mpsa_DeleteConversionTable()
{
  int i;

  for(i = 0; i < NumberOfTableElements; i++) {
    free(TranslationTable[i]->typeName);
    free(TranslationTable[i]);
  }

  free(TranslationTable);
  TranslationTable = NULL;

  return MPSA_OKAY;
}

/*[ mpsa_WriteConversionTableElement
 *[ action:  writes an element of the conversion table from the old id,
 *[          the name and the new id
 *[ objects: takes the old id, the name and the new id of a particle type
 */

int mpsa_WriteConversionTableElement(
  int OldID,
  char *Name,
  int NewID
)
{
  int NameLength;

  NameLength = strlen(Name);

  TranslationTable[OldID]->typeName = (char *) malloc (sizeof(char) * 
    NameLength);
  TranslationTable[OldID]->typeName = strcpy(TranslationTable[OldID]->typeName,
    Name);
  TranslationTable[OldID]->NewID = NewID;

  return MPSA_OKAY;
}

/*[ mpsa_GetNewTabulatedID
 *[ action:  gets new dynamic ID from old dynamic ID
 *[ objects: takes an integer ID and returns another
 */

int mpsa_GetNewTabulatedID(
  int OldID
)
{
  return TranslationTable[OldID]->NewID;
}

/*[ mpsa_ReadFloat/Integer
 *[ action:  read value from a tcl channel, performing appropriate byte
 *[          swapping actions
 *[ objects: a tcl channel from which to read and returns *Value
 */

int mpsa_ReadFloat(
  float *Value,
  Tcl_Channel chan
)
{
  char Byte[4];
  char *Temp;
  int i;

  Temp = (char *) Value;

  Tcl_Read(chan, Byte, FloatSize);
  
  if(ByteOrder == BIG_END) {
    for(i = 0; i < FloatSize; i++) {
      Temp[i] = Byte[i];
    }
  } else {
    for(i = 0; i < FloatSize; i++) {
      Temp[i] = Byte[FloatSize - i - 1];
    }
  }

  return MPSA_OKAY;
}

int mpsa_ReadInteger(
  int *Value,
  Tcl_Channel chan
)
{
  char Byte[4];
  char *Temp;
  int i;

  Temp = (char *) Value;

  Tcl_Read(chan, Byte, IntSize);
  
  if(ByteOrder == BIG_END) {
    for(i = 0; i < FloatSize; i++) {
      Temp[i] = Byte[i];
    }
  } else {
    for(i = 0; i < FloatSize; i++) {
      Temp[i] = Byte[FloatSize - i - 1];
    }
  }

  return MPSA_OKAY;
}

/*[ mpsa_ReadPcl
 *[ action:  create a new blank particle in a simulation and set 
 *[          all of it's values to those stored in the data file, including pip
 *[          data
 *[ objects: takes a simulation and a tcl channel
 */

int mpsa_ReadPcl(
  mpsa_Simulation *Simulation,
  Tcl_Channel chan
)
{
  mpsa_Particle *Pcl;
  int Oldtype, Newtype, origin;
  float tempx[3], tempv[3], tempa[3], tempmass;
  int i;

  for(i = 0; i < 3; i++) {
    mpsa_ReadFloat(&tempx[i], chan);
  }
  for(i = 0; i < 3; i++) {
    mpsa_ReadFloat(&tempv[i], chan);
  }
  for(i = 0; i < 3; i++) {
    mpsa_ReadFloat(&tempa[i], chan);
  }
  mpsa_ReadFloat(&tempmass, chan);
  mpsa_ReadInteger(&Oldtype, chan);
  mpsa_ReadInteger(&origin, chan);

  Newtype = mpsa_GetNewTabulatedID(Oldtype);

  if(MostRecentID != Newtype) {
    mpsa_GetPclDefnFromID(Newtype, &MostRecentDefn);
    MostRecentID = Newtype;
  }

  mpsa_PclCreate(Simulation, MostRecentDefn);

  Pcl = Simulation->lastPcl;

  for(i = 0; i < 3; i++) {
    Pcl->x[i] = tempx[i];
    Pcl->v[i] = tempv[i];
    Pcl->a[i] = tempa[i];
  }
  Pcl->mass = tempmass;

  for(i = 0; i < MostRecentDefn->NPips; i++) {
    MostRecentDefn->Piptypes[i]->Reader(chan, Pcl->PipList[i]);
  }

  Pcl->origin = origin;

  return MPSA_OKAY;
}
