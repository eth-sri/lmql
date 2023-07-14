if [ "$2" == "--production" ]; then
    echo "[WARNING] Uploading to production PyPI"
    echo "Source Distribution"
    python -m twine upload dist/$1.tar.gz -u $TWINE_USERNAME -p $TWINE_PASSWORD
    echo "Wheel Distribution"
    python -m twine upload dist/$1-py3-none-any.whl -u $TWINE_USERNAME -p $TWINE_PASSWORD
else
    echo "Uploading to test.pypi.org"
    echo "Source Distribution"
    python -m twine upload --repository testpypi dist/$1.tar.gz -u $TWINE_USERNAME -p $TWINE_PASSWORD
    echo "Wheel Distribution"
    python -m twine upload --repository testpypi dist/$1-py3-none-any.whl -u $TWINE_USERNAME -p $TWINE_PASSWORD
fi
