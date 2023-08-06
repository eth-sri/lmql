import argparse
import os

def has_docker_image():
    cmd = """sudo docker image ls | grep lmql-serve"""
    print(">", cmd)
    return os.system(cmd) == 0

def build_docker_image():
    cmd = """sudo docker build -t lmql-serve -f Dockerfile.serve ."""
    print(">", cmd)
    os.system(cmd)

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=2223, help='Host port to expose the LMTP endpoint on')
parser.add_argument('--gpus', type=str, default='all', help="GPUs to use, e.g. --gpu all, passed to 'docker run'")
parser.add_argument('--transformers-cache', type=str, default='$HOME/.cache/huggingface/hub', help="Path to local directory to cache downloaded transformers models.")
# all other args are passed to lmql-serve
args, _ = parser.parse_known_args()

if args.transformers_cache.startswith("$HOME"):
    # if homefolder exists, replace $HOME with ~
    if os.path.exists(os.path.expanduser("~")):
        args.transformers_cache = os.path.expanduser(args.transformers_cache.replace("$HOME", "~"))
    else:
        # otherwise, replace $HOME with current directory
        args.transformers_cache = args.transformers_cache.replace("$HOME", ".")

if not has_docker_image():
    build_docker_image()

PORT=2223
GPUS=all

cmd = """sudo docker run \\
    -p $PORT:8899 \\
    -e PORT=8899 \\
    -e TRANSFORMERS_CACHE=/transformers \\
    -it --gpus $GPUS \\
    -v $CACHE:/transformers \\
    lmql-serve --cuda $@
""".replace("$GPUS", args.gpus).replace("$PORT", str(args.port)).replace("$@", " ".join(_)).replace("$CACHE", args.transformers_cache)

print(">", cmd)
os.system(cmd)