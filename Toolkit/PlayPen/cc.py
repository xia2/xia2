import math
import random

def population(N, i):
    return [random.expovariate(1.0 / i) for j in range(N)]

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def noisy_population(population, isigma):
    return [p + random.gauss(0, p / isigma) for p in population]

def cc(a, b):
    _a = sum(a) / len(a)
    _b = sum(b) / len(b)

    sum_ab = 0.0

    for j in range(len(a)):
        sum_ab += (a[j] - _a) * (b[j] - _b)

    sum_aa = sum([(aj - _a) * (aj - _a) for aj in a])
    sum_bb = sum([(bj - _b) * (bj - _b) for bj in b])

    return sum_ab / (math.sqrt(sum_aa) * math.sqrt(sum_bb))

if __name__ == '__main__':

    i = 1.0

    for p_N in range(9):
        N = int(10 * math.pow(2, p_N))

        print N
        pop = population(N, i)

        for p_isigma in range(5):

            isigma = math.pow(2, p_isigma)

            ccs = [cc(noisy_population(pop, isigma),
                      noisy_population(pop, isigma)) for j in range(100)]

            print '%4.1f' % float(isigma), '%.4f %.4f' % meansd(ccs)
