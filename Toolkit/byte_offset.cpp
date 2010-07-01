#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

typedef union {
  char b[2];
  short s;
} u_s;

typedef union {
  char b[4];
  short i;
} u_i;

void byte_swap_short(char * b)
{
  char c;
  c = b[0];
  b[0] = b[1];
  b[1] = c;
  return;
}

void byte_swap_int(char * b)
{
  char c;
  c = b[0];
  b[0] = b[3];
  b[3] = c;
  c = b[1];
  b[1] = b[2];
  b[2] = c;
  return;
}

bool little_endian()
{
  int i = 0x1;
  char b = ((u_i *) &i)[0].b[0];
  if (b == 0)
    {
      return false;
    }
  else
    {
      return true;
    }
}

vector<char> compress(vector<int> values)
{
  vector<char> packed(0);
  int current = 0;
  int delta, i;
  unsigned int j;
  bool le = little_endian();
  short s;
  char c;
  char * b;

  for (j = 0; j < values.size(); j++)
    {
      delta = values[j] - current;

      if ((-127 < delta) && (delta < 127))
	{
	  c = (char) delta;
	  packed.push_back(c);
	  current += delta;
	  continue;
	}

      packed.push_back(-128);

      if ((-32767 < delta) && (delta < 32767))
	{
	  s = (short) delta;
	  b = ((u_s *) & s)[0].b;

	  if (!le) 
	    {
	      byte_swap_short(b);
	    }

	  packed.push_back(b[0]);
	  packed.push_back(b[1]);
	  current += delta;
	  continue;
	}

      s = -32768;
      b = ((u_s *) & s)[0].b;

      if (!le) 
	{
	  byte_swap_short(b);
	}
      
      packed.push_back(b[0]);
      packed.push_back(b[1]);
      
      if ((-2147483647 < delta) && (delta < 2147483647))
	{
	  i = delta;
	  b = ((u_i *) & i)[0].b;

	  if (!le) 
	    {
	      byte_swap_int(b);
	    }

	  packed.push_back(b[0]);
	  packed.push_back(b[1]);
	  packed.push_back(b[2]);
	  packed.push_back(b[3]);
	  current += delta;
	  continue;
	}

      /* FIXME I should not get here */

    }

  return packed;
}

vector<int> uncompress(vector<char> packed)
{
  vector<int> values(0);

  int delta;
  int current = 0;

  unsigned int j;
  short s;
  char c;
  int i;

  bool le = little_endian();

  j = 0;

  while (j < packed.size())
    {
      c = packed[j];
      j += 1;

      if (c != -128)
	{
	  current += c;
	  values.push_back(current);
	  continue;
	}

      ((u_s *) & s)[0].b[0] = packed[j];
      ((u_s *) & s)[0].b[1] = packed[j + 1];
      j += 2;
      
      if (!le) 
	{
	  byte_swap_short((char *) &s);
	}

      if (s != -32768)
	{
	  current += s;
	  values.push_back(current);
	  continue;
	}
	  
      ((u_i *) & i)[0].b[0] = packed[j];
      ((u_i *) & i)[0].b[1] = packed[j + 1];
      ((u_i *) & i)[0].b[2] = packed[j + 2];
      ((u_i *) & i)[0].b[3] = packed[j + 3];
      j += 4;
      
      if (!le) 
	{
	  byte_swap_int((char *) &i);
	}

      current += i;
      values.push_back(current);
    }

  return values;
} 

int main(int argc,
	 char ** argv)
{

  vector<int> values(0);

  unsigned int j;

  for (j = 0; j < 100; j ++)
    {
      values.push_back((rand() & 0xffff));
    }

  if (little_endian())
    {
      cout << "Little endian" << endl;
    }
  else
    {
      cout << "Big endian" << endl;
    }

  vector<char> packed = compress(values);
  vector<int> unpacked = uncompress(packed);

  for (j = 0; j < unpacked.size(); j ++)
    {
      cout << unpacked[j] << "\t" << values[j] << endl;
    }

  return 0;
}
  
