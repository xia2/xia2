from __future__ import division

def work():
  from scitbx import math
  from scitbx.array_family import flex
  N=15
  lfg =  math.log_factorial_generator(N)
  nsssphe = math.nss_spherical_harmonics(6,50000,lfg)

  l = 2
  m = 1
  t = 1
  p = 1

  print nsssphe.spherical_harmonic(2, 1, 1, 1)

def n_terms():
  orders = {}
  for j in range(10):
    nterms = 0
    for k in range(1, j+1):
      for l in range(-k, k+1):
        nterms += 1
    orders[nterms] = j
  print orders

def order_from_nterm(n):
  return {0: 0, 80: 8, 3: 1, 8: 2, 15: 3, 48: 6, 99: 9, 35: 5, 24: 4, 63: 7}[n]

def evaluate_1degree(ClmList):
  from scitbx import math
  from scitbx.array_family import flex
  import math as pymath
  import numpy
  d2r = pymath.pi / 180.0
  order = order_from_nterm(len(ClmList))
  lfg =  math.log_factorial_generator(2 * order + 1)
  nsssphe = math.nss_spherical_harmonics(order,50000,lfg)
  Clm = { }
  idx = 0
  for l in range(1, order+1):
    for m in range(-l, l+1):
      Clm[(l,m)] = ClmList[idx]
      idx += 1

  abscor = numpy.empty((1+180//1, 1+360//1), float, 'C')
  sqrt2 = pymath.sqrt(2)
  for t in range(0, 181, 1):
    for p in range(0, 361, 1):
      a = 1.0
      for l in range(1, order+1):
        for m in range(-l, l+1):
          # Ylm = nsssphe.spherical_harmonic(l, m, t*d2r, p*d2r)
          # Convert from complex to real according to
          # http://en.wikipedia.org/wiki/Spherical_harmonics#Real_form
          Ylm = nsssphe.spherical_harmonic(l, abs(m), t*d2r, p*d2r)
          if m < 0:
            a += Clm[(l,m)] * sqrt2 * ((-1) ** m) * Ylm.imag
          elif m == 0:
            assert(Ylm.imag == 0.0)
            a += Clm[(l,m)] * Ylm.real
          else:
            a += Clm[(l,m)] * sqrt2 * ((-1) ** m) * Ylm.real
      abscor[(t//1, p//1)] = a
  return abscor

def generate_map(abscor, png_filename):
  import matplotlib
  matplotlib.use('Agg')
  from matplotlib import pyplot
  plot = pyplot.imshow(abscor)
  pyplot.colorbar()
  pyplot.savefig(png_filename)

def scrape_coefficients(log_file_name):
  # FIXME cope with cases where the surfaces are not LINKed => will be several
  # of them...
  Clm = { }
  c = 0
  l = 0

  coefficients = []
  for record in open(log_file_name):
    if 'Coefficient(Sd)' in record:
      for token in record.split()[1:]:
        coefficients.append(float(token.split('(')[0]))
  return coefficients

if __name__ == '__main__':
  import sys
  generate_map(evaluate_1degree(scrape_coefficients(sys.argv[1])), sys.argv[2])
