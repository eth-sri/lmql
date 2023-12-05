import os
import sys
import subprocess
import lmql

def run_tests(directory):
    files = sorted(os.listdir(directory))
    TEST_TIMEOUT = float(os.environ.get("TEST_TIMEOUT", 3*60.0))

    errors = 0 
    files = [f for f in files if f.startswith("test_")]

    print(f"Testing LMQL distribution {lmql.__version__} at {lmql.__file__} with {len(files)} in {directory}", flush=True)

    for i,f in enumerate(files):
        try:
            print(">", f"[{i+1}/{len(files)}]", f, flush=True)

            cmd = [sys.executable, os.path.join(directory, f)]
            timeout = TEST_TIMEOUT
            result = subprocess.call(cmd, timeout=timeout)
            
            if result == 2:
                raise KeyboardInterrupt
            if result != 0:
                errors += 1
                print(">", f"[{i+1}/{len(files)}]", f, "failed", flush=True)
                if "--failearly" in sys.argv:
                    break
        except subprocess.TimeoutExpired:
            print(">", f"[{i+1}/{len(files)}]", f, "timed out after", timeout, "seconds")
            return 1

        except KeyboardInterrupt:
            return 1

    if errors != 0:
        return 1
    else:
        return 

if __name__ == "__main__":
    THIS_DIR = os.path.dirname(__file__)

    # if you want to run only some targets, pass them as 'only' arguments, e.g. 'python all.py only openai'
    if "only" in sys.argv:
        targets = []
    else:
        targets = [THIS_DIR]

    # default is the explicit name for .
    if "default" in sys.argv:
        targets.append(THIS_DIR)
    
    include_all_optional = "optional" in sys.argv

    optional_targets = os.listdir(os.path.join(THIS_DIR, "optional"))
    optional_targets = [t for t in optional_targets if os.path.isdir(os.path.join(THIS_DIR, "optional", t)) and (t in sys.argv or include_all_optional)]
    optional_targets = [os.path.join(THIS_DIR, "optional", t) for t in optional_targets]

    targets = sorted(set(targets + optional_targets))

    exit_codes = []

    for t in targets:
        exit_codes += [run_tests(t)]
    
    if any(exit_codes):
        sys.exit(1)
    else:
        sys.exit(0)