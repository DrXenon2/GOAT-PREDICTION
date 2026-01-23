#!/usr/bin/env python3
"""
Setup script for Goat Prediction Ultimate API Gateway.

This script configures the package for distribution and installation.
It handles dependencies, metadata, and entry points for the API Gateway.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.egg_info import egg_info
from setuptools.command.install import install
from setuptools.command.sdist import sdist


def get_version() -> str:
    """Extract version from pyproject.toml or VERSION file."""
    version_file = Path(__file__).parent / "pyproject.toml"
    
    if version_file.exists():
        content = version_file.read_text(encoding="utf-8")
        version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if version_match:
            return version_match.group(1)
    
    version_file = Path(__file__).parent / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    
    return "1.0.0"


def read_requirements(file_path: str) -> List[str]:
    """Read requirements from a file."""
    requirements_path = Path(__file__).parent / file_path
    
    if not requirements_path.exists():
        print(f"Warning: Requirements file {file_path} not found")
        return []
    
    requirements = []
    with open(requirements_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            # Handle -r references to other requirements files
            if line.startswith("-r "):
                referenced_file = line[3:].strip()
                requirements.extend(read_requirements(referenced_file))
                continue
            
            # Handle -c constraints
            if line.startswith("-c "):
                continue
            
            requirements.append(line)
    
    return requirements


def read_long_description() -> str:
    """Read long description from README.md."""
    readme_path = Path(__file__).parent / "README.md"
    
    if readme_path.exists():
        try:
            return readme_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: Could not read README.md: {e}")
    
    return "High-performance API Gateway for Goat Prediction Ultimate - Advanced Sports Betting AI Platform"


class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version."""
    
    description = "Verify that the git tag matches the package version"
    
    def run(self) -> None:
        tag = os.getenv("GIT_TAG", "").strip()
        version = get_version()
        
        if tag and tag != f"v{version}":
            sys.exit(
                f"ERROR: Git tag '{tag}' does not match package version '{version}'"
            )
        
        print(f"✓ Version verification passed: {version}")
        super().run()


class BuildCommand(build_py):
    """Custom build command."""
    
    def run(self) -> None:
        print("Building Goat Prediction API Gateway package...")
        
        # Create necessary directories
        self.mkpath(os.path.join(self.build_lib, "goat_prediction_api_gateway"))
        
        # Copy configuration files
        self.copy_file(
            "pyproject.toml",
            os.path.join(self.build_lib, "goat_prediction_api_gateway", "pyproject.toml")
        )
        
        super().run()


class SDistCommand(sdist):
    """Custom source distribution command."""
    
    def make_release_tree(self, base_dir: str, files: List[str]) -> None:
        super().make_release_tree(base_dir, files)
        
        # Create VERSION file in source distribution
        version_file = os.path.join(base_dir, "VERSION")
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(get_version())


class EggInfoCommand(egg_info):
    """Custom egg info command."""
    
    def run(self) -> None:
        # Ensure VERSION file exists
        version_file = Path(__file__).parent / "VERSION"
        if not version_file.exists():
            version_file.write_text(get_version(), encoding="utf-8")
        
        super().run()


def get_package_data() -> Dict[str, List[str]]:
    """Get package data configuration."""
    return {
        "goat_prediction_api_gateway": [
            "py.typed",
            "*.pyi",
            "**/*.pyi",
            "**/*.json",
            "**/*.yaml",
            "**/*.yml",
            "**/*.env",
            "**/*.ini",
            "**/*.cfg",
            "**/*.md",
            "**/*.txt",
            "**/*.html",
            "**/*.jinja2",
            "**/*.css",
            "**/*.js",
            "**/*.png",
            "**/*.svg",
            "**/*.sql",
        ]
    }


def get_data_files() -> List[Tuple[str, List[str]]]:
    """Get data files configuration."""
    base_dir = Path(__file__).parent
    
    data_files = []
    
    # Configuration files
    config_files = []
    config_dir = base_dir / "config"
    if config_dir.exists():
        for ext in ["*.yaml", "*.yml", "*.json", "*.env.example"]:
            config_files.extend([str(p) for p in config_dir.glob(ext)])
    
    if config_files:
        data_files.append(("share/goat-prediction/api-gateway/config", config_files))
    
    # Schema files
    schema_files = []
    schema_dir = base_dir / "schemas"
    if schema_dir.exists():
        for ext in ["*.json", "*.graphql"]:
            schema_files.extend([str(p) for p in schema_dir.glob(ext)])
    
    if schema_files:
        data_files.append(("share/goat-prediction/api-gateway/schemas", schema_files))
    
    # Template files
    template_files = []
    template_dir = base_dir / "templates"
    if template_dir.exists():
        for ext in ["*.html", "*.jinja2"]:
            template_files.extend([str(p) for p in template_dir.glob(ext)])
    
    if template_files:
        data_files.append(("share/goat-prediction/api-gateway/templates", template_files))
    
    # Static files
    static_files = []
    static_dir = base_dir / "static"
    if static_dir.exists():
        for ext in ["*.css", "*.js", "*.png", "*.svg"]:
            static_files.extend([str(p) for p in static_dir.glob(ext)])
    
    if static_files:
        data_files.append(("share/goat-prediction/api-gateway/static", static_files))
    
    # Migration files
    migration_files = []
    migration_dir = base_dir / "migrations"
    if migration_dir.exists():
        for ext in ["*.sql", "*.py"]:
            migration_files.extend([str(p) for p in migration_dir.glob(f"**/{ext}")])
    
    alembic_file = base_dir / "alembic.ini"
    if alembic_file.exists():
        migration_files.append(str(alembic_file))
    
    if migration_files:
        data_files.append(("share/goat-prediction/api-gateway/migrations", migration_files))
    
    return data_files


