import argparse
import shlex
import subprocess
import os

def has_docker_image():
    cmd = ['docker', 'image', 'ls', '--format', '{{.Tag}}', 'lmql-serve']
    print(">", " ".join(shlex.quote(word) for word in cmd))
    return len(subprocess.check_output(cmd).strip()) > 0

def build_docker_image():
    ADDITIONAL_EXCLUDES = [
    ]
    cmd = ["docker", "build", "-t", "lmql-serve", "-f", "scripts/Dockerfile.serve", "."]
    print(">", " ".join(shlex.quote(word) for word in cmd))
    subprocess.run(cmd, check=True)

parser = argparse.ArgumentParser(description="""
                                 Runs 'lmql serve-model' in a docker container.

                                 This scripts passes all arguments to 'lmql serve-model' in the docker container, except for the following:
                                 """.strip())
parser.add_argument('--port', type=int, default=8080, help="Host port to expose the container's LMTP endpoint on. Default: 8080.")
parser.add_argument('--gpus', type=str, default='all', help="GPUs to use, e.g. --gpu all, passed to 'docker run'. Default: all.")
parser.add_argument('--transformers-cache', type=str, default='$HOME/.cache/huggingface/hub', help="Path to local directory to mount into the container as model cache.")
parser.add_argument('--rebuild', action='store_true', help="Forces rebuilding the docker image")
parser.add_argument('--extras', type=str, default='', help="Extra pip packages to install in the docker image before running lmql serve-model.")
# all other args are passed to lmql-serve
args, extra_positional_args = parser.parse_known_args()

if args.transformers_cache.startswith("$HOME"):
    # if homefolder exists, replace $HOME with ~
    if os.path.exists(os.path.expanduser("~")):
        args.transformers_cache = os.path.expanduser(args.transformers_cache.replace("$HOME", "~"))
    else:
        # otherwise, replace $HOME with current directory
        args.transformers_cache = args.transformers_cache.replace("$HOME", ".")

if not has_docker_image() or args.rebuild:
    build_docker_image()

script = r"""
exec docker run \
    -p "$port:8899" \
    -e TRANSFORMERS_CACHE=/transformers ${extras:+ -e EXTRA_PIP_PACKAGES="$extras"} \
    -it --gpus "$gpus" \
    -v "$cache:/transformers" \
    lmql-serve "$@"
"""

subprocess.run(
    ["bash", "-c", script, "bash"] + extra_positional_args,
    env=dict(os.environ,
        gpus=str(args.gpus),
        port=str(args.port),
        cache=str(args.transformers_cache),
        extras=str(args.extras)
    ))
