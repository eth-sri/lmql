import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=2223)
parser.add_argument('--gpus', type=str, default='all')
parser.add_argument('--transformers-cache', type=str, default='transformers-cache')
# all other args are passed to lmql-serve
args, _ = parser.parse_known_args()



PORT=2223
GPUS=all

sudo docker run \
    -p 2223:8899 \
    -e PORT=8899 \
    -e TRANSFORMERS_CACHE=/transformers \
    -it --gpus $GPUS \
    -v $(pwd)/transformers-cache:/transformers \
    lmql-serve --cuda $@
    