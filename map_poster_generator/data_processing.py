"""
Data processing pipeline for map poster generation.

Handles the expensive one-time processing of OSM data:
- Fetching all data from OSM
- Projecting graphs and features
- Calculating crop limits
- Preparing data for rendering
"""

import osmnx as ox
import matplotlib.pyplot as plt
from tqdm import tqdm
from matplotlib.figure import Figure
from networkx import MultiDiGraph

from .geocoding import apply_shift
from .osm_data import fetch_graph, fetch_features, project_and_filter_features


def get_crop_limits(G: MultiDiGraph, fig: Figure) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Determine cropping limits to maintain aspect ratio of the figure.

    This function calculates the extents of the graph's nodes and adjusts
    the x and y limits to match the aspect ratio of the provided figure.
    
    Args:
        G: The graph to be plotted
        fig: The matplotlib figure object
        
    Returns:
        Tuple of x and y limits for cropping: ((min_x, max_x), (min_y, max_y))
    """
    # Compute node extents in projected coordinates
    xs = [data['x'] for _, data in G.nodes(data=True)]
    ys = [data['y'] for _, data in G.nodes(data=True)]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    x_range = maxx - minx
    y_range = maxy - miny

    fig_width, fig_height = fig.get_size_inches()
    desired_aspect = fig_width / fig_height
    current_aspect = x_range / y_range

    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2

    if current_aspect > desired_aspect:
        # Too wide, need to crop horizontally
        desired_x_range = y_range * desired_aspect
        new_minx = center_x - desired_x_range / 2
        new_maxx = center_x + desired_x_range / 2
        new_miny, new_maxy = miny, maxy
        crop_xlim = (new_minx, new_maxx)
        crop_ylim = (new_miny, new_maxy)
    elif current_aspect < desired_aspect:
        # Too tall, need to crop vertically
        desired_y_range = x_range / desired_aspect
        new_miny = center_y - desired_y_range / 2
        new_maxy = center_y + desired_y_range / 2
        new_minx, new_maxx = minx, maxx
        crop_xlim = (new_minx, new_maxx)
        crop_ylim = (new_miny, new_maxy)
    else:
        # Otherwise, keep original extents (no horizontal crop)
        crop_xlim = (minx, maxx)
        crop_ylim = (miny, maxy)
    
    return crop_xlim, crop_ylim


def fetch_and_process_map_data(
    city: str, 
    country: str, 
    point: tuple, 
    dist: int, 
    aspect_ratio: tuple[float, float], 
    shift: str | None = None
) -> dict:
    """
    Fetch and process all map data. This is the EXPENSIVE part done ONCE.
    
    Args:
        city: City name
        country: Country name
        point: Tuple of (lat, lon, state_province) or (lat, lon)
        dist: Distance in meters
        aspect_ratio: Tuple of (width, height) in inches
        shift: Optional shift string (e.g., '5n', '3.5sw')
        
    Returns:
        Dict with all processed data ready for rendering
    """
    print(f"\n{'='*50}")
    print(f"Fetching and processing map data for {city}, {country}...")
    print(f"{'='*50}")
    
    # Unpack coordinates and state/province
    if isinstance(point, tuple) and len(point) == 3:
        coords_lat, coords_lon, state_province = point
    else:
        coords_lat, coords_lon = point[:2]
        state_province = None
    
    # Apply shift if provided
    if shift:
        coords_lat, coords_lon = apply_shift(coords_lat, coords_lon, shift)
    
    point_coords = (coords_lat, coords_lon)
    
    # Fetch OSM data (uses cache)
    with tqdm(total=4, desc="Fetching map data", unit="step", 
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
        
        pbar.set_description("Downloading street network")
        G = fetch_graph(point_coords, dist)
        if G is None:
            raise RuntimeError("Failed to retrieve street network data.")
        pbar.update(1)
        
        pbar.set_description("Downloading water features")
        water = fetch_features(point_coords, dist, 
                             {'natural': 'water', 'waterway': 'riverbank'}, 'water')
        pbar.update(1)
        
        pbar.set_description("Downloading parks/green spaces")
        parks = fetch_features(point_coords, dist, 
                             {'leisure': 'park', 'landuse': 'grass'}, 'parks')
        pbar.update(1)

        pbar.set_description("Downloading railways")
        railways = fetch_features(point_coords, dist, {'railway': 'rail'}, 'railways')
        pbar.update(1)
    
    print("✓ Data fetched. Now processing geometries (this may take a moment)...")
    
    # PROJECT GRAPH (expensive!)
    G_proj = ox.project_graph(G)
    
    # PROCESS WATER (expensive!)
    water_polys_proj = project_and_filter_features(
        water, G_proj, ['Polygon', 'MultiPolygon']
    )
    
    # PROCESS PARKS (expensive!)
    parks_polys_proj = project_and_filter_features(
        parks, G_proj, ['Polygon', 'MultiPolygon']
    )
    
    # PROCESS RAILWAYS (expensive!)
    normal_rail_proj = None
    subway_lines_proj = None
    if railways is not None and not railways.empty:
        railways_line = railways[railways.geometry.type.isin(['LineString', 'MultiLineString'])]
        if not railways_line.empty:
            # Separate subway/light rail from normal rail
            subway_lines = railways_line[
                (railways_line['railway'].isin(['subway', 'light_rail'])) |
                (railways_line.get('subway') == 'yes')
            ]
            normal_rail = railways_line.drop(subway_lines.index)
            
            if not normal_rail.empty:
                normal_rail_proj = project_and_filter_features(
                    normal_rail, G_proj, ['LineString', 'MultiLineString']
                )
            
            if not subway_lines.empty:
                subway_lines_proj = project_and_filter_features(
                    subway_lines, G_proj, ['LineString', 'MultiLineString']
                )
    
    # Create a temporary figure to calculate crop limits
    fig_temp, _ = plt.subplots(figsize=aspect_ratio)
    crop_xlim, crop_ylim = get_crop_limits(G_proj, fig_temp)
    plt.close(fig_temp)
    
    print("✓ All data processed and ready for rendering!")
    
    # Return everything needed for rendering
    return {
        'city': city,
        'country': country,
        'point_coords': point_coords,
        'state_province': state_province,
        'G_proj': G_proj,
        'water_polys_proj': water_polys_proj,
        'parks_polys_proj': parks_polys_proj,
        'normal_rail_proj': normal_rail_proj,
        'subway_lines_proj': subway_lines_proj,
        'crop_xlim': crop_xlim,
        'crop_ylim': crop_ylim,
        'aspect_ratio': aspect_ratio
    }
