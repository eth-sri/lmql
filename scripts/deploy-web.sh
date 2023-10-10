set -e

REPO=lbeurerkellner/green-gold-dachshund-web

# # make sure there are no uncommitted changes
# if [ -n "$(git status --porcelain)" ]; then
#     echo "🚨  There are uncommitted changes. Please commit or stash them before deploying."
#     exit 1
# fi

mkdir -p ../web-deploy
rm -rf ../web-deploy/*

echo "🌎  Building website..."
pushd ../docs

# create docs/latest copy (skip symlink)
rm docs/latest # remove symlink
# create copy of current 'latest' state
cp -r docs docs-latest
# checkout old state for docs/
git fetch origin stable-docs --depth 1
git checkout origin/stable-docs docs
rm docs/latest
# move latest docs back in
mv docs-latest docs/latest
# build docs

# generate dynamic content
npm install 
npm run docs:build
# copy vitepress build
cp -r .vitepress/dist/* ../web-deploy/
# copy static content
cp -r lmql.svg ../web-deploy/
# undo docs/ checkout
rm -rf docs/latest
git checkout HEAD docs
popd

# copy playground
mkdir -p ../web-deploy/playground

echo "📦  Packaging LMQL for In-Browser use..."
echo $(pwd)
pushd browser-build
bash browser-build.sh
popd
cp -r browser-build/dist/wheels ../web-deploy/playground/
rm ../web-deploy/playground/wheels/.gitignore # remove gitignore to deploy .whl files to Pages
cp -r browser-build/dist/lmql.web.min.js ../web-deploy/playground/

echo "📦  Building playground..."
# create playground destination
mkdir -p ../web-deploy/playground
pushd ../src/lmql/ui/playground
# build playground
yarn
REACT_APP_WEB_BUILD=1 REACT_APP_BUILD_COMMIT=$(git rev-parse HEAD | cut -c1-7) yarn run build
popd

cp -r ../src/lmql/ui/playground/build/* ../web-deploy/playground/

# check for --push
if [ "$1" = "--push" ]; then
    echo "🚀  Deploying website to GitHub $REPO..."
    pushd ../web-deploy
    echo "lmql.ai" > CNAME
    npx gh-pages -d . -r git@github.com:$REPO.git -f
    popd
fi
