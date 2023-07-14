# fail if any commands fails
set -e

COMMIT=$(git rev-parse HEAD)
HAS_UNSTAGED=$(git diff-index --quiet HEAD -- src; echo $?)

if [ $HAS_UNSTAGED -eq 1 ]; then
    echo "Unstaged changes detected. Please commit or stash them before packaging for PyPI."
    echo $(git diff-index HEAD -- src)
    exit 1
fi

VERSION=$1
VERSION_BEFORE=$(cat src/lmql/version.py)
echo "version = \"$VERSION\"" > src/lmql/version.py
echo "commit = \"$COMMIT\"" >> src/lmql/version.py
echo "build_on = \"$(date)\"" >> src/lmql/version.py

echo "Building with version information: $(cat src/lmql/version.py)"

# replace line starting 'version = ' in setup.cfg
UPDATED_SETUP=$(sed "s/version = .*/version = $VERSION/" setup.cfg)
echo "$UPDATED_SETUP" > setup.cfg

# run and ignore failure
python -m build

echo "Reverting version.py to dev"
git checkout HEAD src/lmql/version.py