from setuptools import find_packages, setup

setup(
    name="regulatory-reporting",
    version="1.4.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11",
)
