from collections import defaultdict
from matplotlib import pyplot
import numpy

histogram_isig = defaultdict(int)

scale = 10.0

for record in open('poly.log', 'r'):
    tokens = record.split()
    if not tokens:
        continue
    isig = int(round(scale * float(tokens[18]) / float(tokens[20])))

    histogram_isig[isig] += 1

x = []
y = []

for j in range(min(histogram_isig), max(histogram_isig) + 1):
    x.append(j / scale)
    y.append(histogram_isig[j])

_x = numpy.double(x)
_y = numpy.double(y)

pyplot.yscale('log')
pyplot.plot(_x, _y)
pyplot.axis([-10.0, 100.0, 1, 1000000])
pyplot.savefig('hist.pdf')


