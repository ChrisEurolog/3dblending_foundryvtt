import urllib.request
import re

try:
    url = "https://raw.githubusercontent.com/xNormal/xNormal-Docs/master/Batch%20XML%20Format.md"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    print(urllib.request.urlopen(req).read().decode('utf-8'))
except:
    pass
