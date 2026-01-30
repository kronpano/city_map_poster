"""
SVG Rendering engine for map posters with proper layering.

Handles:
- Creating properly layered SVG output
- Grouping elements by type (water, parks, roads by class, railways)
- Preserving individual features for post-processing
- Adding metadata and IDs for easy selection in Illustrator/Inkscape
"""

import os
from xml.etree import ElementTree as ET
from xml.dom import minidom
import numpy as np

from .fonts import load_fonts, get_font_with_fallback


POSTERS_DIR = "posters"


def prettify_xml(elem):
    """
    Return a pretty-printed XML string for the Element.
    
    Args:
        elem: XML Element
        
    Returns:
        Pretty-printed XML string
    """
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def create_svg_root(width, height, theme):
    """
    Create SVG root element with proper viewBox and styling.
    
    Args:
        width: Width in pixels
        height: Height in pixels
        theme: Theme dictionary
        
    Returns:
        SVG root element
    """
    svg = ET.Element('svg', {
        'xmlns': 'http://www.w3.org/2000/svg',
        'xmlns:xlink': 'http://www.w3.org/1999/xlink',
        'viewBox': f'0 0 {width} {height}',
        'width': str(width),
        'height': str(height)
    })
    
    # Add background
    bg_rect = ET.SubElement(svg, 'rect', {
        'id': 'background',
        'x': '0',
        'y': '0',
        'width': str(width),
        'height': str(height),
        'fill': theme['bg']
    })
    
    return svg


def add_defs_section(svg, theme):
    """
    Add definitions section with gradients and filters.
    
    Args:
        svg: SVG root element
        theme: Theme dictionary
    """
    defs = ET.SubElement(svg, 'defs')
    
    # Bottom gradient (fades from transparent to color)
    gradient_bottom = ET.SubElement(defs, 'linearGradient', {
        'id': 'fadeGradientBottom',
        'x1': '0%',
        'y1': '0%',
        'x2': '0%',
        'y2': '100%'
    })
    
    ET.SubElement(gradient_bottom, 'stop', {
        'offset': '0%',
        'style': f'stop-color:{theme["gradient_color"]};stop-opacity:0'
    })
    
    ET.SubElement(gradient_bottom, 'stop', {
        'offset': '100%',
        'style': f'stop-color:{theme["gradient_color"]};stop-opacity:1'
    })
    
    # Top gradient (fades from color to transparent)
    gradient_top = ET.SubElement(defs, 'linearGradient', {
        'id': 'fadeGradientTop',
        'x1': '0%',
        'y1': '0%',
        'x2': '0%',
        'y2': '100%'
    })
    
    ET.SubElement(gradient_top, 'stop', {
        'offset': '0%',
        'style': f'stop-color:{theme["gradient_color"]};stop-opacity:1'
    })
    
    ET.SubElement(gradient_top, 'stop', {
        'offset': '100%',
        'style': f'stop-color:{theme["gradient_color"]};stop-opacity:0'
    })



def transform_coordinates(coords, xlim, ylim, width, height):
    """
    Transform geographic coordinates to SVG pixel coordinates.
    
    Args:
        coords: Array of coordinates
        xlim: Tuple of (min_x, max_x)
        ylim: Tuple of (min_y, max_y)
        width: SVG width
        height: SVG height
        
    Returns:
        Transformed coordinates
    """
    x_scale = width / (xlim[1] - xlim[0])
    y_scale = height / (ylim[1] - ylim[0])
    
    # Transform and flip Y (SVG has origin at top-left)
    x = (coords[:, 0] - xlim[0]) * x_scale
    y = height - (coords[:, 1] - ylim[0]) * y_scale
    
    return np.column_stack([x, y])


def coords_to_path_data(coords):
    """
    Convert coordinate array to SVG path data string.
    
    Args:
        coords: Nx2 array of coordinates
        
    Returns:
        SVG path data string
    """
    if len(coords) == 0:
        return ""
    
    path_parts = [f"M {coords[0][0]:.2f},{coords[0][1]:.2f}"]
    
    for coord in coords[1:]:
        path_parts.append(f"L {coord[0]:.2f},{coord[1]:.2f}")
    
    return " ".join(path_parts)