def main() -> None:
    """Main setup function."""
    
    # Get version
    version = get_version()
    
    # Read requirements
    install_requires = read_requirements("requirements.txt")
    dev_requires = read_requirements("requirements-dev.txt")
    
    # Define extras
    extras_require = {
        "dev": dev_requires,
        "test": read_requirements("requirements-test.txt"),
        "docs": read_requirements("requirements-docs.txt"),
        "performance": read_requirements("requirements-performance.txt"),
        "security": read_requirements("requirements-security.txt"),
        "monitoring": read_requirements("requirements-monitoring.txt"),
        "all": (
            dev_requires +
            read_requirements("requirements-test.txt") +
            read_requirements("requirements-docs.txt") +
            read_requirements("requirements-performance.txt") +
            read_requirements("requirements-security.txt") +
            read_requirements("requirements-monitoring.txt")
        ),
    }
    
    # Clean up empty extras
    extras_require = {k: v for k, v in extras_require.items() if v}
    
    # Entry points
    entry_points = {
        "console_scripts": [
            "goat-api = goat_prediction_api_gateway.main:main",
            "goat-api-dev = goat_prediction_api_gateway.main:dev",
            "goat-api-prod = goat_prediction_api_gateway.main:prod",
            "goat-api-test = goat_prediction_api_gateway.main:test",
            "goat-api-migrate = goat_prediction_api_gateway.cli.migrations:migrate",
            "goat-api-seed = goat_prediction_api_gateway.cli.seed:seed",
            "goat-api-health = goat_prediction_api_gateway.cli.health:health",
            "goat-api-monitor = goat_prediction_api_gateway.cli.monitor:monitor",
            "goat-api-backup = goat_prediction_api_gateway.cli.backup:backup",
        ],
        "fastapi.apps": [
            "api_gateway = goat_prediction_api_gateway.app:app",
        ],
        "goat_prediction.plugins": [
            "auth = goat_prediction_api_gateway.plugins.auth:AuthPlugin",
            "monitoring = goat_prediction_api_gateway.plugins.monitoring:MonitoringPlugin",
            "rate_limiting = goat_prediction_api_gateway.plugins.rate_limiting:RateLimitingPlugin",
            "caching = goat_prediction_api_gateway.plugins.caching:CachingPlugin",
        ],
    }
    
    # Package data
    package_data = get_package_data()
    
    # Data files
    data_files = get_data_files()
    
    # Setup configuration
    setup_params = {
        # Basic information
        "name": "goat-prediction-api-gateway",
        "version": version,
        "description": "High-performance API Gateway for Goat Prediction Ultimate - Advanced Sports Betting AI Platform",
        "long_description": read_long_description(),
        "long_description_content_type": "text/markdown",
        
        # Author information
        "author": "Goat Prediction Team",
        "author_email": "dev@goat-prediction.com",
        "maintainer": "Goat Prediction Engineering",
        "maintainer_email": "engineering@goat-prediction.com",
        
        # Project URLs
        "url": "https://github.com/goat-prediction/ultimate",
        "download_url": f"https://github.com/goat-prediction/ultimate/archive/v{version}.tar.gz",
        "project_urls": {
            "Documentation": "https://docs.goat-prediction.com",
            "Source": "https://github.com/goat-prediction/ultimate",
            "Tracker": "https://github.com/goat-prediction/ultimate/issues",
            "Changelog": f"https://github.com/goat-prediction/ultimate/releases/tag/v{version}",
            "Roadmap": "https://github.com/goat-prediction/ultimate/ROADMAP.md",
        },
        
        # Classifiers
        "classifiers": [
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Intended Audience :: Financial and Insurance Industry",
            "Intended Audience :: Science/Research",
            "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
            "Topic :: Scientific/Engineering :: Artificial Intelligence",
            "Topic :: Office/Business :: Financial :: Investment",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Programming Language :: Python :: 3 :: Only",
            "Programming Language :: Python :: Implementation :: CPython",
            "Framework :: FastAPI",
            "Environment :: Web Environment",
            "Natural Language :: English",
            "Typing :: Typed",
        ],
        
        # Keywords
        "keywords": [
            "sports-betting",
            "predictions",
            "machine-learning",
            "api-gateway",
            "fastapi",
            "high-performance",
            "real-time",
            "ai",
            "artificial-intelligence",
        ],
        
        # License
        "license": "MIT",
        "license_files": ["LICENSE"],
        
        # Platforms
        "platforms": ["any"],
        
        # Package configuration
        "packages": find_packages(where="src", include=["goat_prediction_api_gateway", "goat_prediction_api_gateway.*"]),
        "package_dir": {"": "src"},
        "include_package_data": True,
        "zip_safe": False,
        
        # Python requirements
        "python_requires": ">=3.11,<3.13",
        
        # Dependencies
        "install_requires": install_requires,
        "extras_require": extras_require,
        
        # Entry points
        "entry_points": entry_points,
        
        # Package data
        "package_data": package_data,
        
        # Data files
        "data_files": data_files,
        
        # Commands
        "cmdclass": {
            "build_py": BuildCommand,
            "egg_info": EggInfoCommand,
            "install": VerifyVersionCommand,
            "sdist": SDistCommand,
        },
    }
    
    # Run setup
    setup(**setup_params)


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 11):
        sys.exit("Error: Goat Prediction API Gateway requires Python 3.11 or higher")
    
    # Run main setup
    main()
