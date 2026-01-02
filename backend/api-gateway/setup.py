# backend/api-gateway/setup.py
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="goat-prediction-api",
    version="1.0.0",
    author="GOAT Prediction Team",
    author_email="dev@goat-prediction.com",
    description="GOAT Prediction Ultimate API Gateway",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/goat-prediction/ultimate",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Framework :: FastAPI",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.6.0",
            "pre-commit>=3.0.0",
        ],
        "ml": [
            "numpy>=1.24.0",
            "pandas>=2.0.0",
            "scikit-learn>=1.3.0",
        ],
        "monitoring": [
            "prometheus-client>=0.19.0",
            "structlog>=23.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "goat-api=src.cli:main",
        ],
    },
    include_package_data=True,
)
