"""
Converters Module
Data conversion utilities for API Gateway
"""

import json
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Converter:
    """Base converter class with common conversion methods"""
    
    @staticmethod
    def safe_convert(value: Any, target_type: type, default: Any = None) -> Any:
        """
        Safely convert value to target type
        
        Args:
            value: Value to convert
            target_type: Target type
            default: Default value if conversion fails
            
        Returns:
            Converted value or default
        """
        try:
            return target_type(value)
        except (ValueError, TypeError):
            return default


def to_dict(obj: Any, exclude_none: bool = False, exclude_private: bool = True) -> Dict[str, Any]:
    """
    Convert object to dictionary
    
    Args:
        obj: Object to convert
        exclude_none: Exclude None values
        exclude_private: Exclude private attributes (starting with _)
        
    Returns:
        Dictionary representation
    """
    if isinstance(obj, dict):
        result = obj
    elif hasattr(obj, '__dict__'):
        result = obj.__dict__.copy()
    elif hasattr(obj, '_asdict'):  # namedtuple
        result = obj._asdict()
    else:
        return {}
    
    # Filter private attributes
    if exclude_private:
        result = {k: v for k, v in result.items() if not k.startswith('_')}
    
    # Filter None values
    if exclude_none:
        result = {k: v for k, v in result.items() if v is not None}
    
    # Recursively convert nested objects
    for key, value in result.items():
        if hasattr(value, '__dict__') or hasattr(value, '_asdict'):
            result[key] = to_dict(value, exclude_none, exclude_private)
        elif isinstance(value, list):
            result[key] = [
                to_dict(item, exclude_none, exclude_private) 
                if hasattr(item, '__dict__') else item 
                for item in value
            ]
    
    return result


def to_json(
    obj: Any,
    indent: Optional[int] = None,
    sort_keys: bool = False,
    ensure_ascii: bool = False
) -> str:
    """
    Convert object to JSON string
    
    Args:
        obj: Object to convert
        indent: JSON indentation
        sort_keys: Sort dictionary keys
        ensure_ascii: Ensure ASCII encoding
        
    Returns:
        JSON string
    """
    def json_encoder(o):
        """Custom JSON encoder for special types"""
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, Decimal):
            return float(o)
        elif hasattr(o, '__dict__'):
            return to_dict(o)
        elif hasattr(o, '_asdict'):
            return o._asdict()
        return str(o)
    
    return json.dumps(
        obj,
        default=json_encoder,
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=ensure_ascii
    )


def from_json(json_string: str, default: Any = None) -> Any:
    """
    Parse JSON string to Python object
    
    Args:
        json_string: JSON string
        default: Default value if parsing fails
        
    Returns:
        Parsed object or default
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Error parsing JSON: {e}")
        return default


def to_snake_case(text: str) -> str:
    """
    Convert string to snake_case
    
    Args:
        text: String to convert
        
    Returns:
        snake_case string
    """
    # Insert underscore before uppercase letters
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    # Insert underscore before uppercase letters followed by lowercase
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    # Replace spaces and dashes with underscores
    s3 = re.sub(r'[\s\-]+', '_', s2)
    # Convert to lowercase
    return s3.lower()


def to_camel_case(text: str, upper_first: bool = False) -> str:
    """
    Convert string to camelCase
    
    Args:
        text: String to convert
        upper_first: Start with uppercase (PascalCase)
        
    Returns:
        camelCase string
    """
    # Split on underscores, spaces, and dashes
    words = re.split(r'[_\s\-]+', text.lower())
    
    if not words:
        return text
    
    # Capitalize first letter of each word except the first
    result = words[0]
    result += ''.join(word.capitalize() for word in words[1:])
    
    # Uppercase first letter if requested
    if upper_first and result:
        result = result[0].upper() + result[1:]
    
    return result


def to_pascal_case(text: str) -> str:
    """
    Convert string to PascalCase
    
    Args:
        text: String to convert
        
    Returns:
        PascalCase string
    """
    return to_camel_case(text, upper_first=True)


def to_kebab_case(text: str) -> str:
    """
    Convert string to kebab-case
    
    Args:
        text: String to convert
        
    Returns:
        kebab-case string
    """
    snake = to_snake_case(text)
    return snake.replace('_', '-')


def convert_keys(
    data: Union[Dict, List],
    converter_func: callable,
    recursive: bool = True
) -> Union[Dict, List]:
    """
    Convert dictionary keys using converter function
    
    Args:
        data: Dictionary or list to convert
        converter_func: Function to convert keys
        recursive: Apply recursively to nested structures
        
    Returns:
        Converted data structure
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            new_key = converter_func(key) if isinstance(key, str) else key
            
            if recursive and isinstance(value, (dict, list)):
                result[new_key] = convert_keys(value, converter_func, recursive)
            else:
                result[new_key] = value
        
        return result
    
    elif isinstance(data, list):
        return [
            convert_keys(item, converter_func, recursive) 
            if isinstance(item, (dict, list)) else item
            for item in data
        ]
    
    return data


