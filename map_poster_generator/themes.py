"""
Theme management for map posters.

Handles loading and managing color themes from JSON files.
"""

import json
import os
from typing import Dict


THEMES_DIR = "themes"


def get_available_themes() -> list[str]:
    """
    Scan the themes directory and return a list of available theme names.
    
    Returns:
        List of theme names (without .json extension)
    """
    if not os.path.exists(THEMES_DIR):
        os.makedirs(THEMES_DIR)
        return []
    
    themes = []
    for file in sorted(os.listdir(THEMES_DIR)):
        if file.endswith('.json'):
            theme_name = file[:-5]  # Remove .json extension
            themes.append(theme_name)
    return themes


def load_theme(theme_name: str = "feature_based") -> Dict[str, str]:
    """
    Load theme from JSON file in themes directory.
    
    Args:
        theme_name: Name of the theme (without .json extension)
        
    Returns:
        Dictionary containing theme colors and metadata
    """
    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")
    
    if not os.path.exists(theme_file):
        print(f"⚠ Theme file '{theme_file}' not found. Using default feature_based theme.")
        # Fallback to embedded default theme
        return {
            "name": "Feature-Based Shading",
            "bg": "#FFFFFF",
            "text": "#000000",
            "gradient_color": "#FFFFFF",
            "water": "#C0C0C0",
            "parks": "#F0F0F0",
            "railway": "#DEE200",
            "road_motorway": "#0A0A0A",
            "road_primary": "#1A1A1A",
            "road_secondary": "#2A2A2A",
            "road_tertiary": "#3A3A3A",
            "road_residential": "#4A4A4A",
            "road_default": "#3A3A3A"
        }
    
    with open(theme_file, 'r') as f:
        theme = json.load(f)
        if 'description' in theme:
            print(f"  ✓ {theme.get('name', theme_name)}: {theme['description']}")
        else:
            print(f"  ✓ {theme.get('name', theme_name)}")
        return theme


def list_themes_info() -> None:
    """Print detailed information about all available themes."""
    available_themes = get_available_themes()
    if not available_themes:
        print("No themes found in 'themes/' directory.")
        return
    
    print("\nAvailable Themes:")
    print("-" * 60)
    for theme_name in available_themes:
        theme_path = os.path.join(THEMES_DIR, f"{theme_name}.json")
        try:
            with open(theme_path, 'r') as f:
                theme_data = json.load(f)
                display_name = theme_data.get('name', theme_name)
                description = theme_data.get('description', '')
        except:
            display_name = theme_name
            description = ''
        print(f"  {theme_name}")
        print(f"    {display_name}")
        if description:
            print(f"    {description}")
        print()
