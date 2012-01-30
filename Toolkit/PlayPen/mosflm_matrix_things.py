import os
import sys
import math
import subprocess

from cctbx import sgtbx
from cctbx import crystal
from cctbx import uctbx
from scitbx import matrix
from cctbx.sgtbx.lattice_symmetry import metric_subgroups

def run_job(executable, arguments = [], stdin = [], working_directory = None):
    '''Run a program with some command-line arguments and some input,
    then return the standard output when it is finished.'''

    if working_directory is None:
        working_directory = os.getcwd()

    command_line = '%s' % executable
    for arg in arguments:
        command_line += ' "%s"' % arg

    popen = subprocess.Popen(command_line,
                             bufsize = 1,
                             stdin = subprocess.PIPE,
                             stdout = subprocess.PIPE,
                             stderr = subprocess.STDOUT,
                             cwd = working_directory,
                             universal_newlines = True,
                             shell = True)

    for record in stdin:
        popen.stdin.write('%s\n' % record)

    popen.stdin.close()

    output = []

    while True:
        record = popen.stdout.readline()
        if not record:
            break

        output.append(record)

    return output

def meansd(values):
    mean = sum(values) / len(values)
    var = sum([(v - mean) * (v - mean) for v in values]) / len(values)
    return mean, math.sqrt(var)

def get_mosflm_cell(records):
    for record in records:
        if 'Refined cell' in record:
            return tuple(map(float, record.split()[-6:]))

def get_mosflm_rmsd(records):
    rmsd = { }
    current_image = None

    for record in records:
        if 'Processing Image' in record:
            current_image = int(record.split()[2])

        if 'Rms Resid' in record:
            rmsd[current_image] = float(record.split()[-2])

    return rmsd

def parse_matrix(matrix_text):

    tokens = map(float, matrix_text.replace('-', ' -').split())

    cell = tokens[21:27]
    a = tokens[0:9]
    u = tokens[12:21]

    return cell, a, u

def format_matrix(cell, a, u):

    matrix_format = ' %11.8f %11.8f %11.8f\n' + \
                    ' %11.8f %11.8f %11.8f\n' + \
                    ' %11.8f %11.8f %11.8f\n'

    cell_format = ' %11.4f %11.4f %11.4f %11.4f %11.4f %11.4f\n'

    misset = '       0.000       0.000       0.000\n'

    return matrix_format % tuple(a) + misset + matrix_format % tuple(u) + \
           cell_format % tuple(cell) + misset

def mosflm_a_to_cell(mosflm_a_matrix, wavelength):
    real_a = matrix.sqr(mosflm_a_matrix).inverse()

    a = wavelength * matrix.col(real_a.elems[0:3])
    b = wavelength * matrix.col(real_a.elems[3:6])
    c = wavelength * matrix.col(real_a.elems[6:9])

    r2d = 180.0 / math.pi

    return math.sqrt(a.dot()), math.sqrt(b.dot()), math.sqrt(c.dot()), \
           b.angle(c) * r2d, c.angle(a) * r2d, a.angle(b) * r2d

def calculate_wavelength(unit_cell, mosflm_a_matrix):
    real_a = matrix.sqr(mosflm_a_matrix).inverse()

    a = matrix.col(real_a.elems[0:3])
    b = matrix.col(real_a.elems[3:6])
    c = matrix.col(real_a.elems[6:9])

    r2d = 180.0 / math.pi

    assert(math.fabs(a.angle(b) * r2d - unit_cell[5]) < 0.1)
    assert(math.fabs(b.angle(c) * r2d - unit_cell[3]) < 0.1)
    assert(math.fabs(c.angle(a) * r2d - unit_cell[4]) < 0.1)

    wavelength = (unit_cell[0] / math.sqrt(a.dot()) + \
                  unit_cell[1] / math.sqrt(b.dot()) + \
                  unit_cell[2] / math.sqrt(c.dot())) / 3.0

    return wavelength

def generate_lattice_options(unit_cell, space_group_name):
    cs = crystal.symmetry(
        unit_cell = unit_cell,
        space_group_symbol = space_group_name)

    original_reindex = cs.change_of_basis_op_to_minimum_cell()

    groups = metric_subgroups(input_symmetry = cs, max_delta = 0.0)

    result = []

    for item in groups.result_groups:

        cs = item['ref_subsym']

        convert_to_best_cell = True

        if convert_to_best_cell:
            cb = cs.change_of_basis_op_to_best_cell(
                best_monoclinic_beta = False)
            cs_best = cs.change_basis(cb)

            o_unit_cell = cs_best.unit_cell().parameters()
            sg = cs_best.space_group().build_derived_acentric_group()

            o_space_group_name = sg.type().universal_hermann_mauguin_symbol()
            reindex = (cb * item['subsym'].space_group_info().type().cb_op(
                ) * original_reindex).c().r().as_double()

            result.append((o_space_group_name, o_unit_cell, reindex))

        else:

            o_unit_cell = cs.unit_cell().parameters()
            sg = cs.space_group().build_derived_acentric_group()

            o_space_group_name = sg.type().universal_hermann_mauguin_symbol()
            reindex = (item['subsym'].space_group_info().type().cb_op(
                ) * original_reindex).c().r().as_double()

            result.append((o_space_group_name, o_unit_cell, reindex))

    return result

