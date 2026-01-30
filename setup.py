from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="satellite-downloader",
    version="1.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Download satellite imagery and maps from multiple free sources and export as GeoTIFF",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/satellite-downloader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "rasterio>=1.3.0",
        "pillow>=10.0.0",
        "numpy>=1.24.0",
        "requests>=2.31.0",
        "click>=8.1.0",
        "tqdm>=4.65.0",
    ],
    entry_points={
        "console_scripts": [
            "satellite-download=satellite_downloader.cli:main",
        ],
    },
)
