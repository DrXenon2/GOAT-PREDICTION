"""
Formatters Module
Data formatting utilities for API Gateway
"""

from typing import Optional, Union, Any
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import locale
import logging

logger = logging.getLogger(__name__)


class Formatter:
    """Base formatter class with common formatting methods"""
    
    @staticmethod
    def truncate(text: str, length: int, suffix: str = '...') -> str:
        """Truncate text to specified length"""
        if len(text) <= length:
            return text
        return text[:length - len(suffix)] + suffix


def format_currency(
    amount: Union[int, float, Decimal],
    currency: str = 'USD',
    locale_name: Optional[str] = None,
    symbol: bool = True
) -> str:
    """
    Format currency amount
    
    Args:
        amount: Amount to format
        currency: Currency code (USD, EUR, GBP, etc.)
        locale_name: Locale for formatting
        symbol: Include currency symbol
        
    Returns:
        Formatted currency string
    """
    # Currency symbols
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CHF': 'Fr',
        'CAD': 'C$',
        'AUD': 'A$',
    }
    
    # Format number with 2 decimal places
    formatted = f"{float(amount):,.2f}"
    
    # Add currency symbol
    if symbol:
        currency_symbol = symbols.get(currency.upper(), currency + ' ')
        
        # Symbol position depends on currency
        if currency.upper() in ['USD', 'GBP', 'CAD', 'AUD']:
            return f"{currency_symbol}{formatted}"
        else:
            return f"{formatted} {currency_symbol}"
    
    return f"{formatted} {currency.upper()}"


def format_percentage(
    value: Union[int, float],
    decimals: int = 2,
    include_sign: bool = True
) -> str:
    """
    Format percentage value
    
    Args:
        value: Value to format (0.5 = 50%)
        decimals: Number of decimal places
        include_sign: Include % sign
        
    Returns:
        Formatted percentage string
    """
    # Convert to percentage if needed
    if abs(value) <= 1.0:
        percentage = value * 100
    else:
        percentage = value
    
    formatted = f"{percentage:.{decimals}f}"
    
    return f"{formatted}%" if include_sign else formatted


def format_date(
    dt: Union[datetime, date],
    format: str = '%Y-%m-%d',
    locale_name: Optional[str] = None
) -> str:
    """
    Format date
    
    Args:
        dt: Date or datetime object
        format: Date format string
        locale_name: Locale for formatting
        
    Returns:
        Formatted date string
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    return dt.strftime(format)


def format_datetime(
    dt: datetime,
    format: str = '%Y-%m-%d %H:%M:%S',
    timezone_name: Optional[str] = None
) -> str:
    """
    Format datetime
    
    Args:
        dt: Datetime object
        format: Datetime format string
        timezone_name: Timezone name
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime(format)


def format_time(
    t: Union[datetime, time],
    format: str = '%H:%M:%S'
) -> str:
    """
    Format time
    
    Args:
        t: Time or datetime object
        format: Time format string
        
    Returns:
        Formatted time string
    """
    if isinstance(t, datetime):
        t = t.time()
    
    return t.strftime(format)


def format_duration(
    seconds: Union[int, float, timedelta],
    verbose: bool = False,
    precision: int = 2
) -> str:
    """
    Format duration/time difference
    
    Args:
        seconds: Duration in seconds or timedelta object
        verbose: Use verbose format (e.g., "2 hours" vs "2h")
        precision: Number of time units to show
        
    Returns:
        Formatted duration string
    """
    if isinstance(seconds, timedelta):
        seconds = seconds.total_seconds()
    
    seconds = int(seconds)
    
    # Time units
    units = [
        ('year', 'y', 365 * 24 * 3600),
        ('month', 'mo', 30 * 24 * 3600),
        ('week', 'w', 7 * 24 * 3600),
        ('day', 'd', 24 * 3600),
        ('hour', 'h', 3600),
        ('minute', 'm', 60),
        ('second', 's', 1),
    ]
    
    parts = []
    remaining = seconds
    
    for long_name, short_name, unit_seconds in units:
        if remaining >= unit_seconds:
            value = remaining // unit_seconds
            remaining %= unit_seconds
            
            if verbose:
                unit = long_name if value == 1 else f"{long_name}s"
                parts.append(f"{value} {unit}")
            else:
                parts.append(f"{value}{short_name}")
            
            if len(parts) >= precision:
                break
    
    if not parts:
        return "0s" if not verbose else "0 seconds"
    
    if verbose:
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return f"{parts[0]} and {parts[1]}"
        else:
            return ', '.join(parts[:-1]) + f", and {parts[-1]}"
    else:
        return ' '.join(parts)


def format_filesize(
    bytes_size: Union[int, float],
    precision: int = 2,
    binary: bool = False
) -> str:
    """
    Format file size
    
    Args:
        bytes_size: Size in bytes
        precision: Decimal precision
        binary: Use binary units (1024) vs decimal (1000)
        
    Returns:
        Formatted file size
    """
    if binary:
        units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
        divisor = 1024.0
    else:
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        divisor = 1000.0
    
    size = float(bytes_size)
    
    for unit in units[:-1]:
        if abs(size) < divisor:
            return f"{size:.{precision}f} {unit}"
        size /= divisor
    
    return f"{size:.{precision}f} {units[-1]}"


