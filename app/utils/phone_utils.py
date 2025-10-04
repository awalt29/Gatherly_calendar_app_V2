"""
Phone number utility functions for normalization and formatting
"""
import re

def normalize_phone_number(phone):
    """
    Normalize phone number to digits only for consistent storage and searching
    
    Examples:
    - "(555) 123-4567" -> "5551234567"
    - "+1 555-123-4567" -> "15551234567"
    - "555.123.4567" -> "5551234567"
    - "555 123 4567" -> "5551234567"
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # If it starts with 1 and is 11 digits, keep the 1 (US country code)
    # If it's 10 digits, assume US number without country code
    if len(digits_only) == 11 and digits_only.startswith('1'):
        return digits_only
    elif len(digits_only) == 10:
        return digits_only
    else:
        # Return as-is for international numbers or other formats
        return digits_only

def format_phone_display(phone):
    """
    Format phone number for display purposes
    
    Examples:
    - "5551234567" -> "(555) 123-4567"
    - "15551234567" -> "+1 (555) 123-4567"
    """
    if not phone:
        return ""
    
    # Normalize first
    normalized = normalize_phone_number(phone)
    
    if len(normalized) == 10:
        # US number without country code: (555) 123-4567
        return f"({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}"
    elif len(normalized) == 11 and normalized.startswith('1'):
        # US number with country code: +1 (555) 123-4567
        return f"+1 ({normalized[1:4]}) {normalized[4:7]}-{normalized[7:]}"
    else:
        # Other formats, return as-is
        return phone

def search_phone_patterns(phone_input):
    """
    Generate different phone number patterns for flexible searching
    
    Returns a list of possible formats to search for
    """
    if not phone_input:
        return []
    
    normalized = normalize_phone_number(phone_input)
    patterns = [normalized]  # Always include normalized version
    
    # Add original input if different
    if phone_input != normalized:
        patterns.append(phone_input)
    
    # If it's a 10-digit US number, also try with country code
    if len(normalized) == 10:
        patterns.append(f"1{normalized}")
    
    # If it's an 11-digit US number, also try without country code
    elif len(normalized) == 11 and normalized.startswith('1'):
        patterns.append(normalized[1:])
    
    # Add common formatted versions
    if len(normalized) == 10:
        patterns.extend([
            f"({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}",
            f"{normalized[:3]}-{normalized[3:6]}-{normalized[6:]}",
            f"{normalized[:3]}.{normalized[3:6]}.{normalized[6:]}",
            f"{normalized[:3]} {normalized[3:6]} {normalized[6:]}"
        ])
    elif len(normalized) == 11 and normalized.startswith('1'):
        base = normalized[1:]
        patterns.extend([
            f"+1 ({base[:3]}) {base[3:6]}-{base[6:]}",
            f"+1-{base[:3]}-{base[3:6]}-{base[6:]}",
            f"1-{base[:3]}-{base[3:6]}-{base[6:]}",
            f"1 ({base[:3]}) {base[3:6]}-{base[6:]}"
        ])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    for pattern in patterns:
        if pattern not in seen:
            seen.add(pattern)
            unique_patterns.append(pattern)
    
    return unique_patterns
