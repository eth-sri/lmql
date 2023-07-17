import os
import sys
import subprocess
import lmql

THIS_DIR = os.path.dirname(__file__)
files = sorted(os.listdir(THIS_DIR))
TEST_TIMEOUT = float(os.environ.get("TEST_TIMEOUT", 3*60.0))

errors = 0 
files = [f for f in files if f.startswith("test_")]

print(f"Testing LMQL distribution {lmql.__version__} at {lmql.__file__} with {len(files)} tests")

for i,f in enumerate(files):
    try:
        print(">", f"[{i+1}/{len(files)}]", f)

        cmd = "python " + os.path.join(THIS_DIR, f)
        timeout = TEST_TIMEOUT
        result = subprocess.call(cmd, shell=True, timeout=timeout)
        
        if result == 2:
            raise KeyboardInterrupt
        if result != 0:
            errors += 1
            if "--failearly" in sys.argv:
                break
    except subprocess.TimeoutExpired:
        print(">", f"[{i+1}/{len(files)}]", f, "timed out after", timeout, "seconds")
        sys.exit(1)

    except KeyboardInterrupt:
        sys.exit(1)

if errors != 0:
    sys.exit(1)
else:
    sys.exit(0)