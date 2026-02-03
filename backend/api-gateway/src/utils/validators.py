"""
Validators Module
Data validation utilities for API Gateway
"""

import re
from typing import Optional, Any, List, Dict
from datetime import datetime, date
from email.utils import parseaddr
import uuid as uuid_lib
import logging

logger = logging.getLogger(__name__)


class Validator:
    """Base validator class with common validation methods"""
    
    @staticmethod
    def is_not_empty(value: Any) -> bool:
        """Check if value is not empty"""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict, tuple)):
            return bool(value)
        return True
    
    @staticmethod
    def is_type(value: Any, expected_type: type) -> bool:
        """Check if value is of expected type"""
        return isinstance(value, expected_type)
    
    @staticmethod
    def is_in_range(value: float, min_val: Optional[float] = None, 
                    max_val: Optional[float] = None) -> bool:
        """Check if value is in specified range"""
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True
    
    @staticmethod
    def is_length_valid(value: str, min_length: Optional[int] = None,
                       max_length: Optional[int] = None) -> bool:
        """Check if string length is valid"""
        length = len(value)
        if min_length is not None and length < min_length:
            return False
        if max_length is not None and length > max_length:
            return False
        return True


def validate_email(email: str, check_mx: bool = False) -> bool:
    """
    Validate email address
    
    Args:
        email: Email address to validate
        check_mx: Check MX records (requires DNS lookup)
        
    Returns:
        True if valid email
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic format validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False
    
    # Parse email
    name, addr = parseaddr(email)
    if not addr:
        return False
    
    # Additional validations
    local, domain = addr.rsplit('@', 1)
    
    # Local part checks
    if len(local) > 64:
        return False
    if local.startswith('.') or local.endswith('.'):
        return False
    if '..' in local:
        return False
    
    # Domain checks
    if len(domain) > 255:
        return False
    if domain.startswith('-') or domain.endswith('-'):
        return False
    
    # MX record check (optional, requires DNS)
    if check_mx:
        try:
            import dns.resolver
            mx_records = dns.resolver.resolve(domain, 'MX')
            return len(list(mx_records)) > 0
        except:
            logger.warning(f"Could not verify MX records for {domain}")
    
    return True


def validate_phone(phone: str, country_code: Optional[str] = None) -> bool:
    """
    Validate phone number
    
    Args:
        phone: Phone number to validate
        country_code: Optional country code (e.g., 'US', 'FR')
        
    Returns:
        True if valid phone number
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # Check if only digits and + (for international)
    if not re.match(r'^\+?[0-9]{7,15}$', cleaned):
        return False
    
    # Country-specific validation (basic)
    if country_code:
        if country_code.upper() == 'US':
            # US: +1XXXXXXXXXX or 10 digits
            pattern = r'^(\+1)?[0-9]{10}$'
            return bool(re.match(pattern, cleaned))
        elif country_code.upper() == 'FR':
            # France: +33XXXXXXXXX or 0XXXXXXXXX
            pattern = r'^(\+33|0)[0-9]{9}$'
            return bool(re.match(pattern, cleaned))
    
    return True


def validate_url(url: str, schemes: Optional[List[str]] = None) -> bool:
    """
    Validate URL
    
    Args:
        url: URL to validate
        schemes: Allowed URL schemes (default: ['http', 'https'])
        
    Returns:
        True if valid URL
    """
    if not url or not isinstance(url, str):
        return False
    
    if schemes is None:
        schemes = ['http', 'https']
    
    # Basic URL pattern
    pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
    if not re.match(pattern, url, re.IGNORECASE):
        return False
    
    # Check scheme
    scheme = url.split('://')[0].lower()
    if scheme not in schemes:
        return False
    
    return True


