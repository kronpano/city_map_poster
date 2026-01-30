"""
Geocoding functionality using Nominatim.

Handles:
- Looking up coordinates for cities
- Extracting state/province information
- Coordinate shifting with compass directions
- Caching of results
"""

import time
import asyncio
import re
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

from .cache import cache_get, cache_set, CacheError


def get_state_province(city: str, country: str) -> str | None:
    """
    Fetch just the state/province information for a city.
    Used when coordinates are manually provided.
    
    Args:
        city: City name
        country: Country name
        
    Returns:
        State/province name or None if not found
    """
    province_cache = f"province_{city.lower()}_{country.lower()}"
    cached = cache_get(province_cache)
    
    if cached is not None:
        print("✓ Using cached state/province info")
        return cached

    print("Looking up state/province information...")
    geolocator = Nominatim(user_agent="city_map_poster", timeout=10)
    
    time.sleep(1)
    
    location = geolocator.geocode(f"{city}, {country}", addressdetails=True)
    
    # Handle async if needed
    if asyncio.iscoroutine(location):
        try:
            location = asyncio.run(location)
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Geocoder returned a coroutine while an event loop is already running.")
            location = loop.run_until_complete(location)
    
    if location:
        # Extract state/province from address details
        address = location.raw.get('address', {})
        state_province = (address.get('state') or 
                         address.get('province') or 
                         address.get('region') or 
                         address.get('county'))
        
        print(f"✓ Found state/province: {state_province}")
        
        try:
            cache_set(province_cache, state_province)
        except CacheError as e:
            print(e)
        
        return state_province
    else:
        print("⚠ Could not find state/province information")
        return None


def get_coordinates(city: str, country: str) -> tuple[float, float, str | None]:
    """
    Fetch coordinates for a given city and country using geopy.
    Includes rate limiting to be respectful to the geocoding service.
    
    Args:
        city: City name
        country: Country name
        
    Returns:
        Tuple of (latitude, longitude, state_province)
        
    Raises:
        ValueError: If coordinates cannot be found
    """
    coords = f"coords_{city.lower()}_{country.lower()}"
    cached = cache_get(coords)
    
    if cached is not None:
        print("✓ Using cached coordinates")
        return cached

    print("Looking up coordinates...")
    geolocator = Nominatim(user_agent="city_map_poster", timeout=10)
    
    time.sleep(1)
    
    location = geolocator.geocode(f"{city}, {country}", addressdetails=True)
    
    # Handle async if needed
    if asyncio.iscoroutine(location):
        try:
            location = asyncio.run(location)
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Geocoder returned a coroutine while an event loop is already running.")
            location = loop.run_until_complete(location)
    
    if location:
        addr = getattr(location, "address", None)
        if addr:
            print(f"✓ Found: {addr}")
        else:
            print("✓ Found location (address not available)")

        print(f"✓ Coordinates: {location.latitude}, {location.longitude}")
        
        # Extract state/province from address details
        address = location.raw.get('address', {})
        state_province = (address.get('state') or 
                         address.get('province') or 
                         address.get('region') or 
                         address.get('county'))
        
        result = (location.latitude, location.longitude, state_province)
        try:
            cache_set(coords, result)
        except CacheError as e:
            print(e)
        
        return result
    else:
        raise ValueError(f"Could not find coordinates for {city}, {country}")


def apply_shift(lat: float, lon: float, shift_str: str) -> tuple[float, float]:
    """
    Shift coordinates by distance in a direction.
    Supports 16-point compass rose.
    
    Args:
        lat: Latitude
        lon: Longitude
        shift_str: Shift specification (e.g., '2w', '5ne', '3.5s', '10nw')
        
    Returns:
        Tuple of (new_latitude, new_longitude)
        
    Raises:
        ValueError: If shift format is invalid
        
    Examples:
        >>> apply_shift(40.0, 116.0, '5n')  # 5km north
        >>> apply_shift(40.0, 116.0, '2.5ne')  # 2.5km northeast
    """
    if not shift_str:
        return lat, lon
    
    match = re.match(r'^([\d.]+)([nsew]+)$', shift_str.lower())
    if not match:
        raise ValueError(f"Invalid shift format: '{shift_str}'. Use format like '2w', '5ne', '3.5s', '4nnw'")
    
    distance_km = float(match.group(1))
    direction = match.group(2)
    
    # Calculate bearing - 16-point compass rose
    bearing_map = {
        # Cardinal directions (4-point)
        'n': 0,
        'e': 90,
        's': 180,
        'w': 270,
        # Ordinal directions (8-point)
        'ne': 45,
        'se': 135,
        'sw': 225,
        'nw': 315,
        # Intercardinal directions (16-point)
        'nne': 22.5,
        'ene': 67.5,
        'ese': 112.5,
        'sse': 157.5,
        'ssw': 202.5,
        'wsw': 247.5,
        'wnw': 292.5,
        'nnw': 337.5,
    }
    
    if direction not in bearing_map:
        valid_dirs = ', '.join(sorted(bearing_map.keys()))
        raise ValueError(f"Invalid direction: '{direction}'. Valid directions: {valid_dirs}")
    
    bearing = bearing_map[direction]
    new_point = geodesic(kilometers=distance_km).destination((lat, lon), bearing)
    
    print(f"✓ Shifting center {distance_km}km {direction.upper()} from ({lat:.6f}, {lon:.6f}) to ({new_point.latitude:.6f}, {new_point.longitude:.6f})")
    
    return new_point.latitude, new_point.longitude
