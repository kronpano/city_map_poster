"""
Font management with CJK (Chinese, Japanese, Korean) support.

Handles:
- Loading custom Roboto fonts
- Detecting CJK characters in text
- Falling back to system CJK fonts when needed
"""

import os
from matplotlib.font_manager import FontProperties


FONTS_DIR = "fonts"


def load_fonts():
    """
    Load Roboto fonts from the fonts directory.
    
    Returns:
        Dict with font paths for different weights, or None if fonts not found
    """
    fonts = {
        'bold': os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'),
        'regular': os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'),
        'light': os.path.join(FONTS_DIR, 'Roboto-Light.ttf')
    }
    
    # Verify fonts exist
    for weight, path in fonts.items():
        if not os.path.exists(path):
            print(f"⚠ Font not found: {path}")
            return None
    
    return fonts


def has_cjk_characters(text: str) -> bool:
    """
    Check if text contains CJK (Chinese, Japanese, Korean) characters.
    
    Args:
        text: Text to check
        
    Returns:
        True if CJK characters found, False otherwise
    """
    for char in text:
        code = ord(char)
        # CJK Unified Ideographs ranges
        if (0x4E00 <= code <= 0x9FFF or      # CJK Unified Ideographs
            0x3400 <= code <= 0x4DBF or      # CJK Unified Ideographs Extension A
            0x20000 <= code <= 0x2A6DF or    # CJK Unified Ideographs Extension B
            0x2A700 <= code <= 0x2B73F or    # CJK Unified Ideographs Extension C
            0x2B740 <= code <= 0x2B81F or    # CJK Unified Ideographs Extension D
            0x2B820 <= code <= 0x2CEAF or    # CJK Unified Ideographs Extension E
            0xF900 <= code <= 0xFAFF or      # CJK Compatibility Ideographs
            0x2F800 <= code <= 0x2FA1F or    # CJK Compatibility Ideographs Supplement
            0x3040 <= code <= 0x309F or      # Hiragana
            0x30A0 <= code <= 0x30FF or      # Katakana
            0xAC00 <= code <= 0xD7AF):       # Hangul Syllables
            return True
    return False


def get_font_with_fallback(
    primary_font_path=None, 
    size=12, 
    weight='normal', 
    verbose=False, 
    text_sample=""
) -> FontProperties:
    """
    Create a FontProperties object with fallback for CJK/Unicode characters.
    
    Args:
        primary_font_path: Path to primary font file (e.g., Roboto)
        size: Font size
        weight: Font weight ('light', 'normal', 'bold')
        verbose: Print font selection info
        text_sample: Sample of text to be rendered (used to detect CJK)
        
    Returns:
        FontProperties object configured with appropriate font
    """
    # Check if the text contains CJK characters
    needs_cjk = has_cjk_characters(text_sample) if text_sample else False
    
    # If text needs CJK support, don't use custom font files - use system fonts
    if needs_cjk:
        if verbose:
            print(f"⚠ Text contains CJK characters, using system CJK font instead of Roboto")
        use_system_font = True
    elif primary_font_path and os.path.exists(primary_font_path):
        # Use specified font for non-CJK text
        return FontProperties(fname=primary_font_path, size=size)
    else:
        use_system_font = True
    
    if use_system_font:
        # Fallback to system fonts with CJK support
        from matplotlib import font_manager
        
        # List of CJK font families to try (in order of preference)
        cjk_font_candidates = [
            'Noto Sans CJK SC',      # Google's font - Simplified Chinese
            'Noto Sans CJK TC',      # Traditional Chinese
            'Noto Sans CJK JP',      # Japanese
            'Noto Sans CJK KR',      # Korean
            'Microsoft YaHei',       # Windows Chinese
            'SimHei',                # Windows Chinese
            'MS Gothic',             # Windows Japanese
            'Malgun Gothic',         # Windows Korean
            'Arial Unicode MS',      # Windows Unicode
            'DejaVu Sans',           # Linux
            'FreeSans',              # Linux
            'Liberation Sans',       # Linux
        ]
        
        # Get all available fonts
        available_fonts = set([f.name for f in font_manager.fontManager.ttflist])
        
        # Find first available CJK font
        found_font = None
        for font_name in cjk_font_candidates:
            if font_name in available_fonts:
                found_font = font_name
                if verbose:
                    print(f"✓ Using CJK font: {font_name}")
                break
        
        if verbose and not found_font:
            print("⚠ No CJK fonts found. Chinese/Japanese/Korean characters may not display correctly.")
            print("  Consider installing: Noto Sans CJK (recommended)")
        
        # Build family list with found font first, then fallbacks
        if found_font:
            family_list = [found_font, 'sans-serif']
        else:
            family_list = ['sans-serif', 'DejaVu Sans', 'Arial Unicode MS']
        
        # Map weight strings to numeric values
        weight_map = {
            'light': 300,
            'normal': 400,
            'regular': 400,
            'bold': 700
        }
        weight_value = weight_map.get(weight, weight)
        
        return FontProperties(
            family=family_list,
            weight=weight_value,
            size=size
        )


def rebuild_font_cache() -> bool:
    """
    Rebuild matplotlib font cache to recognize new fonts.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        import matplotlib.font_manager as fm
        
        # This forces matplotlib to rescan for fonts
        fm._load_fontmanager(try_read_cache=False)
        
        print("✓ Font cache rebuilt successfully")
        return True
    except Exception as e:
        print(f"⚠ Could not rebuild font cache: {e}")
        # Fallback method
        try:
            fm.fontManager.__init__()
            print("✓ Font cache rebuilt using fallback method")
            return True
        except:
            print(f"⚠ Fallback also failed")
            return False
