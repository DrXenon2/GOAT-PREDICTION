"""
Helpers Module
General helper utilities for API Gateway
"""

import hashlib
import secrets
import string
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Helper:
    """Base helper class with common utility methods"""
    
    @staticmethod
    def get_nested(data: dict, path: str, default: Any = None, separator: str = '.') -> Any:
        """
        Get value from nested dictionary using dot notation
        
        Args:
            data: Dictionary to search
            path: Dot-notation path (e.g., 'user.profile.name')
            default: Default value if path not found
            separator: Path separator
            
        Returns:
            Value at path or default
        """
        keys = path.split(separator)
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value


def generate_id(prefix: str = '', length: int = 16, uppercase: bool = False) -> str:
    """
    Generate unique ID
    
    Args:
        prefix: Optional prefix
        length: Length of random part
        uppercase: Use uppercase letters
        
    Returns:
        Generated ID
    """
    # Generate random hex string
    random_part = secrets.token_hex(length // 2)
    
    if uppercase:
        random_part = random_part.upper()
    
    if prefix:
        return f"{prefix}_{random_part}"
    
    return random_part


def generate_uuid(version: int = 4) -> str:
    """
    Generate UUID
    
    Args:
        version: UUID version (1 or 4)
        
    Returns:
        UUID string
    """
    if version == 1:
        return str(uuid.uuid1())
    else:
        return str(uuid.uuid4())


def generate_token(length: int = 32, url_safe: bool = True) -> str:
    """
    Generate secure random token
    
    Args:
        length: Token length
        url_safe: Use URL-safe characters
        
    Returns:
        Random token
    """
    if url_safe:
        return secrets.token_urlsafe(length)
    else:
        return secrets.token_hex(length)


def generate_slug(
    text: str,
    max_length: int = 50,
    separator: str = '-',
    lowercase: bool = True
) -> str:
    """
    Generate URL-friendly slug from text
    
    Args:
        text: Text to slugify
        max_length: Maximum slug length
        separator: Word separator
        lowercase: Convert to lowercase
        
    Returns:
        Slug string
    """
    # Remove special characters
    slug = re.sub(r'[^\w\s-]', '', text)
    
    # Replace whitespace with separator
    slug = re.sub(r'[\s_]+', separator, slug)
    
    # Remove duplicate separators
    slug = re.sub(f'{separator}+', separator, slug)
    
    # Convert to lowercase
    if lowercase:
        slug = slug.lower()
    
    # Trim to max length
    slug = slug[:max_length]
    
    # Remove leading/trailing separators
    slug = slug.strip(separator)
    
    return slug


def generate_password(
    length: int = 16,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_digits: bool = True,
    include_special: bool = True
) -> str:
    """
    Generate random password
    
    Args:
        length: Password length
        include_uppercase: Include uppercase letters
        include_lowercase: Include lowercase letters
        include_digits: Include digits
        include_special: Include special characters
        
    Returns:
        Generated password
    """
    characters = ''
    
    if include_uppercase:
        characters += string.ascii_uppercase
    if include_lowercase:
        characters += string.ascii_lowercase
    if include_digits:
        characters += string.digits
    if include_special:
        characters += string.punctuation
    
    if not characters:
        characters = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(characters) for _ in range(length))


def paginate(
    items: List[Any],
    page: int = 1,
    per_page: int = 10
) -> Dict[str, Any]:
    """
    Paginate list of items
    
    Args:
        items: List to paginate
        page: Page number (1-indexed)
        per_page: Items per page
        
    Returns:
        Pagination result dictionary
    """
    total = len(items)
    total_pages = (total + per_page - 1) // per_page
    
    # Ensure page is in valid range
    page = max(1, min(page, total_pages or 1))
    
    # Calculate slice indices
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        'items': items[start:end],
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None
    }


def calculate_hash(
    data: Union[str, bytes],
    algorithm: str = 'sha256',
    encoding: str = 'utf-8'
) -> str:
    """
    Calculate hash of data
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
        encoding: String encoding
        
    Returns:
        Hash hexdigest
    """
    if isinstance(data, str):
        data = data.encode(encoding)
    
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    
    return hash_obj.hexdigest()


def verify_hash(
    data: Union[str, bytes],
    hash_value: str,
    algorithm: str = 'sha256',
    encoding: str = 'utf-8'
) -> bool:
    """
    Verify data hash
    
    Args:
        data: Data to verify
        hash_value: Expected hash value
        algorithm: Hash algorithm
        encoding: String encoding
        
    Returns:
        True if hash matches
    """
    calculated = calculate_hash(data, algorithm, encoding)
    return calculated == hash_value


