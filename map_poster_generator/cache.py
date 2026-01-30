"""
Cache management for map poster generation.

Handles caching of:
- Geocoding results
- OSM graph data
- Processed features
- State/province information
"""

import pickle
from pathlib import Path
from hashlib import md5
import os


class CacheError(Exception):
    """Raised when a cache operation fails."""
    pass


# Global variable to store current city for cache organization
_CURRENT_CITY_CACHE = None

# Cache directory from environment or default
CACHE_DIR_PATH = os.environ.get("CACHE_DIR", "cache")
CACHE_DIR = Path(CACHE_DIR_PATH)
CACHE_DIR.mkdir(exist_ok=True)


def set_cache_city(city: str, country: str) -> Path:
    """
    Set the current city for cache organization.
    Creates a city-specific cache directory.
    
    Args:
        city: City name
        country: Country name
        
    Returns:
        Path to the city-specific cache directory
    """
    global _CURRENT_CITY_CACHE
    
    # Create a clean directory name from city and country
    city_slug = f"{city}_{country}".lower().replace(' ', '_').replace(',', '')
    _CURRENT_CITY_CACHE = city_slug
    
    # Create the directory
    city_dir = CACHE_DIR / city_slug
    city_dir.mkdir(exist_ok=True, parents=True)
    
    print(f"📁 Cache directory: {city_dir}")
    
    return city_dir


def get_city_cache_dir() -> Path:
    """Get the cache directory for the current city."""
    if _CURRENT_CITY_CACHE is None:
        return CACHE_DIR
    
    city_dir = CACHE_DIR / _CURRENT_CITY_CACHE
    city_dir.mkdir(exist_ok=True)
    return city_dir


def cache_file(key: str) -> str:
    """Generate a cache filename from a key using MD5 hash."""
    encoded = md5(key.encode()).hexdigest()
    return f"{encoded}.pkl"


def cache_get(name: str):
    """
    Retrieve an object from cache.
    
    Args:
        name: Cache key
        
    Returns:
        Cached object or None if not found
    """
    cache_dir = get_city_cache_dir()
    path = cache_dir / cache_file(name)
    
    if path.exists():
        with path.open("rb") as f:
            return pickle.load(f)
    
    return None


def cache_set(name: str, obj) -> None:
    """
    Store an object in cache.
    
    Args:
        name: Cache key
        obj: Object to cache
        
    Raises:
        CacheError: If caching fails
    """
    cache_dir = get_city_cache_dir()
    path = cache_dir / cache_file(name)
    
    try:
        with path.open("wb") as f:
            pickle.dump(obj, f)
    except pickle.PickleError as e:
        raise CacheError(
            f"Serialization error while saving cache for '{name}': {e}"
        ) from e
    except (OSError, IOError) as e:
        raise CacheError(
            f"File error while saving cache for '{name}': {e}"
        ) from e


def configure_osmnx_cache(cache_dir: Path) -> None:
    """
    Configure OSMnx to use a specific cache directory.
    
    Args:
        cache_dir: Path to cache directory
    """
    import osmnx as ox
    ox.settings.cache_folder = str(cache_dir)
    ox.settings.use_cache = True