def add_polygon_layer(svg, gdf, layer_id, layer_class, fill_color, xlim, ylim, width, height):
    """
    Add a layer of polygon features to SVG.
    
    Args:
        svg: SVG root element
        gdf: GeoDataFrame with polygon geometries
        layer_id: ID for the layer group
        layer_class: Class for the layer group
        fill_color: Fill color
        xlim: X limits
        ylim: Y limits
        width: SVG width
        height: SVG height
    """
    if gdf is None or gdf.empty:
        return
    
    layer_group = ET.SubElement(svg, 'g', {
        'id': layer_id,
        'class': layer_class,
        'fill': fill_color,
        'fill-rule': 'evenodd',
        'stroke': 'none'
    })
    
    for idx, feature in gdf.iterrows():
        geom = feature.geometry
        
        # Handle MultiPolygon
        if geom.geom_type == 'MultiPolygon':
            for poly_idx, polygon in enumerate(geom.geoms):
                coords = np.array(polygon.exterior.coords)
                transformed = transform_coordinates(coords, xlim, ylim, width, height)
                path_data = coords_to_path_data(transformed)
                
                ET.SubElement(layer_group, 'path', {
                    'id': f'{layer_id}-{idx}-{poly_idx}',
                    'class': f'{layer_class}-feature',
                    'd': path_data
                })
        
        # Handle Polygon
        elif geom.geom_type == 'Polygon':
            coords = np.array(geom.exterior.coords)
            transformed = transform_coordinates(coords, xlim, ylim, width, height)
            path_data = coords_to_path_data(transformed)
            
            ET.SubElement(layer_group, 'path', {
                'id': f'{layer_id}-{idx}',
                'class': f'{layer_class}-feature',
                'd': path_data
            })


def add_linestring_layer(svg, gdf, layer_id, layer_class, stroke_color, stroke_width, xlim, ylim, width, height):
    """
    Add a layer of linestring features (roads, railways) to SVG.
    
    Args:
        svg: SVG root element
        gdf: GeoDataFrame with linestring geometries
        layer_id: ID for the layer group
        layer_class: Class for the layer group
        stroke_color: Stroke color
        stroke_width: Stroke width
        xlim: X limits
        ylim: Y limits
        width: SVG width
        height: SVG height
    """
    if gdf is None or gdf.empty:
        return
    
    layer_group = ET.SubElement(svg, 'g', {
        'id': layer_id,
        'class': layer_class,
        'fill': 'none',
        'stroke': stroke_color,
        'stroke-width': str(stroke_width),
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round'
    })
    
    for idx, feature in gdf.iterrows():
        geom = feature.geometry
        
        # Handle MultiLineString
        if geom.geom_type == 'MultiLineString':
            for line_idx, line in enumerate(geom.geoms):
                coords = np.array(line.coords)
                transformed = transform_coordinates(coords, xlim, ylim, width, height)
                path_data = coords_to_path_data(transformed)
                
                ET.SubElement(layer_group, 'path', {
                    'id': f'{layer_id}-{idx}-{line_idx}',
                    'class': f'{layer_class}-feature',
                    'd': path_data
                })
        
        # Handle LineString
        elif geom.geom_type == 'LineString':
            coords = np.array(geom.coords)
            transformed = transform_coordinates(coords, xlim, ylim, width, height)
            path_data = coords_to_path_data(transformed)
            
            ET.SubElement(layer_group, 'path', {
                'id': f'{layer_id}-{idx}',
                'class': f'{layer_class}-feature',
                'd': path_data
            })


