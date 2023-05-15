FROM python:latest

WORKDIR lmql
VOLUME ~/.lmql/
ARG GPU_ENABLED

RUN apt-get update
RUN apt-get install -y curl
RUN curl -sL https://deb.nodesource.com/setup_18.x > node.sh
RUN chmod +x node.sh && ./node.sh
RUN apt-get install -y nodejs
RUN rm node.sh

RUN if [ "${GPU_ENABLED}" = "true" ]; then pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118; fi
RUN if [ "${GPU_ENABLED}" = "true" ]; then apt-get install git && pip install git+https://github.com/huggingface/transformers; fi
RUN pip install lmql


CMD ["lmql", "playground"]
