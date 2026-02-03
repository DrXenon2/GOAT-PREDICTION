"""
Utils Manager Module
Centralized manager for all utility functions
"""

from typing import Optional, Any, Dict, List
from functools import lru_cache
import logging

from .validators import Validator, validate_email, validate_url, validate_password
from .converters import Converter, to_dict, to_json, to_snake_case, to_camel_case
from .formatters import Formatter, format_currency, format_date, format_duration
from .helpers import Helper, generate_id, generate_token, sanitize_string

logger = logging.getLogger(__name__)


class UtilsManager:
    """
    Centralized manager for all utility functions
    Provides unified access to validators, converters, formatters, and helpers
    """
    
    def __init__(self):
        """Initialize utils manager"""
        self.validator = Validator()
        self.converter = Converter()
        self.formatter = Formatter()
        self.helper = Helper()
        
        logger.info("Utils manager initialized")
    
    # Validation methods
    
    def validate(
        self,
        value: Any,
        validation_type: str,
        **kwargs
    ) -> bool:
        """
        Universal validation method
        
        Args:
            value: Value to validate
            validation_type: Type of validation (email, url, uuid, etc.)
            **kwargs: Additional validation parameters
            
        Returns:
            True if valid
        """
        validators = {
            'email': validate_email,
            'url': validate_url,
            'password': lambda v, **kw: validate_password(v, **kw)['valid'],
            'not_empty': self.validator.is_not_empty,
            'type': lambda v, **kw: self.validator.is_type(v, kw.get('expected_type')),
            'range': lambda v, **kw: self.validator.is_range(v, kw.get('min_val'), kw.get('max_val')),
        }
        
        validator_func = validators.get(validation_type)
        if not validator_func:
            raise ValueError(f"Unknown validation type: {validation_type}")
        
        try:
            return validator_func(value, **kwargs)
        except Exception as e:
            logger.error(f"Validation error for {validation_type}: {e}")
            return False
    
    def validate_multiple(
        self,
        data: Dict[str, Any],
        rules: Dict[str, str]
    ) -> Dict[str, bool]:
        """
        Validate multiple fields
        
        Args:
            data: Data dictionary
            rules: Validation rules {field: validation_type}
            
        Returns:
            Validation results {field: is_valid}
        """
        results = {}
        
        for field, validation_type in rules.items():
            value = data.get(field)
            results[field] = self.validate(value, validation_type)
        
        return results
    
    # Conversion methods
    
    def convert(
        self,
        value: Any,
        conversion_type: str,
        **kwargs
    ) -> Any:
        """
        Universal conversion method
        
        Args:
            value: Value to convert
            conversion_type: Type of conversion
            **kwargs: Additional conversion parameters
            
        Returns:
            Converted value
        """
        conversions = {
            'dict': lambda v, **kw: to_dict(v, **kw),
            'json': lambda v, **kw: to_json(v, **kw),
            'snake_case': lambda v, **kw: to_snake_case(v),
            'camel_case': lambda v, **kw: to_camel_case(v, **kw),
            'safe': lambda v, **kw: self.converter.safe_convert(
                v,
                kw.get('target_type', str),
                kw.get('default')
            ),
        }
        
        converter_func = conversions.get(conversion_type)
        if not converter_func:
            raise ValueError(f"Unknown conversion type: {conversion_type}")
        
        try:
            return converter_func(value, **kwargs)
        except Exception as e:
            logger.error(f"Conversion error for {conversion_type}: {e}")
            return kwargs.get('default')
    
    # Formatting methods
    
    def format(
        self,
        value: Any,
        format_type: str,
        **kwargs
    ) -> str:
        """
        Universal formatting method
        
        Args:
            value: Value to format
            format_type: Type of formatting
            **kwargs: Additional formatting parameters
            
        Returns:
            Formatted string
        """
        formatters = {
            'currency': lambda v, **kw: format_currency(v, **kw),
            'date': lambda v, **kw: format_date(v, **kw),
            'duration': lambda v, **kw: format_duration(v, **kw),
            'truncate': lambda v, **kw: self.formatter.truncate(v, kw.get('length', 50)),
        }
        
        formatter_func = formatters.get(format_type)
        if not formatter_func:
            raise ValueError(f"Unknown format type: {format_type}")
        
        try:
            return formatter_func(value, **kwargs)
        except Exception as e:
            logger.error(f"Formatting error for {format_type}: {e}")
            return str(value)
    
    # Helper methods
    
    def generate(
        self,
        generation_type: str,
        **kwargs
    ) -> str:
        """
        Universal generation method
        
        Args:
            generation_type: Type of generation (id, token, slug)
            **kwargs: Additional generation parameters
            
        Returns:
            Generated string
        """
        generators = {
            'id': lambda **kw: generate_id(**kw),
            'token': lambda **kw: generate_token(**kw),
            'slug': lambda **kw: self.helper.generate_slug(**kw),
        }
        
        generator_func = generators.get(generation_type)
        if not generator_func:
            raise ValueError(f"Unknown generation type: {generation_type}")
        
        try:
            return generator_func(**kwargs)
        except Exception as e:
            logger.error(f"Generation error for {generation_type}: {e}")
            raise
    
    def sanitize(
        self,
        text: str,
        **kwargs
    ) -> str:
        """
        Sanitize text
        
        Args:
            text: Text to sanitize
            **kwargs: Sanitization options
            
        Returns:
            Sanitized text
        """
        return sanitize_string(text, **kwargs)
    
    def paginate_data(
        self,
        items: List[Any],
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """
        Paginate data
        
        Args:
            items: List of items
            page: Page number
            per_page: Items per page
            
        Returns:
            Pagination result
        """
        from .helpers import paginate
        return paginate(items, page, per_page)
    
    # Batch operations
    
    def batch_validate(
        self,
        values: List[Any],
        validation_type: str,
        **kwargs
    ) -> List[bool]:
        """
        Validate multiple values
        
        Args:
            values: List of values to validate
            validation_type: Type of validation
            **kwargs: Validation parameters
            
        Returns:
            List of validation results
        """
        return [self.validate(value, validation_type, **kwargs) for value in values]
    
    def batch_convert(
        self,
        values: List[Any],
        conversion_type: str,
        **kwargs
    ) -> List[Any]:
        """
        Convert multiple values
        
        Args:
            values: List of values to convert
            conversion_type: Type of conversion
            **kwargs: Conversion parameters
            
        Returns:
            List of converted values
        """
        return [self.convert(value, conversion_type, **kwargs) for value in values]
    
    def batch_format(
        self,
        values: List[Any],
        format_type: str,
        **kwargs
    ) -> List[str]:
        """
        Format multiple values
        
        Args:
            values: List of values to format
            format_type: Type of formatting
            **kwargs: Formatting parameters
            
        Returns:
            List of formatted strings
        """
        return [self.format(value, format_type, **kwargs) for value in values]
    
    # Utility information
    
    def get_available_validators(self) -> List[str]:
        """Get list of available validators"""
        return [
            'email', 'url', 'uuid', 'password', 'username',
            'phone', 'date', 'ip_address', 'json', 'credit_card'
        ]
    
    def get_available_converters(self) -> List[str]:
        """Get list of available converters"""
        return [
            'dict', 'json', 'snake_case', 'camel_case', 'pascal_case',
            'kebab_case', 'timezone', 'bytes', 'bool'
        ]
    
    def get_available_formatters(self) -> List[str]:
        """Get list of available formatters"""
        return [
            'currency', 'percentage', 'date', 'datetime', 'time',
            'duration', 'filesize', 'number', 'phone', 'address'
        ]
    
    def get_available_generators(self) -> List[str]:
        """Get list of available generators"""
        return ['id', 'uuid', 'token', 'slug', 'password']
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get utils manager information
        
        Returns:
            Information dictionary
        """
        return {
            'validators': self.get_available_validators(),
            'converters': self.get_available_converters(),
            'formatters': self.get_available_formatters(),
            'generators': self.get_available_generators(),
            'version': '1.0.0'
        }
    
    def __repr__(self) -> str:
        """String representation"""
        return "UtilsManager(validators, converters, formatters, helpers)"


# Singleton instance
_utils_manager: Optional[UtilsManager] = None


@lru_cache(maxsize=1)
def get_utils_manager() -> UtilsManager:
    """
    Get singleton utils manager instance
    
    Returns:
        UtilsManager instance
    """
    global _utils_manager
    if _utils_manager is None:
        _utils_manager = UtilsManager()
    return _utils_manager


# Convenience functions using the manager

def validate(value: Any, validation_type: str, **kwargs) -> bool:
    """Validate value using utils manager"""
    return get_utils_manager().validate(value, validation_type, **kwargs)


def convert(value: Any, conversion_type: str, **kwargs) -> Any:
    """Convert value using utils manager"""
    return get_utils_manager().convert(value, conversion_type, **kwargs)


def format_value(value: Any, format_type: str, **kwargs) -> str:
    """Format value using utils manager"""
    return get_utils_manager().format(value, format_type, **kwargs)


def generate(generation_type: str, **kwargs) -> str:
    """Generate value using utils manager"""
    return get_utils_manager().generate(generation_type, **kwargs)


# Export all
__all__ = [
    'UtilsManager',
    'get_utils_manager',
    'validate',
    'convert',
    'format_value',
    'generate',
]
