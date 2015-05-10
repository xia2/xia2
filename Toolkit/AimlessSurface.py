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

  abscor = []
  for t in range(0, 361, 5):
    for p in range(0, 181, 5):
      a = 1.0
      for l in range(1, order+1):
        for m in range(-l, l+1):
          a += Clm[(l,m)] * nsssphe.spherical_harmonic(l, m, t*d2r, p*d2r)
      abscor.append(abs(a))

  print min(abscor), max(abscor)

def scrape_coefficients():
  Clm = { }
  c = 0
  l = 0

  coefficients = []
  for record in open('aimless.log'):
    if 'Coefficient(Sd)' in record:
      for token in record.split()[1:]:
        coefficients.append(float(token.split('(')[0]))
  return coefficients

evaluate_1degree(scrape_coefficients())
