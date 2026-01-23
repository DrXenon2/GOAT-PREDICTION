"""
Environment configuration and validation.
"""

import os
import sys
from typing import Dict, Any
from pathlib import Path

from .settings import settings


def load_environment(env_file: str = None) -> None:
    """
    Load environment variables from file.
    
    Args:
        env_file: Path to .env file
    """
    if env_file is None:
        # Try to find .env file in parent directories
        current_dir = Path(__file__).parent.parent.parent
        possible_paths = [
            current_dir / ".env",
            current_dir.parent / ".env",
            current_dir.parent.parent / ".env",
        ]
        
        for path in possible_paths:
            if path.exists():
                env_file = str(path)
                break
    
    if env_file and os.path.exists(env_file):
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"Loaded environment from: {env_file}")
    else:
        print("No .env file found, using system environment variables")


def validate_environment() -> Dict[str, Any]:
    """
    Validate that all required environment variables are set.
    
    Returns:
        Dict with validation results
    """
    validation_results = {
        "database": {
            "required": ["POSTGRES_SERVER", "POSTGRES_USER", "POSTGRES_DB"],
            "missing": [],
            "status": "OK"
        },
        "redis": {
            "required": ["REDIS_HOST", "REDIS_PORT"],
            "missing": [],
            "status": "OK"
        },
        "security": {
            "required": ["SECRET_KEY"],
            "missing": [],
            "status": "OK"
        },
        "external_apis": {
            "recommended": ["STATSBOMB_API_KEY", "OPTA_API_KEY", "SPORTRADAR_API_KEY"],
            "missing": [],
            "status": "WARNING"
        }
    }
    
    # Check database
    for var in validation_results["database"]["required"]:
        if not os.getenv(var):
            validation_results["database"]["missing"].append(var)
    
    if validation_results["database"]["missing"]:
        validation_results["database"]["status"] = "ERROR"
    
    # Check Redis
    for var in validation_results["redis"]["required"]:
        if not os.getenv(var):
            validation_results["redis"]["missing"].append(var)
    
    if validation_results["redis"]["missing"]:
        validation_results["redis"]["status"] = "ERROR"
    
    # Check security
    if not os.getenv("SECRET_KEY") or os.getenv("SECRET_KEY") == "your-secret-key-here":
        validation_results["security"]["missing"].append("SECRET_KEY")
        validation_results["security"]["status"] = "ERROR"
    
    # Check external APIs (warnings only)
    for var in validation_results["external_apis"]["recommended"]:
        if not os.getenv(var):
            validation_results["external_apis"]["missing"].append(var)
    
    if validation_results["external_apis"]["missing"]:
        validation_results["external_apis"]["status"] = "WARNING"
    
    return validation_results


def print_environment_summary() -> None:
    """Print environment configuration summary."""
    print("\n" + "="*60)
    print("GOAT PREDICTION - ENVIRONMENT CONFIGURATION")
    print("="*60)
    
    print(f"\n📋 Application:")
    print(f"   Name: {settings.APP_NAME}")
    print(f"   Version: {settings.APP_VERSION}")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Debug: {settings.DEBUG}")
    
    print(f"\n🗄️  Database:")
    print(f"   URL: {settings.get_database_url()}")
    
    print(f"\n🔐 Security:")
    print(f"   JWT Algorithm: {settings.ALGORITHM}")
    print(f"   Token Expiry: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} min")
    print(f"   CORS Origins: {len(settings.CORS_ORIGINS)} configured")
    
    print(f"\n⚡ Performance:")
    print(f"   Cache Enabled: {settings.CACHE_ENABLED}")
    print(f"   Rate Limiting: {settings.RATE_LIMIT_ENABLED}")
    print(f"   Max Workers: {settings.MAX_WORKERS}")
    
    print(f"\n🔗 External Services:")
    print(f"   Prediction Engine: {settings.PREDICTION_ENGINE_URL}")
    print(f"   User Service: {settings.USER_SERVICE_URL}")
    print(f"   Auth Service: {settings.AUTH_SERVICE_URL}")
    
    print(f"\n🚀 Feature Flags:")
    enabled_flags = [k for k, v in settings.FEATURE_FLAGS.items() if v]
    disabled_flags = [k for k, v in settings.FEATURE_FLAGS.items() if not v]
    
    print(f"   Enabled: {', '.join(enabled_flags[:5])}")
    if len(enabled_flags) > 5:
        print(f"            ... and {len(enabled_flags) - 5} more")
    
    if disabled_flags:
        print(f"   Disabled: {', '.join(disabled_flags[:3])}")
        if len(disabled_flags) > 3:
            print(f"             ... and {len(disabled_flags) - 3} more")
    
    print("\n" + "="*60)
    
    # Validate environment
    validation = validate_environment()
    
    print("\n🔍 Environment Validation:")
    for category, result in validation.items():
        status_emoji = "✅" if result["status"] == "OK" else "⚠️" if result["status"] == "WARNING" else "❌"
        print(f"   {status_emoji} {category.capitalize()}: {result['status']}")
        if result["missing"]:
            print(f"      Missing: {', '.join(result['missing'])}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Load environment and print summary
    load_environment()
    print_environment_summary()
    
    # Exit with error if validation fails
    validation = validate_environment()
    has_errors = any(result["status"] == "ERROR" for result in validation.values())
    
    if has_errors:
        print("\n❌ Environment validation failed!")
        sys.exit(1)
    else:
        print("\n✅ Environment validation passed!")
