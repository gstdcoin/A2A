from setuptools import setup, find_packages

setup(
    name="gstd_a2a",
    version="1.0.0",
    description="GSTD Autonomous Agent Protocol SDK",
    author="GSTD Foundation",
    packages=find_packages(),
    package_dir={'': 'python-sdk'},
    install_requires=[
        "requests",
        "mcp",
        "pydantic",
        "tonsdk",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
)
