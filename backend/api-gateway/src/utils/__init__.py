"""
Utils Module for API Gateway
Common utilities, helpers, validators, converters, and formatters
"""

from .validators import (
    validate_email,
    validate_phone,
    validate_url,
    validate_uuid,
    validate_date,
    validate_password,
    validate_username,
    Validator
)

from .converters import (
    to_dict,
    to_json,
    from_json,
    to_snake_case,
    to_camel_case,
    to_pascal_case,
    convert_timezone,
    Converter
)

from .formatters import (
    format_currency,
    format_percentage,
    format_date,
    format_datetime,
    format_duration,
    format_filesize,
    format_number,
    Formatter
)

from .helpers import (
    generate_id,
    generate_token,
    generate_slug,
    paginate,
    calculate_hash,
    sanitize_string,
    truncate_string,
    parse_query_params,
    Helper
)

from .utils_manager import UtilsManager, get_utils_manager

__all__ = [
    # Validators
    'validate_email',
    'validate_phone',
    'validate_url',
    'validate_uuid',
    'validate_date',
    'validate_password',
    'validate_username',
    'Validator',
    
    # Converters
    'to_dict',
    'to_json',
    'from_json',
    'to_snake_case',
    'to_camel_case',
    'to_pascal_case',
    'convert_timezone',
    'Converter',
    
    # Formatters
    'format_currency',
    'format_percentage',
    'format_date',
    'format_datetime',
    'format_duration',
    'format_filesize',
    'format_number',
    'Formatter',
    
    # Helpers
    'generate_id',
    'generate_token',
    'generate_slug',
    'paginate',
    'calculate_hash',
    'sanitize_string',
    'truncate_string',
    'parse_query_params',
    'Helper',
    
    # Manager
    'UtilsManager',
    'get_utils_manager',
]

__version__ = '1.0.0'
