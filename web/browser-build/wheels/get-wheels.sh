if [ ! -f "astunparse-1.6.3-py2.py3-none-any.whl" ]; then
    wget https://files.pythonhosted.org/packages/2b/03/13dde6512ad7b4557eb792fbcf0c653af6076b81e5941d36ec61f7ce6028/astunparse-1.6.3-py2.py3-none-any.whl
fi

if [ ! -f "comma-fix.zip" ]; then
    # get GH https://github.com/lbeurerkellner/gpt3-tokenizer/archive/refs/heads/comma-fix.zip
    wget https://github.com/lbeurerkellner/gpt3-tokenizer/archive/refs/heads/comma-fix.zip
fi
# unzip comma-fix.zip
unzip comma-fix.zip
# make new archive with gpt3-tokenizer-comma-fix/* files
pushd gpt3-tokenizer-comma-fix
zip -r ../gpt3-tokenizer.zip *
popd

pushd ../
bash package.sh openai
popd
