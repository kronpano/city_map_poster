"""
OSM data fetching and processing.

Handles:
- Downloading street networks
- Downloading geographic features (water, parks, railways)
- Graph projection
- Feature filtering and projection
"""

import time
from typing import cast
import osmnx as ox
from networkx import MultiDiGraph
from geopandas import GeoDataFrame

from .cache import cache_get, cache_set, CacheError


def fetch_graph(point: tuple[float, float], dist: int) -> MultiDiGraph | None:
    """
    Fetch street network graph from OSM.
    
    Args:
        point: Tuple of (latitude, longitude)
        dist: Distance in meters for bounding box
        
    Returns:
        NetworkX MultiDiGraph or None if fetch fails
    """
    lat, lon = point
    graph = f"graph_{lat}_{lon}_{dist}"
    cached = cache_get(graph)
    
    if cached is not None:
        print("✓ Using cached street network")
        return cast(MultiDiGraph, cached)

    try:
        G = ox.graph_from_point(point, dist=dist, dist_type='bbox', network_type='all')
        # Rate limit between requests
        time.sleep(0.5)
        try:
            cache_set(graph, G)
        except CacheError as e:
            print(e)
        return G
    except Exception as e:
        print(f"OSMnx error while fetching graph: {e}")
        return None


def fetch_features(point: tuple[float, float], dist: int, tags: dict, name: str) -> GeoDataFrame | None:
    """
    Fetch geographic features from OSM.
    
    Args:
        point: Tuple of (latitude, longitude)
        dist: Distance in meters for bounding box
        tags: OSM tags to filter features
        name: Name for cache key
        
    Returns:
        GeoDataFrame or None if fetch fails
    """
    lat, lon = point
    tag_str = "_".join(tags.keys())
    features = f"{name}_{lat}_{lon}_{dist}_{tag_str}"
    cached = cache_get(features)
    
    if cached is not None:
        print(f"✓ Using cached {name}")
        return cast(GeoDataFrame, cached)

    try:
        data = ox.features_from_point(point, tags=tags, dist=dist)
        # Rate limit between requests
        time.sleep(0.3)
        try:
            cache_set(features, data)
        except CacheError as e:
            print(e)
        return data
    except Exception as e:
        print(f"OSMnx error while fetching features: {e}")
        return None


def project_and_filter_features(features: GeoDataFrame, G_proj: MultiDiGraph, geometry_types: list[str]) -> GeoDataFrame | None:
    """
    Project features to match graph CRS and filter by geometry type.
    
    Args:
        features: Raw GeoDataFrame from OSM
        G_proj: Projected graph to match CRS with
        geometry_types: List of geometry types to keep (e.g., ['Polygon', 'MultiPolygon'])
        
    Returns:
        Projected and filtered GeoDataFrame or None
    """
    if features is None or features.empty:
        return None
    
    # Filter by geometry type
    filtered = features[features.geometry.type.isin(geometry_types)]
    
    if filtered.empty:
        return None
    
    # Project to match graph CRS
    try:
        projected = ox.projection.project_gdf(filtered)
    except Exception:
        projected = filtered.to_crs(G_proj.graph['crs'])
    
    return projected
