#!/usr/bin/env python

def run_job(executable, arguments = [], stdin = [], working_directory = None):
    '''Run a program with some command-line arguments and some input,
    then return the standard output when it is finished.'''

    import subprocess
    import os

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
                             shell = True,
                             env = os.environ)

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

def run_merge2cbf(linked_file_template, image_range, output_template):

    open('MERGE2CBF.INP', 'w').write(
        'NAME_TEMPLATE_OF_DATA_FRAMES=%s\n' % linked_file_template +
        'DATA_RANGE= %d %d\n' % image_range +
        'NAME_TEMPLATE_OF_OUTPUT_FRAMES=%s\n' % output_template +
        'NUMBER_OF_DATA_FRAMES_COVERED_BY_EACH_OUTPUT_FRAME=%d\n' %
        image_range[1])

    output = run_job('merge2cbf')

    return

def merge(filenames, output_template):
    '''Merge the cbf images of N files with random names.'''

    import os

    template = 'to_sum_%04d.cbf'

    for j, filename in enumerate(filenames):
        os.symlink(os.path.abspath(filename), os.path.join(
            os.getcwd(), template % (j + 1)))

    run_merge2cbf(os.path.join(os.getcwd(), template.replace('%04d', '????')),
                  (1, len(filenames)), output_template)

    for j in range(len(filenames)):
        os.remove(os.path.join(os.getcwd(), template % (j + 1)))

    return

def main():
    import sys
    import os

    assert(not os.path.exists(sys.argv[1]))

    merge(sys.argv[2:], 'summed_????.cbf')

    os.rename('summed_0001.cbf', sys.argv[1])

    print 'Merged %d images to %s' % (len(sys.argv[2:]), sys.argv[1])
    
if __name__ == '__main__':
    main()
