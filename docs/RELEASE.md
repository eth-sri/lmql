# LMQL PyPI Release

To distribute a new LMQL release run the following commands in the project root.

```
# prepare source and whl archive in dist/ folder (requires 'python -m build' command)
bash scripts/wheel.sh <VERSION>

# upload resulting archives to PyPI
bash scripts/pypi-release.sh lmql-<VERSION>
```

Append `--production` to the `pypi-release.sh` script to push the artifacts to the actual 
PyPI index and not just the test.pypi.org.