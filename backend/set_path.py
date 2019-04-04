
import sys

paths = [
    '/workspace/'
]

for path in paths:
    if path not in sys.path:
        sys.path.append(path)
