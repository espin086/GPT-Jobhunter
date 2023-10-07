# Use the officinal Python runtime
FROM python:3.8.-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages using the Makefile
RUN make install

# Expose port 8000
EXPOSE 8000

# Run Application
RUN make run
