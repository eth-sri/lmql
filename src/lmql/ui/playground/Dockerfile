# Pull the latest base image
FROM node:alpine
# set working directory
WORKDIR /app
# add `/app/node_modules/.bin` to $PATH
ENV PATH /app/node_modules/.bin:$PATH
# Copy package.json to /app
COPY package.json ./
# Copy package-lock.json to /app
COPY package-lock.json ./
# Install dependencies
RUN npm i
# add app
COPY . ./
# start app
CMD ["npm", "start"]