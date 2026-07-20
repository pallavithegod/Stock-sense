# print lines from app.py that contain non-ascii bytes along with their index
import sys
path = r'd:\\New3_Working_V3\\app.py'
with open(path, 'rb') as f:
    for i, line in enumerate(f, start=1):
        if any(b > 127 for b in line):
            print(i, line[:200])
