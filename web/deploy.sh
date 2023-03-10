set -e

REPO=lbeurerkellner/green-gold-dachshund-web

mkdir -p ../web-deploy
rm -rf ../web-deploy/*

echo "🌎  Building website..."
# generate dynamic content
node generate.js
# copy index.html
cp index.html ../web-deploy/
cp static/images/lmql.svg ../web-deploy/lmql.svg
# copy static content
cp -r static ../web-deploy/

echo "📦  Building playground..."
# create playground destination
mkdir -p ../web-deploy/playground
pushd ../src/lmql/ui/playground
# build playground
yarn
REACT_APP_WEB_BUILD=1 REACT_APP_BUILD_COMMIT=$(git rev-parse HEAD | cut -c1-7) yarn run build
popd
# copy playground
cp -r ../src/lmql/ui/playground/build/* ../web-deploy/playground/

echo "📦  Packaging LMQL for In-Browser use..."
echo $(pwd)
pushd browser-build
bash browser-build.sh
popd
cp -r browser-build/dist/wheels ../web-deploy/playground/
cp -r browser-build/dist/lmql.web.min.js ../web-deploy/playground/

# check for --push
if [ "$1" = "--push" ]; then
    echo "🚀  Deploying website to GitHub $REPO..."
    pushd ../web-deploy
    echo "lmql.ai" > CNAME
    npx gh-pages -d . -r git@github.com:$REPO.git -f
    popd
fi