def format_number(
    number: Union[int, float, Decimal],
    decimals: Optional[int] = None,
    thousands_separator: str = ',',
    decimal_separator: str = '.'
) -> str:
    """
    Format number with separators
    
    Args:
        number: Number to format
        decimals: Number of decimal places (None for auto)
        thousands_separator: Thousands separator
        decimal_separator: Decimal separator
        
    Returns:
        Formatted number string
    """
    if decimals is not None:
        formatted = f"{float(number):.{decimals}f}"
    else:
        formatted = str(float(number))
    
    # Split integer and decimal parts
    if '.' in formatted:
        integer_part, decimal_part = formatted.split('.')
    else:
        integer_part, decimal_part = formatted, None
    
    # Add thousands separators
    integer_with_sep = '{:,}'.format(int(integer_part)).replace(',', thousands_separator)
    
    # Combine with decimal part
    if decimal_part:
        return f"{integer_with_sep}{decimal_separator}{decimal_part}"
    
    return integer_with_sep


def format_phone(phone: str, country_code: str = 'US') -> str:
    """
    Format phone number
    
    Args:
        phone: Phone number
        country_code: Country code
        
    Returns:
        Formatted phone number
    """
    # Remove non-digits
    import re
    digits = re.sub(r'\D', '', phone)
    
    if country_code.upper() == 'US':
        # US format: (123) 456-7890
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    
    return phone


def format_address(
    street: str,
    city: str,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    country: Optional[str] = None,
    multiline: bool = False
) -> str:
    """
    Format postal address
    
    Args:
        street: Street address
        city: City
        state: State/province
        postal_code: Postal/ZIP code
        country: Country
        multiline: Use multiple lines
        
    Returns:
        Formatted address
    """
    parts = [street]
    
    city_line = city
    if state:
        city_line += f", {state}"
    if postal_code:
        city_line += f" {postal_code}"
    
    parts.append(city_line)
    
    if country:
        parts.append(country)
    
    if multiline:
        return '\n'.join(parts)
    else:
        return ', '.join(parts)


def format_name(
    first_name: str,
    last_name: str,
    middle_name: Optional[str] = None,
    title: Optional[str] = None,
    format: str = 'first_last'
) -> str:
    """
    Format person's name
    
    Args:
        first_name: First name
        last_name: Last name
        middle_name: Middle name
        title: Title (Mr., Dr., etc.)
        format: Name format (first_last, last_first, full)
        
    Returns:
        Formatted name
    """
    if format == 'last_first':
        name = f"{last_name}, {first_name}"
        if middle_name:
            name += f" {middle_name[0]}."
    elif format == 'full':
        parts = []
        if title:
            parts.append(title)
        parts.append(first_name)
        if middle_name:
            parts.append(middle_name)
        parts.append(last_name)
        name = ' '.join(parts)
    else:  # first_last
        name = f"{first_name} {last_name}"
        if title:
            name = f"{title} {name}"
    
    return name


def format_list(
    items: list,
    conjunction: str = 'and',
    oxford_comma: bool = True
) -> str:
    """
    Format list as human-readable string
    
    Args:
        items: List of items
        conjunction: Conjunction word (and, or)
        oxford_comma: Use Oxford comma
        
    Returns:
        Formatted list string
    """
    items = [str(item) for item in items]
    
    if len(items) == 0:
        return ''
    elif len(items) == 1:
        return items[0]
    elif len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    else:
        if oxford_comma:
            return f"{', '.join(items[:-1])}, {conjunction} {items[-1]}"
        else:
            return f"{', '.join(items[:-1])} {conjunction} {items[-1]}"


def format_json(
    data: Any,
    indent: int = 2,
    sort_keys: bool = False,
    pretty: bool = True
) -> str:
    """
    Format data as pretty JSON
    
    Args:
        data: Data to format
        indent: Indentation spaces
        sort_keys: Sort dictionary keys
        pretty: Pretty print format
        
    Returns:
        Formatted JSON string
    """
    import json
    
    if pretty:
        return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
    else:
        return json.dumps(data, sort_keys=sort_keys, ensure_ascii=False)


def format_sql(sql: str) -> str:
    """
    Format SQL query for readability
    
    Args:
        sql: SQL query string
        
    Returns:
        Formatted SQL
    """
    import re
    
    # Keywords to uppercase
    keywords = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
        'ON', 'AND', 'OR', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET',
        'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE',
        'ALTER', 'DROP', 'AS', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN'
    ]
    
    formatted = sql
    for keyword in keywords:
        formatted = re.sub(
            rf'\b{keyword}\b',
            keyword,
            formatted,
            flags=re.IGNORECASE
        )
    
    return formatted


# Export all
__all__ = [
    'Formatter',
    'format_currency',
    'format_percentage',
    'format_date',
    'format_datetime',
    'format_time',
    'format_duration',
    'format_filesize',
    'format_number',
    'format_phone',
    'format_address',
    'format_name',
    'format_list',
    'format_json',
    'format_sql',
]
