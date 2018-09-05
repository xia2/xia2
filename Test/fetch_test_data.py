from __future__ import absolute_import, division, print_function

import hashlib
import os
import queue
import sys
import threading
import time
import urllib2

def download_to_file(url, file):
  """Downloads a URL to file. Returns the file size.
     Returns -1 if the downloaded file size does not match the expected file
     size
     Simplified version of the one used in bootstrap script.
  """
  socket = urllib2.urlopen(url)
  file_size = int(socket.info().getheader('Content-Length'))
  # There is no guarantee that the content-length header is set
  received = 0
  block_size = 8192
  # Allow for writing the file immediately so we can empty the buffer
  with open(file, 'wb') as f:
    while True:
      block = socket.read(block_size)
      received += len(block)
      f.write(block)
      if not block: break
  socket.close()

  if (file_size > 0) and (file_size != received):
    return -1
  return received

def file_md5(filename):
  hash_md5 = hashlib.md5()
  with open(filename, "rb") as f:
    for chunk in iter(lambda: f.read(40960), b""):
      hash_md5.update(chunk)
  return hash_md5.hexdigest().lower()

def fetch_test_data(target_dir, skip_existing_files=True, retry_limit=3, verify_threads=8, download_threads=8,
    verbose=False):
  if not os.path.exists(target_dir):
    os.mkdir(target_dir)
  os.chdir(target_dir)

  errors = queue.Queue()
  verify_queue = queue.Queue()
  download_queue = queue.Queue()
  print_queue = queue.Queue()

  class Printer(threading.Thread):
    def __init__(self, *args, **kwargs):
      threading.Thread.__init__(self)
      self.daemon = True
    def print(self, string):
      if verbose:
        print(string)
      else:
        print("\r" + string, end=" "*max(0, getattr(self, 'last_line_length', 0)-len(string)))
        sys.stdout.flush()
        self.last_line_length = len(string)
    def run(self):
      while True:
        item = print_queue.get()
        if not verbose:
          aggregate = time.time()
          try:
            while time.time() < aggregate + 0.01:
              print_queue.get(False)
              print_queue.task_done()
          except queue.Empty:
            pass
        prefix = ""
        verify_count = verify_queue.qsize()
        download_count = download_queue.qsize()
        if verify_count:
          prefix = "[ %d files left to verify ] " % verify_count
        if download_count:
          prefix = prefix + "[ %d files left to download ] " % download_count
        self.print(prefix + item.get('status', '') + ' ' + item['filename'])
        print_queue.task_done()
        if not verbose:
          time.sleep(0.3)

  class FileVerifier(threading.Thread):
    def __init__(self, *args, **kwargs):
      threading.Thread.__init__(self)
      self.daemon = True
    def run(self):
      while True:
        item = verify_queue.get()
        item['status'] = 'Verifying'
        print_queue.put(item)
        if os.path.exists(item['filename']) and file_md5(item['filename']) == item['checksum']:
          item['status'] = 'Verified'
        else:
          item['status'] = 'Downloading'
          download_queue.put(item)
        print_queue.put(item)
        verify_queue.task_done()

  class FileDownloader(threading.Thread):
    def __init__(self, *args, **kwargs):
      threading.Thread.__init__(self)
      self.daemon = True
    def run(self):
      while True:
        item = download_queue.get()
        dirname, filename = os.path.split(item['filename'])
        if dirname:
          try:
            os.makedirs(dirname)
          except:
            pass
        success = True
        try:
          download_to_file(item['url'], item['filename'])
          item['status'] = 'Downloaded'
          if file_md5(item['filename']) != item['checksum']:
            item['error'] = 'failed validation with hash mismatch'
            success = False
        except urllib2.HTTPError as e:
          item['error'] = str(e)
          success = False
        if not success:
          item['status'] = 'Error downloading'
          item['retry'] = item['retry'] + 1
          if item['retry'] < retry_limit:
            download_queue.put(item)
          else:
            errors.put(item)
        print_queue.put(item)
        download_queue.task_done()

  Printer().start()
  for n in range(download_threads):
    FileDownloader().start()
  for n in range(verify_threads):
    FileVerifier().start()

  file_count = 0
  index_url = 'http://dials.diamond.ac.uk/xia2/filelist-v2.dat'
  result = download_to_file(index_url, 'filelist-v2.dat')
  if result == -1:
    raise RuntimeError('Could not download file list.')

  with open('filelist-v2.dat') as fh:
    for record in fh:
      checksum = record[0:32]
      filename = record[34:].strip()
      url = 'http://dials.diamond.ac.uk/xia2/' + filename
      item = {'url': url, 'filename': filename, 'checksum': checksum, 'retry': 0}
      if os.path.exists(item['filename']):
        verify_queue.put(item)
      else:
        download_queue.put(item)
      file_count = file_count + 1

  def queue_join(q):
    '''Working around .join() blocking Ctrl+C'''
    term = threading.Thread(target=q.join)
    term.daemon = True
    term.start()
    while term.isAlive():
      term.join(3600)
  queue_join(verify_queue)
  queue_join(download_queue)
  queue_join(print_queue)
  print("\n")

  exit_code = 0
  try:
    while True:
      item = errors.get(False)
      print("""
Error downloading file {0[filename]}
                  from {0[url]}
                  due to {0[error]}
""".format(item))
      exit_code = 1
  except queue.Empty:
    pass
  if exit_code == 0:
    print("Download completed successfully.")
  sys.exit(exit_code)
