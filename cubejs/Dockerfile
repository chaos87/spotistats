# Use an appropriate Node.js base image
FROM node:20-slim

# Set the working directory
WORKDIR /usr/src/app

# Copy package.json and install dependencies
# We assume npm is used. If a package-lock.json was available, it should be copied too.
COPY package.json ./
RUN npm cache clean --force && npm install

# Copy the Cube.js project files
# Copy model directory, cube.js, and any other necessary configuration files.
COPY model/ ./model/
COPY cube.js ./cube.js
# If there are other essential files like .env for default non-sensitive values, copy them too.
# For now, we'll only copy model/ and cube.js as essential.

# Expose the default Cube.js port
EXPOSE 4000

# Define the command to start the Cube.js server
# This is based on the "dev" script in package.json
CMD [ "npm", "start" ]
