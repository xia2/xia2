import base64
from dials.util.procrunner import run_process
import json
import xia2.XIA2Version

token = base64.b64decode('eGlhMnN1cHBvcnQ6MWY5MzI4NWRhMDBhMGM3MDZkZjVkY2FiNWU0ZTY4YWNhMmJmYjIxNQ==')
report = { 'public': 'false', 'files': {} }
report['description'] = '%s automated bug report' % xia2.XIA2Version.Version
for filename in ['xia2.error', 'xia2-debug.txt', 'xia2.txt']:
  with open(filename, 'r') as fh:
    report['files'][filename] = { 'content': fh.read() }

result = run_process(['curl', '-u', token, 'https://api.github.com/gists', '-d', '@-'], stdin = json.dumps(report))
if result['exitcode'] == 0:
  print "Bug report submitted"
else:
  print "Could not submit bug report"
