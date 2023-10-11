from setuptools import setup, find_packages

# Read the content of requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="jobhunter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=requirements,  # List of dependencies read from requirements.txt
)
