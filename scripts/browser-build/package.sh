# show output
set -x

if [ "$1" = "lmql" ]; then
    cd temp
    rm -rf lmql-package
    rsync -rd --exclude=".git/*" --exclude="*__pycache__*" --exclude="*node_modules*" --exclude="*evaluation*" --exclude="*playground*" ../../../src/ lmql-package
    cd lmql-package
    tar --exclude=lmql.tar.gz -czf lmql.tar.gz .
    cp lmql.tar.gz ../../wheels/
elif [ "$1" = "openai" ]; then
    cd shim/openai-shim
    tar --exclude=openai.tar.gz -czf openai-shim.tar.gz .
    cp openai-shim.tar.gz ../../wheels/
else
    echo "Usage: package.sh lmql|openai"
fi