def add_roads_by_type(svg, G_proj, theme, xlim, ylim, width, height):
    """
    Add road layers, separated by road type.
    
    Args:
        svg: SVG root element
        G_proj: Projected graph
        theme: Theme dictionary
        xlim: X limits
        ylim: Y limits
        width: SVG width
        height: SVG height
    """
    # Group roads by type
    road_types = {
        'motorway': {'edges': [], 'color': theme['road_motorway'], 'width': 1.2},
        'primary': {'edges': [], 'color': theme['road_primary'], 'width': 1.0},
        'secondary': {'edges': [], 'color': theme['road_secondary'], 'width': 0.8},
        'tertiary': {'edges': [], 'color': theme['road_tertiary'], 'width': 0.6},
        'residential': {'edges': [], 'color': theme['road_residential'], 'width': 0.4},
        'other': {'edges': [], 'color': theme['road_default'], 'width': 0.4}
    }
    
    for u, v, key, data in G_proj.edges(keys=True, data=True):
        highway = data.get('highway', 'unclassified')
        
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        # Get geometry
        if 'geometry' in data:
            geom = data['geometry']
        else:
            # Create line from nodes
            u_data = G_proj.nodes[u]
            v_data = G_proj.nodes[v]
            coords = [(u_data['x'], u_data['y']), (v_data['x'], v_data['y'])]
            geom = coords
        
        # Classify road
        if highway in ['motorway', 'motorway_link']:
            road_types['motorway']['edges'].append(geom)
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            road_types['primary']['edges'].append(geom)
        elif highway in ['secondary', 'secondary_link']:
            road_types['secondary']['edges'].append(geom)
        elif highway in ['tertiary', 'tertiary_link']:
            road_types['tertiary']['edges'].append(geom)
        elif highway in ['residential', 'living_street', 'unclassified']:
            road_types['residential']['edges'].append(geom)
        else:
            road_types['other']['edges'].append(geom)
    
    # Create layer for each road type
    for road_type, data in road_types.items():
        if not data['edges']:
            continue
        
        layer_group = ET.SubElement(svg, 'g', {
            'id': f'roads-{road_type}',
            'class': f'roads-layer roads-{road_type}',
            'fill': 'none',
            'stroke': data['color'],
            'stroke-width': str(data['width']),
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round'
        })
        
        for idx, edge_geom in enumerate(data['edges']):
            # Handle shapely geometry
            if hasattr(edge_geom, 'coords'):
                coords = np.array(edge_geom.coords)
            else:
                coords = np.array(edge_geom)
            
            transformed = transform_coordinates(coords, xlim, ylim, width, height)
            path_data = coords_to_path_data(transformed)
            
            ET.SubElement(layer_group, 'path', {
                'id': f'road-{road_type}-{idx}',
                'class': f'road-{road_type}-segment',
                'd': path_data
            })


def add_text_layer(svg, city, country, state_province, point_coords, theme, width, height):
    """
    Add text labels for city name and metadata.
    Font sizes scale proportionally with image size.
    
    Args:
        svg: SVG root element
        city: City name
        country: Country name
        state_province: State/province or None
        point_coords: Tuple of (lat, lon)
        theme: Theme dictionary
        width: SVG width
        height: SVG height
    """
    text_group = ET.SubElement(svg, 'g', {
        'id': 'labels',
        'class': 'text-layer'
    })
    
    # Scale font sizes based on image dimensions
    # Base sizes are for 4800px width (16" @ 300dpi)
    base_width = 4800
    scale_factor = width / base_width
    
    font_city = int(60 * scale_factor)
    font_location = int(22 * scale_factor)
    font_coords = int(14 * scale_factor)
    font_attr = int(8 * scale_factor)
    
    # Adjust city font size for long city names
    city_char_count = len(city)
    if city_char_count > 10:
        city_scale = 10 / city_char_count
        font_city = max(int(font_city * city_scale), int(24 * scale_factor))
    
    # City name (spaced and uppercase)
    spaced_city = "  ".join(list(city.upper()))
    
    city_text = ET.SubElement(text_group, 'text', {
        'id': 'city-name',
        'x': str(width / 2),
        'y': str(height * 0.92),
        'text-anchor': 'middle',
        'font-family': 'Roboto, sans-serif',
        'font-weight': 'bold',
        'font-size': str(font_city),
        'fill': theme['text']
    })
    city_text.text = spaced_city
    
    # Divider line (scale width too)
    line_width = width * 0.2
    ET.SubElement(text_group, 'line', {
        'id': 'divider-line',
        'x1': str((width - line_width) / 2),
        'y1': str(height * 0.93),
        'x2': str((width + line_width) / 2),
        'y2': str(height * 0.93),
        'stroke': theme['text'],
        'stroke-width': str(max(1, int(2 * scale_factor)))
    })
    
    # Location (state/province and country)
    location_text = f"{state_province} ({country})" if state_province else country
    location = ET.SubElement(text_group, 'text', {
        'id': 'location',
        'x': str(width / 2),
        'y': str(height * 0.95),
        'text-anchor': 'middle',
        'font-family': 'Roboto, sans-serif',
        'font-weight': '300',
        'font-size': str(font_location),
        'fill': theme['text']
    })
    location.text = location_text
    
    # Coordinates
    lat, lon = point_coords
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    coords_text = f"{abs(lat):.4f}° {lat_dir} / {abs(lon):.4f}° {lon_dir}"
    
    coords = ET.SubElement(text_group, 'text', {
        'id': 'coordinates',
        'x': str(width / 2),
        'y': str(height * 0.97),
        'text-anchor': 'middle',
        'font-family': 'Roboto, sans-serif',
        'font-size': str(font_coords),
        'fill': theme['text'],
        'opacity': '0.7'
    })
    coords.text = coords_text
    
    # Attribution
    attribution = ET.SubElement(text_group, 'text', {
        'id': 'attribution',
        'x': str(width * 0.98),
        'y': str(height * 0.98),
        'text-anchor': 'end',
        'font-family': 'Roboto, sans-serif',
        'font-size': str(font_attr),
        'fill': theme['text'],
        'opacity': '0.5'
    })
    attribution.text = "© OpenStreetMap contributors"


