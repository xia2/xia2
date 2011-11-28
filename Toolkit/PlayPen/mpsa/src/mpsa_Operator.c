/* gsimII mpsa operators file v1.0
 * maintained by g.winter
 * 16th august 2000
 * 
 * 
 */

#include "mpsa_export.h"
#include "mpsa_private.h"

int (*IntOperator)(int, int);
int (*FloatOperator)(float, float);

/*[ mpsa_SetOperator
 *[ action:  set appropriate operator for use with list append command
 *[          uses global variables for sake of efficiency
 *[ objects: takes name of operator, eg >=
 */

int mpsa_SetOperator(
  char *OperatorName
)
{
  if(strcmp(OperatorName, ">") == 0) {
    IntOperator = mpsa_IntGreater;
    FloatOperator = mpsa_FloatGreater;
  } else if (strcmp(OperatorName, "<") == 0) {
    IntOperator = mpsa_IntLess;
    FloatOperator = mpsa_FloatLess;
  } else if (strcmp(OperatorName, "==") == 0) {
    IntOperator = mpsa_IntEqual;
    FloatOperator = mpsa_FloatEqual;
  } else if (strcmp(OperatorName, "!=") == 0) {
    IntOperator = mpsa_IntNotEqual;
    FloatOperator = mpsa_FloatNotEqual;
  } else if (strcmp(OperatorName, ">=") == 0) {
    IntOperator = mpsa_IntGreaterEqual;
    FloatOperator = mpsa_FloatGreaterEqual;
  } else if (strcmp(OperatorName, "<=") == 0) {
    IntOperator = mpsa_IntLessEqual;
    FloatOperator = mpsa_FloatLessEqual;
  } else {
    return MPSA_FAIL;
  }

  return MPSA_OKAY;
}

/*[ mpsa_BinaryOperators
 *[ action:  act as wrapper functions to binary operators to enable faster
 *[          action in list appending command, as pointers to functions can
 *[          be set, as set above and used below
 *[ objects: all take two variables and return MPSA_OKAY = true, MPSA_FAIL =
 *[          false
 */

int mpsa_IntGreater(
  int a,
  int b
)
{
  if(a > b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_FloatGreater(
  float a,
  float b
)
{
  if(a > b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_IntLess(
  int a,
  int b
)
{
  if(a < b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_FloatLess(
  float a,
  float b
)
{
  if(a < b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_IntEqual(
  int a,
  int b
)
{
  if(a == b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_FloatEqual(
  float a,
  float b
)
{
  if(a == b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_IntNotEqual(
  int a,
  int b
)
{
  if(a != b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_FloatNotEqual(
  float a,
  float b
)
{
  if(a != b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_IntGreaterEqual(
  int a,
  int b
)
{
  if(a >= b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_FloatGreaterEqual(
  float a,
  float b
)
{
  if(a >= b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_IntLessEqual(
  int a,
  int b
)
{
  if(a <= b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

int mpsa_FloatLessEqual(
  float a,
  float b
)
{
  if(a <= b) {
    return MPSA_OKAY;
  } else {
    return MPSA_FAIL;
  }
}

/*[ mpsa_Int/Float Operator
 *[ action:  generic operator as set above, returns value of operator acting
 *[          on two variables
 *[ objects: takes two variables, returns MPSA_OKAY = true, MPSA_FAIL = false
 */

int mpsa_IntOperator(
  int a,
  int b
)
{
  return IntOperator(a, b);
}

int mpsa_FloatOperator(
  float a,
  float b
)
{
  return FloatOperator(a, b);
}

