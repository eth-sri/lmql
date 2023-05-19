FROM python:latest

WORKDIR lmql
VOLUME ~/.lmql/
ARG GPU_ENABLED

HEALTHCHECK CMD curl --fail http://localhost:3000/ || exit 1

RUN apt-get update
RUN apt-get install -y curl
RUN curl -sL https://deb.nodesource.com/setup_18.x > node.sh
RUN chmod +x node.sh && ./node.sh
RUN apt-get install -y nodejs
RUN rm node.sh

RUN if [ "${GPU_ENABLED}" = "true" ]; then pip install accelerate lmql[hf]; else pip install lmql; fi
RUN if [ "${GPU_ENABLED}" = "true" ]; then apt-get install git && pip install git+https://github.com/huggingface/transformers; fi


CMD ["lmql", "playground"]