def render_svg_poster_from_processed_data(
    processed_data: dict,
    output_file: str,
    theme: dict,
    dpi: int = 300
) -> None:
    """
    Render a layered SVG poster using pre-processed data.
    
    Args:
        processed_data: Dictionary from fetch_and_process_map_data()
        output_file: Output file path
        theme: Theme dictionary with colors
        dpi: DPI for converting inches to pixels (default: 300)
    """
    city = processed_data['city']
    country = processed_data['country']
    point_coords = processed_data['point_coords']
    state_province = processed_data['state_province']
    G_proj = processed_data['G_proj']
    water_polys_proj = processed_data['water_polys_proj']
    parks_polys_proj = processed_data['parks_polys_proj']
    normal_rail_proj = processed_data['normal_rail_proj']
    subway_lines_proj = processed_data['subway_lines_proj']
    crop_xlim = processed_data['crop_xlim']
    crop_ylim = processed_data['crop_ylim']
    aspect_ratio = processed_data['aspect_ratio']
    
    # Calculate pixel dimensions from aspect ratio (in inches) and DPI
    width = int(aspect_ratio[0] * dpi)
    height = int(aspect_ratio[1] * dpi)
    
    print(f"  Rendering layered SVG for {city} with {theme.get('name', 'current theme')}...")
    print(f"  SVG dimensions: {width}x{height}px ({aspect_ratio[0]}\" x {aspect_ratio[1]}\" @ {dpi} DPI)")
    
    # Create SVG root
    svg = create_svg_root(width, height, theme)
    
    # Add definitions
    add_defs_section(svg, theme)
    
    # Layer 1: Water
    add_polygon_layer(
        svg, water_polys_proj, 'water', 'water-layer',
        theme['water'], crop_xlim, crop_ylim, width, height
    )
    
    # Layer 2: Parks
    add_polygon_layer(
        svg, parks_polys_proj, 'parks', 'parks-layer',
        theme['parks'], crop_xlim, crop_ylim, width, height
    )
    
    # Layer 3: Roads (separated by type)
    add_roads_by_type(svg, G_proj, theme, crop_xlim, crop_ylim, width, height)
    
    # Layer 4: Normal railways
    add_linestring_layer(
        svg, normal_rail_proj, 'railways', 'railway-layer',
        theme['railway'], 0.6, crop_xlim, crop_ylim, width, height
    )
    
    # Layer 5: Subway/light rail
    add_linestring_layer(
        svg, subway_lines_proj, 'subway', 'subway-layer',
        '#FF00FF', 0.8, crop_xlim, crop_ylim, width, height
    )
    
    # Layer 6: Gradient fades (top and bottom)
    gradient_group = ET.SubElement(svg, 'g', {
        'id': 'gradients',
        'class': 'gradient-layer'
    })
    
    # Bottom gradient fade (0% to 25% of height)
    bottom_gradient = ET.SubElement(gradient_group, 'rect', {
        'id': 'gradient-bottom',
        'x': '0',
        'y': str(height * 0.75),
        'width': str(width),
        'height': str(height * 0.25),
        'fill': 'url(#fadeGradientBottom)'
    })
    
    # Top gradient fade (75% to 100% of height)
    top_gradient = ET.SubElement(gradient_group, 'rect', {
        'id': 'gradient-top',
        'x': '0',
        'y': '0',
        'width': str(width),
        'height': str(height * 0.25),
        'fill': 'url(#fadeGradientTop)'
    })
    
    # Layer 7: Text labels
    add_text_layer(svg, city, country, state_province, point_coords, theme, width, height)
    
    # Save SVG
    svg_string = prettify_xml(svg)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(svg_string)
    
    print(f"  ✓ Saved layered SVG: {os.path.basename(output_file)}")
    print(f"     Layers: water, parks, roads (motorway/primary/secondary/tertiary/residential), railways, subway, labels")
