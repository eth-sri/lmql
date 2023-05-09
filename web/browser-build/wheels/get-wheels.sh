if [ ! -f "astunparse-1.6.3-py2.py3-none-any.whl" ]; then
    wget https://files.pythonhosted.org/packages/2b/03/13dde6512ad7b4557eb792fbcf0c653af6076b81e5941d36ec61f7ce6028/astunparse-1.6.3-py2.py3-none-any.whl
fi

if [ ! -f "pydot-1.4.2-py2.py3-none-any.whl" ]; then
    wget https://files.pythonhosted.org/packages/ea/76/75b1bb82e9bad3e3d656556eaa353d8cd17c4254393b08ec9786ac8ed273/pydot-1.4.2-py2.py3-none-any.whl
fi

if [ ! -f "gpt3_tokenizer-0.1.3-py2.py3-none-any.whl" ]; then
    wget https://files.pythonhosted.org/packages/1e/a7/9b825973eb7933cec48dfdce0db81ef6e901971f6e8bb2c440617676e2c0/gpt3_tokenizer-0.1.3-py2.py3-none-any.whl
fi

pushd ../
bash package.sh openai
popd
