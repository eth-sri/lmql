import os
import sys

THIS_DIR = os.path.dirname(__file__)
files = sorted(os.listdir(THIS_DIR))

errors = 0 
files = [f for f in files if f.startswith("test_")]

for i,f in enumerate(files):
    try:
        print(">", f"[{i+1}/{len(files)}]", f)
        result = os.system("python " + os.path.join(THIS_DIR, f))
        
        if result == 2:
            raise KeyboardInterrupt
        if result != 0:
            errors += 1

    except KeyboardInterrupt:
        sys.exit(1)

if errors != 0:
    sys.exit(1)
else:
    sys.exit(0)