def convert_timezone(
    dt: datetime,
    from_tz: Optional[timezone] = None,
    to_tz: timezone = timezone.utc
) -> datetime:
    """
    Convert datetime between timezones
    
    Args:
        dt: Datetime object
        from_tz: Source timezone (None for naive datetime)
        to_tz: Target timezone
        
    Returns:
        Converted datetime
    """
    if dt.tzinfo is None:
        # Naive datetime - assign source timezone
        if from_tz:
            dt = dt.replace(tzinfo=from_tz)
        else:
            dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(to_tz)


def bytes_to_human_readable(bytes_size: int, precision: int = 2) -> str:
    """
    Convert bytes to human-readable format
    
    Args:
        bytes_size: Size in bytes
        precision: Decimal precision
        
    Returns:
        Human-readable size (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.{precision}f} {unit}"
        bytes_size /= 1024.0
    
    return f"{bytes_size:.{precision}f} EB"


def human_readable_to_bytes(size_str: str) -> int:
    """
    Convert human-readable size to bytes
    
    Args:
        size_str: Size string (e.g., "1.5 MB")
        
    Returns:
        Size in bytes
    """
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'PB': 1024 ** 5,
        'EB': 1024 ** 6,
    }
    
    # Parse size string
    match = re.match(r'^([\d.]+)\s*([A-Z]+)$', size_str.strip().upper())
    if not match:
        raise ValueError(f"Invalid size format: {size_str}")
    
    number, unit = match.groups()
    
    if unit not in units:
        raise ValueError(f"Unknown unit: {unit}")
    
    return int(float(number) * units[unit])


def bool_to_string(value: bool, format: str = 'yes_no') -> str:
    """
    Convert boolean to string
    
    Args:
        value: Boolean value
        format: Output format (yes_no, true_false, on_off, 1_0)
        
    Returns:
        String representation
    """
    formats = {
        'yes_no': ('Yes', 'No'),
        'true_false': ('True', 'False'),
        'on_off': ('On', 'Off'),
        '1_0': ('1', '0'),
    }
    
    if format not in formats:
        format = 'yes_no'
    
    true_val, false_val = formats[format]
    return true_val if value else false_val


def string_to_bool(value: str, default: bool = False) -> bool:
    """
    Convert string to boolean
    
    Args:
        value: String value
        default: Default if conversion fails
        
    Returns:
        Boolean value
    """
    if not isinstance(value, str):
        return default
    
    true_values = {'true', 'yes', 'on', '1', 'y', 't'}
    false_values = {'false', 'no', 'off', '0', 'n', 'f'}
    
    value_lower = value.lower().strip()
    
    if value_lower in true_values:
        return True
    elif value_lower in false_values:
        return False
    
    return default


def list_to_dict(
    items: List[Any],
    key_attr: str,
    value_attr: Optional[str] = None
) -> Dict[Any, Any]:
    """
    Convert list to dictionary using specified attributes
    
    Args:
        items: List of items
        key_attr: Attribute to use as key
        value_attr: Attribute to use as value (None = whole object)
        
    Returns:
        Dictionary
    """
    result = {}
    
    for item in items:
        if isinstance(item, dict):
            key = item.get(key_attr)
            value = item.get(value_attr) if value_attr else item
        elif hasattr(item, key_attr):
            key = getattr(item, key_attr)
            value = getattr(item, value_attr) if value_attr else item
        else:
            continue
        
        result[key] = value
    
    return result


def dict_to_query_string(params: Dict[str, Any], encode: bool = True) -> str:
    """
    Convert dictionary to URL query string
    
    Args:
        params: Parameters dictionary
        encode: URL encode values
        
    Returns:
        Query string
    """
    from urllib.parse import urlencode, quote
    
    if encode:
        return urlencode(params)
    else:
        return '&'.join(f"{k}={v}" for k, v in params.items())


def flatten_dict(
    nested_dict: Dict[str, Any],
    separator: str = '.',
    parent_key: str = ''
) -> Dict[str, Any]:
    """
    Flatten nested dictionary
    
    Args:
        nested_dict: Nested dictionary
        separator: Key separator
        parent_key: Parent key prefix
        
    Returns:
        Flattened dictionary
    """
    items = []
    
    for key, value in nested_dict.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(
                flatten_dict(value, separator, new_key).items()
            )
        else:
            items.append((new_key, value))
    
    return dict(items)


def unflatten_dict(
    flat_dict: Dict[str, Any],
    separator: str = '.'
) -> Dict[str, Any]:
    """
    Unflatten dictionary with separator in keys
    
    Args:
        flat_dict: Flattened dictionary
        separator: Key separator
        
    Returns:
        Nested dictionary
    """
    result = {}
    
    for key, value in flat_dict.items():
        parts = key.split(separator)
        current = result
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    return result


# Export all
__all__ = [
    'Converter',
    'to_dict',
    'to_json',
    'from_json',
    'to_snake_case',
    'to_camel_case',
    'to_pascal_case',
    'to_kebab_case',
    'convert_keys',
    'convert_timezone',
    'bytes_to_human_readable',
    'human_readable_to_bytes',
    'bool_to_string',
    'string_to_bool',
    'list_to_dict',
    'dict_to_query_string',
    'flatten_dict',
    'unflatten_dict',
]
