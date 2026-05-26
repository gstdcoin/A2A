from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="gstd-a2a",
    version="2.0.0",
    description="GSTD Agent-to-Agent Protocol SDK — connect any AI agent to the GSTD compute network",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="GSTD Foundation",
    author_email="dev@gstdtoken.com",
    url="https://github.com/gstdcoin/A2A",
    project_urls={
        "Dashboard": "https://app.gstdtoken.com",
        "Documentation": "https://github.com/gstdcoin/A2A/blob/master/AGENTS.md",
        "Bug Tracker": "https://github.com/gstdcoin/A2A/issues",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.28.0",
        "pydantic>=2.0",
        "pynacl>=1.5.0",
        "aiohttp>=3.9.0",
        "typing_extensions>=4.5.0",
    ],
    extras_require={
        "ton": ["tonsdk>=1.0.12"],
        "mcp": ["mcp>=0.1.0", "uvicorn>=0.20.0"],
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "pytest-cov>=4.0",
            "mypy>=1.0",
            "bandit>=1.7",
            "types-requests",
        ],
        "full": ["tonsdk>=1.0.12", "mcp>=0.1.0", "uvicorn>=0.20.0"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "gstd-node=gstd_a2a.agent:main",
            "gstd-a2a-mcp=gstd_a2a.main:run",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
