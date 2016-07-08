import sys
from xia2_main import run

if __name__ == '__main__':
  if 'small_molecule=true' not in sys.argv:
    sys.argv.insert(1, 'small_molecule=true')
  run()
