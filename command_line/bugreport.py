import base64
import json
import urllib2
import xia2.XIA2Version

token = 'eGlhMnN1cHBvcnQ6MWY5MzI4NWRhMDBhMGM3MDZkZjVkY2FiNWU0ZTY4YWNhMmJmYjIxNQ=='

report = { 'public': 'false', 'files': {} }
report['description'] = '%s automated bug report' % xia2.XIA2Version.Version
for filename in ['xia2.error', 'xia2-debug.txt', 'xia2.txt']:
  with open(filename, 'r') as fh:
    report['files'][filename] = { 'content': fh.read() }

post_data = json.dumps(report)
url_request = urllib2.Request('https://api.github.com/gists', post_data)
url_request.add_header("Authorization", "Basic %s" % token)

socket = urllib2.urlopen(url_request)
if socket.getcode() == 201:
  print "Bug report submitted"
else:
  print socket.info()
  print "\nCould not submit bug report"
