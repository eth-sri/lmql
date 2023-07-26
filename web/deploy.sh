set -e

REPO=lbeurerkellner/green-gold-dachshund-web

mkdir -p ../web-deploy
rm -rf ../web-deploy/*

echo "🌎  Building website..."
# generate dynamic content
npm install 
node generate.js
# copy index.html
cp index.html ../web-deploy/
cp index-next.html ../web-deploy/
cp static/images/lmql.svg ../web-deploy/lmql.svg
# copy static content
cp -r static ../web-deploy/
cp -r try ../web-deploy/

# build actions/
pushd actions
node generate.js
popd
mkdir -p ../web-deploy/actions
cp -r actions/index.html ../web-deploy/actions/index.html
cp -r actions/*.css ../web-deploy/actions/

# build chat/
mkdir -p ../web-deploy/chat
cp -r chat/index.html ../web-deploy/chat/index.html
cp -r chat/send.svg ../web-deploy/chat/send.svg
cp -r chat/studio-screenshot.png ../web-deploy/chat/studio-screenshot.png

# build blog
pushd blog
node generate.js
popd
# sync all *.html files except index.template.html 
rsync -av --exclude="index.template.html" blog/*.html ../web-deploy/blog/

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

# copy documentation snippets
echo "📦  Copying documentation snippets..."
pushd ../docs
# check if any doc-snippets exist at all (check for *)
if [ -n "$(ls -A build/html/doc-snippets/*)" ]; then
    cp -r build/html/doc-snippets/* ../web-deploy/playground/doc-snippets/
fi
popd

echo "📦  Packaging LMQL for In-Browser use..."
echo $(pwd)
pushd browser-build
bash browser-build.sh
popd
cp -r browser-build/dist/wheels ../web-deploy/playground/
rm ../web-deploy/playground/wheels/.gitignore # remove gitignore to deploy .whl files to Pages
cp -r browser-build/dist/lmql.web.min.js ../web-deploy/playground/

# check for --push
if [ "$1" = "--push" ]; then
    echo "🚀  Deploying website to GitHub $REPO..."
    pushd ../web-deploy
    echo "lmql.ai" > CNAME
    npx gh-pages -d . -r git@github.com:$REPO.git -f
    popd
fi
