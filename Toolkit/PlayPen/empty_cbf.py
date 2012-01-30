import os
import sys
import shutil

def empty_cbf(fin, fout):
    data = open(fin).read()

    assert('CBF_template_file:' in data)
    assert(not os.path.exists(fout))

    header = data.split('# CBF_template_file:')[0] + ';\n'
    image = '\n_array_data.data' + data.split('_array_data.data')[1]

    open(fout, 'w').write(header + image)

    return

class handler:

    def __init__(self, source, target):
        self._source = source
        self._target = target
        self._files = []
        return

    def add_file(self, f):
        assert(os.path.exists(f))
        self._files.append(f)
        return

    def work(self):
        for f in self._files:
            fin = f
            fout = f.replace(self._source, self._target)
            fout_dir = os.path.split(fout)[0]
            if not os.path.exists(fout_dir):
                os.makedirs(fout_dir)
            print '%s => %s' % (fin, fout)
            empty_cbf(fin, fout)
        return

    def number(self):
        return len(self._files)

handler = handler(os.getcwd(), os.path.join(os.getcwd(), 'empty'))

def handle_directory(root, directory, files):
    for f in files:
        if not '.cbf' in f[-4:]:
            continue
        handler.add_file(os.path.join(directory, f))

def work():
    os.path.walk(os.getcwd(), handle_directory, os.getcwd())
    print 'found %d files' % handler.number()
    handler.work()

if __name__ == '__main__':
    work()
