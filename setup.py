from setuptools import setup, find_packages


# Read the requirements.txt file
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="jobhunter",
    version="0.1",
    packages=find_packages(),
    install_requires=requirements,
    url="https://github.com/espin086/GPT-JobHunter",
    author="JJ Espinoza",
    author_email="jj.espinoza.la@gmail.com",
    description="A package that hunts for jobs",
)