def apply_reindex_operation(mosflm_a_matrix, mosflm_u_matrix, reindex):

    a = matrix.sqr(mosflm_a_matrix)
    u = matrix.sqr(mosflm_u_matrix)
    r = matrix.sqr(reindex).transpose()

    return a * r, u * r

def compute_u(mosflm_a_matrix, unit_cell, wavelength):

    uc = uctbx.unit_cell(unit_cell)
    A = (1.0 / wavelength) * matrix.sqr(mosflm_a_matrix)
    B = matrix.sqr(uc.orthogonalization_matrix()).inverse()

    return A * B.inverse()

def macguffin(mosflm_matrix, space_group_name):

    cell, a, u = parse_matrix(mosflm_matrix)

    wavelength = calculate_wavelength(cell, a)

    options = generate_lattice_options(cell, space_group_name)

    results = []

    for o_space_group_name, o_unit_cell, reindex in options:
        o_a, o_u = apply_reindex_operation(a, u, reindex)

        if False:
            print '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % o_unit_cell
            print '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % mosflm_a_to_cell(
                o_a, wavelength)

        results.append((spacegroup_long_to_short(o_space_group_name),
                        format_matrix(o_unit_cell, o_a, o_u)))

    return results

def spacegroup_long_to_short(spacegroup_name):

    if ':' in spacegroup_name:
        spacegroup_name = spacegroup_name.split(
            ':')[0].replace('R', 'H').strip()

    for record in open(os.path.join(os.environ['CLIBD'], 'symop.lib')):
        if ' ' in record[:1]:
            continue

        tokens = record.split()

        short_name = tokens[3]
        long_name = record.split('\'')[1]

        if long_name == spacegroup_name:
            return short_name

    raise RuntimeError, 'can not find %s' % spacegroup_name

def super_test():

    original_commands = '''template "insulin_1_0##.img"
    directory "/data/graeme/test/demo"
    matrix %s.mat
    beam 94.329000 94.497600
    distance 159.720000
    symmetry %s
    mosaic 0.250000
    resolution 1.850000
    wavelength 0.979000
    !parameters from autoindex run
    raster 19 21 11 6 6
    separation 0.650000 0.730000
    separation close
    refinement residual 15
    refinement include partials
    limits xscan 94.003200 yscan 94.003200
    postref multi segments 3 repeat 10
    postref maxresidual 5.0
    process 1 3
    go
    process 20 22
    go
    process 43 45
    go
    '''

    original_matrix = ''' -0.00729930 -0.00995677  0.00173476
  0.01009847 -0.00709839  0.00174938
-0.000409412  0.00242942  0.01222117
       0.000       0.000       0.000
 -0.58548911 -0.79864911  0.13914780
  0.81001486 -0.56937347  0.14032030
 -0.03283962  0.19486779  0.98027960
     78.5272     78.5272     78.5272     90.0000     90.0000     90.0000
       0.000       0.000       0.000
'''

    original_spacegroup = 'I23'

    for spacegroup, matrix in macguffin(original_matrix, original_spacegroup):
        open('%s.mat' % spacegroup, 'w').write(matrix)

        commands = (original_commands % (spacegroup, spacegroup)).split('\n')

        output = run_job('ipmosflm', [], commands)

        rmsds = get_mosflm_rmsd(output)

        m, s = meansd([rmsds[image] for image in sorted(rmsds)])

        print '%10s %.3f %.3f' % (spacegroup, m, s), \
              '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % \
              parse_mosflm_matrix(matrix)[0]

def get_mosflm_commands(lines_of_input):
    '''Get the commands which were sent to Mosflm.'''

    result = []

    for line in lines_of_input:
        if '===>' in line:
            result.append(line.replace('===>', '').strip())
        if 'MOSFLM =>' in line:
            result.append(line.replace('MOSFLM =>', '').strip())

    return result

def nint(a):
    return int(round(a) - 0.5) + (a > 0)

def super_test_deux(mosflm_lp_file):

    commands = get_mosflm_commands(open(mosflm_lp_file).readlines())

    original_commands = []

    for c in commands:
        if 'matrix' in c:
            original_commands.append('matrix %s.mat')
            original_matrix = open(c.split()[-1]).read()
        elif 'symmetry' in c:
            original_commands.append('symmetry %s')
            original_spacegroup = c.split()[-1]
        else:
            original_commands.append(c)

    for spacegroup, matrix in macguffin(original_matrix, original_spacegroup):

        cell = tuple(parse_matrix(matrix)[0])

        name = '%s-%d-%d-%d-%d-%d-%d' % (spacegroup, cell[0], cell[1],
                                         cell[2], cell[3], cell[4], cell[5])

        open('%s.mat' % name, 'w').write(matrix)

        commands = ('\n'.join(original_commands) % (name, spacegroup)
                    ).split('\n')

        output = run_job('ipmosflm', [], commands)

        open('%s.log' % name, 'w').write(''.join(output))

        rmsds = get_mosflm_rmsd(output)

        cell = get_mosflm_cell(output)

        m, s = meansd([rmsds[image] for image in sorted(rmsds)])

        print '%10s %.3f %.3f' % (spacegroup, m, s), \
              '%6.2f %6.2f %6.2f %6.2f %6.2f %6.2f' % tuple(cell)

if __name__ == '__main__':

    super_test_deux(sys.argv[1])
