from __future__ import division

def index_solution(tokens):
    from collections import namedtuple
    IndexSolution = namedtuple('IndexSolution',
                               'penalty sdcell fracn latt cell')

    cell = tuple(map(float, tokens[5:11]))
    return IndexSolution(int(tokens[1]), float(tokens[2]), float(tokens[3]),
                         tokens[4], cell)

def parse_index_log(mosflm_output):
    n_solutions = 0
    solutions = [ ]

    for record in mosflm_output:
        if 'DIRECT SPACE VECTORS DID NOT RESULT INTO A ORIENTATION' in record:
            from Exceptions import AutoindexError
            raise AutoindexError, 'indexing failed'

    for j, record in enumerate(mosflm_output):
        if ' No PENALTY SDCELL FRACN LATT      a        b        c' in record:
            k = j
            while n_solutions < 44:
                try:
                    lattice_character = int(mosflm_output[k].split()[0])
                    if not 'unrefined' in mosflm_output[k]:
                        solutions.append(index_solution(
                            mosflm_output[k].split()))

                    n_solutions += 1
                    k += 1
                except ValueError, e:
                    k += 1
                    continue
                except IndexError, e:
                    k += 1
                    continue

    return solutions
