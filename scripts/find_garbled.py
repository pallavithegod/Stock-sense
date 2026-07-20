import re
fname='d:\\New3_Working_V3\\app.py'
with open(fname,encoding='utf-8',errors='ignore') as f:
    txt=f.read()
patterns=set(re.findall(r'Ã[^\s\"]*',txt))
for p in sorted(patterns):
    print(repr(p))
