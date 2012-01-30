/*
 * byte_offset.cpp
 *
 * An implementation of the byte_offset compression scheme used with CBF
 * images with the hopeful intention of replacing existing Python code for
 * doing this with something quicker. Main routines are:
 *
 * vector<char> compress(vector<int>)
 * vector<int> uncompress(vector<char>)
 *
 */

#include <iostream>
#include <vector>
#include <cstdlib>
#include <ctime>

using namespace std;

// unions to assist in byte manipulation

typedef union {
  char b[2];
  short s;
} u_s;

typedef union {
  char b[4];
  int i;
} u_i;

// functions for byte swapping

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

// helper function: is this machine little endian? CBF files are

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

// main functions

vector<char> compress(const vector<int> values)
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

      if ((-127 <= delta) && (delta <= 127))
        {
          c = (char) delta;
          packed.push_back(c);
          current += delta;
          continue;
        }

      packed.push_back(-128);

      if ((-32767 <= delta) && (delta <= 32767))
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

      if ((-2147483647 <= delta) && (delta <= 2147483647))
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

vector<int> uncompress(const vector<char> packed)
{
  vector<int> values(0);
  int current = 0;
  unsigned int j = 0;
  short s;
  char c;
  int i;
  bool le = little_endian();

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

// helper for timing tests

double ms(clock_t t1, clock_t t2)
{
  return 1000.0 * (t2 - t1) / CLOCKS_PER_SEC;
}

// demo / test code

int main(int argc,
         char ** argv)
{

  vector<int> values(0);

  unsigned int j;
  unsigned int size = 4096 * 4096;
  clock_t start;

  start = clock();

  for (j = 0; j < size; j ++)
    {
      values.push_back((rand() & 0xffff));
    }

  cout << "Generating: " << ms(start, clock()) << endl;

  start = clock();
  vector<char> packed = compress(values);
  cout << "Packing:    " << ms(start, clock()) << endl;


  start = clock();
  vector<int> unpacked = uncompress(packed);
  cout << "Unpacking:  " << ms(start, clock()) << endl;

  for (j = 0; j < unpacked.size(); j ++)
    {
      if (unpacked[j] != values[j])
        {
          cout << "Error for index " << j << endl;
        }
    }

  return 0;
}
