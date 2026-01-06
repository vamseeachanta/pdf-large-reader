"""
ABOUTME: Setup configuration for pdf-large-reader package
ABOUTME: Defines package metadata, dependencies, and CLI entry points
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split("\n")
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith("#")]

setup(
    name="pdf-large-reader",
    version="1.3.0",
    author="Workspace Hub",
    author_email="noreply@workspace-hub.dev",
    description="Memory-efficient PDF processing library for large files (100MB+, 1000+ pages)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/workspace-hub/pdf-large-reader",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business",
        "Topic :: Text Processing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.1",
        ],
        "progress": [
            "tqdm>=4.65.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pdf-large-reader=src.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "pdf",
        "large-files",
        "memory-efficient",
        "streaming",
        "extraction",
        "text-extraction",
        "image-extraction",
        "table-extraction",
        "ai-fallback",
    ],
    project_urls={
        "Bug Reports": "https://github.com/workspace-hub/pdf-large-reader/issues",
        "Source": "https://github.com/workspace-hub/pdf-large-reader",
        "Documentation": "https://github.com/workspace-hub/pdf-large-reader/blob/main/README.md",
    },
)
