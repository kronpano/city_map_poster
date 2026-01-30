"""
Utility functions for the map poster generator.
"""

import os
from datetime import datetime


POSTERS_DIR = "posters"


def generate_output_filename(
    city: str, 
    theme_name: str, 
    distance: int, 
    output_format: str, 
    shift: str | None = None
) -> str:
    """
    Generate unique output filename with city, theme, distance, shift, and datetime.
    
    Args:
        city: City name
        theme_name: Theme name
        distance: Distance in meters
        output_format: File format extension
        shift: Optional shift string
        
    Returns:
        Full path to output file
    """
    if not os.path.exists(POSTERS_DIR):
        os.makedirs(POSTERS_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city.lower().replace(' ', '_')
    ext = output_format.lower()
    
    if shift:
        filename = f"{city_slug}_{theme_name}_{distance}_{shift}_{timestamp}.{ext}"
    else:
        filename = f"{city_slug}_{theme_name}_{distance}_{timestamp}.{ext}"
    
    return os.path.join(POSTERS_DIR, filename)


def parse_aspect_ratio(ratio_str: str) -> tuple[float, float]:
    """
    Parse aspect ratio string like '16:9' or '4:3' and return (width, height) in inches.
    Uses a base size and scales according to the ratio.
    
    Args:
        ratio_str: Ratio string (e.g., '16:9', '4:3')
        
    Returns:
        Tuple of (width, height) in inches
        
    Raises:
        ValueError: If ratio format is invalid
    """
    try:
        parts = ratio_str.split(':')
        if len(parts) != 2:
            raise ValueError("Ratio must be in format 'width:height' (e.g., '16:9')")
        
        width_ratio = float(parts[0])
        height_ratio = float(parts[1])
        
        # Base size
        base_size = 16  # inches
        
        # Calculate dimensions maintaining the ratio
        if width_ratio >= height_ratio:
            width = base_size
            height = base_size * (height_ratio / width_ratio)
        else:
            height = base_size
            width = base_size * (width_ratio / height_ratio)
        
        return (width, height)
    
    except (ValueError, ZeroDivisionError) as e:
        raise ValueError(f"Invalid aspect ratio '{ratio_str}': {e}")
