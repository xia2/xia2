import json
import sys

result = { }

for arg in sys.argv[1:]:
    result.update(json.load(open(arg, 'r')))

print json.dumps(result)
