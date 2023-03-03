from setuptools import setup, find_packages


setup(
    name='jobhunter',
    version='0.0.1',
    author='JJ Espinoza',
    description='Automated job discovery using machine learning',
    packages=find_packages(),
    install_requires=[
        'boto3',
        'brotlipy',
        'bs4',
        'certifi',
        'nltk',
        'numpy',
        'pyyaml',
        'pandas',
        'requests-oauthlib',
        'scipy',
        'scikit-learn',
    ],
)