def sanitize_string(
    text: str,
    remove_html: bool = True,
    remove_scripts: bool = True,
    max_length: Optional[int] = None
) -> str:
    """
    Sanitize string by removing potentially dangerous content
    
    Args:
        text: Text to sanitize
        remove_html: Remove HTML tags
        remove_scripts: Remove script tags
        max_length: Maximum length
        
    Returns:
        Sanitized string
    """
    if not text:
        return text
    
    # Remove null bytes
    sanitized = text.replace('\x00', '')
    
    # Remove script tags
    if remove_scripts:
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML tags
    if remove_html:
        sanitized = re.sub(r'<[^>]+>', '', sanitized)
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def truncate_string(
    text: str,
    length: int,
    suffix: str = '...',
    word_boundary: bool = True
) -> str:
    """
    Truncate string to specified length
    
    Args:
        text: Text to truncate
        length: Maximum length
        suffix: Suffix to add if truncated
        word_boundary: Truncate at word boundary
        
    Returns:
        Truncated string
    """
    if len(text) <= length:
        return text
    
    truncated = text[:length - len(suffix)]
    
    if word_boundary:
        # Find last space
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]
    
    return truncated + suffix


def parse_query_params(query_string: str) -> Dict[str, Any]:
    """
    Parse query string into dictionary
    
    Args:
        query_string: Query string
        
    Returns:
        Dictionary of parameters
    """
    from urllib.parse import parse_qs, unquote
    
    params = {}
    
    if not query_string:
        return params
    
    # Remove leading ?
    if query_string.startswith('?'):
        query_string = query_string[1:]
    
    parsed = parse_qs(query_string)
    
    for key, values in parsed.items():
        # If single value, don't use list
        if len(values) == 1:
            params[key] = unquote(values[0])
        else:
            params[key] = [unquote(v) for v in values]
    
    return params


def merge_dicts(*dicts: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
    """
    Merge multiple dictionaries
    
    Args:
        *dicts: Dictionaries to merge
        deep: Deep merge nested dictionaries
        
    Returns:
        Merged dictionary
    """
    result = {}
    
    for d in dicts:
        if not deep:
            result.update(d)
        else:
            for key, value in d.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value, deep=True)
                else:
                    result[key] = value
    
    return result


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks
    
    Args:
        items: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def deduplicate_list(items: List[Any], key: Optional[callable] = None) -> List[Any]:
    """
    Remove duplicates from list while preserving order
    
    Args:
        items: List to deduplicate
        key: Optional function to extract comparison key
        
    Returns:
        Deduplicated list
    """
    seen = set()
    result = []
    
    for item in items:
        item_key = key(item) if key else item
        
        # Handle unhashable types
        try:
            if item_key not in seen:
                seen.add(item_key)
                result.append(item)
        except TypeError:
            # For unhashable types, use linear search
            if item not in result:
                result.append(item)
    
    return result


def retry_on_exception(
    func: callable,
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple = (Exception,)
) -> Any:
    """
    Retry function on exception
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Delay between retries (seconds)
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Function result
    """
    import time
    
    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries - 1:
                raise
            
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)


def memoize(func: callable) -> callable:
    """
    Memoization decorator
    
    Args:
        func: Function to memoize
        
    Returns:
        Memoized function
    """
    cache = {}
    
    def wrapper(*args, **kwargs):
        # Create cache key
        key = str(args) + str(kwargs)
        
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        
        return cache[key]
    
    return wrapper


def timing_decorator(func: callable) -> callable:
    """
    Decorator to measure function execution time
    
    Args:
        func: Function to time
        
    Returns:
        Wrapped function
    """
    import time
    
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        
        logger.debug(f"{func.__name__} took {(end - start) * 1000:.2f}ms")
        
        return result
    
    return wrapper


def get_client_ip(request) -> Optional[str]:
    """
    Get client IP address from request
    
    Args:
        request: Request object
        
    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header
    forwarded_for = getattr(request, 'headers', {}).get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    # Check X-Real-IP header
    real_ip = getattr(request, 'headers', {}).get('X-Real-IP')
    if real_ip:
        return real_ip
    
    # Fallback to client host
    if hasattr(request, 'client') and request.client:
        return request.client.host
    
    return None


# Export all
__all__ = [
    'Helper',
    'generate_id',
    'generate_uuid',
    'generate_token',
    'generate_slug',
    'generate_password',
    'paginate',
    'calculate_hash',
    'verify_hash',
    'sanitize_string',
    'truncate_string',
    'parse_query_params',
    'merge_dicts',
    'chunk_list',
    'deduplicate_list',
    'retry_on_exception',
    'memoize',
    'timing_decorator',
    'get_client_ip',
]
