from setuptools import setup, find_packages

setup(
    name="allma",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "torch",
        "numpy",
        "pytest",
        "dataclasses",
        "typing",
    ],
    python_requires=">=3.7",
)
