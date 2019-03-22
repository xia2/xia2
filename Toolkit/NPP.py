from __future__ import absolute_import, division, print_function

import math

from scitbx.array_family import flex
from scitbx.math import distributions
from scitbx.random import poisson_distribution, variate


def test():
    numbers = variate(poisson_distribution(mean=1000))
    data = flex.double()
    for j in range(1000):
        data.append(next(numbers))

    _x, _y = npp_ify(data)
    fit = flex.linear_regression(_x, _y)
    fit.show_summary()

    _x, _y = npp_ify(data, input_mean_variance=(1000, 1000))
    fit = flex.linear_regression(_x, _y)
    fit.show_summary()


def mean_variance(values):
    m = flex.sum(values) / values.size()
    m2 = flex.sum(values * values) / values.size()
    v = m2 - m ** 2
    return m, v


def npp_ify(values, input_mean_variance=None):
    """Analyse data in values (assumed to be drawn from one population) and
  return the sorted list of (expected, observed) deviation from the mean."""

    distribution = distributions.normal_distribution()
    values = flex.sorted(values)
    if input_mean_variance:
        mean, variance = input_mean_variance
    else:
        mean, variance = mean_variance(values)

    scaled = (values - mean) / math.sqrt(variance)
    expected = distribution.quantiles(values.size())

    return expected, scaled


if __name__ == "__main__":
    test()
