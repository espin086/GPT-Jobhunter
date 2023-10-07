# Installation Guide

This guide will walk you through the installation process for the program. Please follow the steps below to ensure a successful installation.

## Prerequisites

Before proceeding with the installation, please make sure you have the following prerequisites:

- Access to a linux terminal (Mac or Ubuntu) or a WSL on Windows

## Step 0: Clone the repository
Clone the repository to your local environment.


## Step 1: Copy the .env-template

To begin, we need to copy the `.env-template` file into `.env` so that the program can work properly. Use the following command to accomplish this:

```shell
cp .env-template .env
```

## Step 2: Add your Rapid API Key

Next, open the `.env` file in a text editor and add your Rapid API Key. This key is required for the program to function correctly. If you don't have a Rapid API Key, you can sign up for one [here](https://www.rapidapi.com/).

## Step 3: Test the program

To ensure that everything is set up correctly, run the following command to run the tests:

```shell
make test
```

If there are no errors, then everything is working properly.

## Step 4: Create a Docker image

To create a Docker image, you need to run the appropriate Docker command on the Dockerfile. Make sure you have Docker installed on your system. If you don't have Docker installed, you can download it from the official website [here](https://www.docker.com/products/docker-desktop).

```shell
docker build -t jobhunter .
```

## Step 5: Create a container and pass the .env file

Finally, create a container from the Docker image and securely pass your secrets by using the local `.env` file as a variable. This will ensure that your secrets are securely passed to the container.



```shell
docker run --env-file .env -p 8501:8501 jobhunter
```

That's it! You have successfully installed the program. 

** You should be able to access the application in your browser by clicking **

```http://localhost:8501/```

If you encounter any issues during the installation process, please refer to the documentation or seek assistance from the support team.
