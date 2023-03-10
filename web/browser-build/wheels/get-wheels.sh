if [ ! -f "astunparse-1.6.3-py2.py3-none-any.whl" ]; then
    wget https://files.pythonhosted.org/packages/2b/03/13dde6512ad7b4557eb792fbcf0c653af6076b81e5941d36ec61f7ce6028/astunparse-1.6.3-py2.py3-none-any.whl
fi
# d24e46166555fe1917398f6d7c016dad
echo "d24e46166555fe1917398f6d7c016dad astunparse-1.6.3-py2.py3-none-any.whl" | md5sum -c

if [ ! -f "pydot-1.4.2-py2.py3-none-any.whl" ]; then
    wget https://files.pythonhosted.org/packages/ea/76/75b1bb82e9bad3e3d656556eaa353d8cd17c4254393b08ec9786ac8ed273/pydot-1.4.2-py2.py3-none-any.whl
    # 07598e9e7488926d7312640aacd22599
fi
echo "07598e9e7488926d7312640aacd22599 pydot-1.4.2-py2.py3-none-any.whl" | md5sum -c

pushd ../
bash package.sh openai
popd