def validate_uuid(uuid_string: str, version: Optional[int] = None) -> bool:
    """
    Validate UUID
    
    Args:
        uuid_string: UUID string to validate
        version: Optional UUID version (1, 3, 4, 5)
        
    Returns:
        True if valid UUID
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    try:
        uuid_obj = uuid_lib.UUID(uuid_string)
        
        # Check version if specified
        if version is not None and uuid_obj.version != version:
            return False
        
        return True
    except (ValueError, AttributeError):
        return False


def validate_date(date_string: str, format: str = '%Y-%m-%d') -> bool:
    """
    Validate date string
    
    Args:
        date_string: Date string to validate
        format: Expected date format
        
    Returns:
        True if valid date
    """
    if not date_string or not isinstance(date_string, str):
        return False
    
    try:
        datetime.strptime(date_string, format)
        return True
    except ValueError:
        return False


def validate_password(
    password: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = True
) -> Dict[str, Any]:
    """
    Validate password strength
    
    Args:
        password: Password to validate
        min_length: Minimum password length
        require_uppercase: Require uppercase letter
        require_lowercase: Require lowercase letter
        require_digit: Require digit
        require_special: Require special character
        
    Returns:
        Dictionary with validation results
    """
    result = {
        'valid': True,
        'errors': [],
        'strength': 'strong'
    }
    
    if not password or not isinstance(password, str):
        result['valid'] = False
        result['errors'].append('Password is required')
        return result
    
    # Length check
    if len(password) < min_length:
        result['valid'] = False
        result['errors'].append(f'Password must be at least {min_length} characters')
    
    # Uppercase check
    if require_uppercase and not re.search(r'[A-Z]', password):
        result['valid'] = False
        result['errors'].append('Password must contain at least one uppercase letter')
    
    # Lowercase check
    if require_lowercase and not re.search(r'[a-z]', password):
        result['valid'] = False
        result['errors'].append('Password must contain at least one lowercase letter')
    
    # Digit check
    if require_digit and not re.search(r'\d', password):
        result['valid'] = False
        result['errors'].append('Password must contain at least one digit')
    
    # Special character check
    if require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        result['valid'] = False
        result['errors'].append('Password must contain at least one special character')
    
    # Calculate strength
    if result['valid']:
        score = 0
        score += min(len(password) // 4, 5)  # Length score (max 5)
        score += 1 if re.search(r'[A-Z]', password) else 0
        score += 1 if re.search(r'[a-z]', password) else 0
        score += 1 if re.search(r'\d', password) else 0
        score += 1 if re.search(r'[!@#$%^&*]', password) else 0
        
        if score >= 8:
            result['strength'] = 'strong'
        elif score >= 6:
            result['strength'] = 'medium'
        else:
            result['strength'] = 'weak'
    else:
        result['strength'] = 'weak'
    
    return result


def validate_username(
    username: str,
    min_length: int = 3,
    max_length: int = 30,
    allow_special: bool = False
) -> bool:
    """
    Validate username
    
    Args:
        username: Username to validate
        min_length: Minimum length
        max_length: Maximum length
        allow_special: Allow special characters
        
    Returns:
        True if valid username
    """
    if not username or not isinstance(username, str):
        return False
    
    # Length check
    if len(username) < min_length or len(username) > max_length:
        return False
    
    # Character check
    if allow_special:
        pattern = r'^[a-zA-Z0-9_\-\.]+$'
    else:
        pattern = r'^[a-zA-Z0-9_]+$'
    
    if not re.match(pattern, username):
        return False
    
    # Cannot start or end with special chars
    if username[0] in '._-' or username[-1] in '._-':
        return False
    
    # No consecutive special chars
    if re.search(r'[._-]{2,}', username):
        return False
    
    return True


def validate_json(json_string: str) -> bool:
    """
    Validate JSON string
    
    Args:
        json_string: JSON string to validate
        
    Returns:
        True if valid JSON
    """
    if not json_string or not isinstance(json_string, str):
        return False
    
    try:
        import json
        json.loads(json_string)
        return True
    except (ValueError, TypeError):
        return False


def validate_ip_address(ip: str, version: Optional[int] = None) -> bool:
    """
    Validate IP address
    
    Args:
        ip: IP address to validate
        version: IP version (4 or 6)
        
    Returns:
        True if valid IP address
    """
    if not ip or not isinstance(ip, str):
        return False
    
    import ipaddress
    
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        if version == 4:
            return isinstance(ip_obj, ipaddress.IPv4Address)
        elif version == 6:
            return isinstance(ip_obj, ipaddress.IPv6Address)
        
        return True
    except ValueError:
        return False


def validate_credit_card(card_number: str) -> Dict[str, Any]:
    """
    Validate credit card number using Luhn algorithm
    
    Args:
        card_number: Credit card number
        
    Returns:
        Dictionary with validation results
    """
    result = {
        'valid': False,
        'card_type': None
    }
    
    if not card_number or not isinstance(card_number, str):
        return result
    
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-]', '', card_number)
    
    # Check if only digits
    if not cleaned.isdigit():
        return result
    
    # Luhn algorithm
    def luhn_check(number: str) -> bool:
        digits = [int(d) for d in number]
        checksum = 0
        
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        
        return checksum % 10 == 0
    
    if not luhn_check(cleaned):
        return result
    
    # Identify card type
    if cleaned.startswith('4'):
        result['card_type'] = 'visa'
    elif cleaned.startswith(('51', '52', '53', '54', '55')):
        result['card_type'] = 'mastercard'
    elif cleaned.startswith(('34', '37')):
        result['card_type'] = 'amex'
    elif cleaned.startswith('6011'):
        result['card_type'] = 'discover'
    
    result['valid'] = True
    return result


def validate_postal_code(postal_code: str, country_code: str = 'US') -> bool:
    """
    Validate postal code for different countries
    
    Args:
        postal_code: Postal code to validate
        country_code: Country code
        
    Returns:
        True if valid postal code
    """
    if not postal_code or not isinstance(postal_code, str):
        return False
    
    patterns = {
        'US': r'^\d{5}(-\d{4})?$',  # 12345 or 12345-6789
        'CA': r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$',  # A1A 1A1
        'UK': r'^[A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2}$',  # SW1A 1AA
        'FR': r'^\d{5}$',  # 75001
        'DE': r'^\d{5}$',  # 12345
    }
    
    pattern = patterns.get(country_code.upper())
    if not pattern:
        return False
    
    return bool(re.match(pattern, postal_code.upper()))


# Export all
__all__ = [
    'Validator',
    'validate_email',
    'validate_phone',
    'validate_url',
    'validate_uuid',
    'validate_date',
    'validate_password',
    'validate_username',
    'validate_json',
    'validate_ip_address',
    'validate_credit_card',
    'validate_postal_code',
]
