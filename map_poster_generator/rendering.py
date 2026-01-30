"""
Rendering engine for map posters.

Handles:
- Visual styling (colors, line widths)
- Gradients and effects
- Typography and labels
- Final image generation
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.transforms import ScaledTranslation
import osmnx as ox

from .fonts import load_fonts, get_font_with_fallback


POSTERS_DIR = "posters"


def create_gradient_fade(ax, color: str, location: str = 'bottom', zorder: int = 10):
    """
    Create a fade effect at the top or bottom of the map.
    
    Args:
        ax: Matplotlib axes
        color: Color for gradient
        location: 'bottom' or 'top'
        zorder: Z-order for layering
    """
    vals = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((vals, vals))
    
    rgb = mcolors.to_rgb(color)
    my_colors = np.zeros((256, 4))
    my_colors[:, 0] = rgb[0]
    my_colors[:, 1] = rgb[1]
    my_colors[:, 2] = rgb[2]
    
    if location == 'bottom':
        my_colors[:, 3] = np.linspace(1, 0, 256)
        extent_y_start = 0
        extent_y_end = 0.25
    else:
        my_colors[:, 3] = np.linspace(0, 1, 256)
        extent_y_start = 0.75
        extent_y_end = 1.0

    custom_cmap = mcolors.ListedColormap(my_colors)
    
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]
    
    y_bottom = ylim[0] + y_range * extent_y_start
    y_top = ylim[0] + y_range * extent_y_end
    
    ax.imshow(gradient, extent=[xlim[0], xlim[1], y_bottom, y_top], 
              aspect='auto', cmap=custom_cmap, zorder=zorder, origin='lower')


def get_edge_colors_by_type(G, theme: dict) -> list:
    """
    Assign colors to edges based on road type hierarchy.
    
    Args:
        G: NetworkX graph
        theme: Theme dictionary with color definitions
        
    Returns:
        List of colors corresponding to each edge
    """
    edge_colors = []
    
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', 'unclassified')
        
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        if highway in ['motorway', 'motorway_link']:
            color = theme['road_motorway']
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            color = theme['road_primary']
        elif highway in ['secondary', 'secondary_link']:
            color = theme['road_secondary']
        elif highway in ['tertiary', 'tertiary_link']:
            color = theme['road_tertiary']
        elif highway in ['residential', 'living_street', 'unclassified']:
            color = theme['road_residential']
        else:
            color = theme['road_default']
        
        edge_colors.append(color)
    
    return edge_colors


def get_edge_widths_by_type(G) -> list:
    """
    Assign line widths to edges based on road type.
    
    Args:
        G: NetworkX graph
        
    Returns:
        List of widths corresponding to each edge
    """
    edge_widths = []
    
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', 'unclassified')
        
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        if highway in ['motorway', 'motorway_link']:
            width = 1.2
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            width = 1.0
        elif highway in ['secondary', 'secondary_link']:
            width = 0.8
        elif highway in ['tertiary', 'tertiary_link']:
            width = 0.6
        else:
            width = 0.4
        
        edge_widths.append(width)
    
    return edge_widths


def draw_bottom_label(
    ax,
    city_name: str,
    country: str,
    state_province: str | None,
    point: tuple[float, float],
    *,
    theme: dict,
    font_main,
    font_sub,
    font_coords,
    base_xy: tuple[float, float] = (0.5, 0.1),
    line_width: float = 0.2,
    zorder: int = 11
):
    """
    Draw bottom-centered label block (city, divider line, location, coordinates).
    Uses aspect-ratio–independent spacing.
    
    Args:
        ax: Matplotlib axes
        city_name: City name (usually spaced and uppercase)
        country: Country name
        state_province: State/province name or None
        point: Tuple of (latitude, longitude)
        theme: Theme dictionary
        font_main: Font for city name
        font_sub: Font for location
        font_coords: Font for coordinates
        base_xy: Base position for text
        line_width: Width of divider line
        zorder: Z-order for layering
    """
    fig = ax.figure

    def trans(dy_pts):
        return ax.transAxes + ScaledTranslation(
            0, dy_pts / 72, fig.dpi_scale_trans
        )

    # Format coordinates
    lat, lon = point
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    coords = f"{abs(lat):.4f}° {lat_dir} / {abs(lon):.4f}° {lon_dir}"

    x, y = base_xy

    # City name (top)
    ax.text(
        x, y, city_name,
        transform=trans(46),
        ha="center",
        color=theme["text"],
        fontproperties=font_main,
        zorder=zorder
    )

    # Divider line
    ax.plot(
        [x - line_width / 2, x + line_width / 2],
        [y, y],
        transform=trans(29),
        color=theme["text"],
        linewidth=1,
        zorder=zorder
    )

    # State/Province (Country)
    location_text = f"{state_province} ({country})" if state_province else country
    ax.text(
        x, y, location_text,
        transform=ax.transAxes,
        ha="center",
        color=theme["text"],
        fontproperties=font_sub,
        zorder=zorder
    )

    # Coordinates (bottom)
    ax.text(
        x, y, coords,
        transform=trans(-35),
        ha="center",
        color=theme["text"],
        alpha=0.7,
        fontproperties=font_coords,
        zorder=zorder
    )


def render_poster_from_processed_data(
    processed_data: dict, 
    output_file: str, 
    output_format: str,
    theme: dict
) -> None:
    """
    Render a poster using pre-processed data. This is FAST - just applies colors and saves.
    
    Args:
        processed_data: Dictionary from fetch_and_process_map_data()
        output_file: Output file path
        output_format: File format ('png', 'svg', 'pdf')
        theme: Theme dictionary with colors
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
    
    print(f"  Rendering {city} with {theme.get('name', 'current theme')}...")
    
    # Setup plot
    fig, ax = plt.subplots(figsize=aspect_ratio, facecolor=theme['bg'])
    ax.set_facecolor(theme['bg'])
    ax.set_position((0.0, 0.0, 1.0, 1.0))
    
    # Plot water
    if water_polys_proj is not None and not water_polys_proj.empty:
        water_polys_proj.plot(ax=ax, facecolor=theme['water'], edgecolor='none', zorder=1)
    
    # Plot parks
    if parks_polys_proj is not None and not parks_polys_proj.empty:
        parks_polys_proj.plot(ax=ax, facecolor=theme['parks'], edgecolor='none', zorder=2)
    
    # Plot railways
    if normal_rail_proj is not None and not normal_rail_proj.empty:
        normal_rail_proj.plot(ax=ax, color=theme['railway'], linewidth=0.6, zorder=8)
    
    if subway_lines_proj is not None and not subway_lines_proj.empty:
        subway_lines_proj.plot(ax=ax, color="#FF00FF", linewidth=0.8, zorder=9)
    
    # Plot roads with colors
    edge_colors = get_edge_colors_by_type(G_proj, theme)
    edge_widths = get_edge_widths_by_type(G_proj)
    
    ox.plot_graph(
        G_proj, ax=ax, bgcolor=theme['bg'],
        node_size=0,
        edge_color=edge_colors,
        edge_linewidth=edge_widths,
        show=False, close=False
    )
    
    for coll in ax.collections:
        coll.set_zorder(5)
    
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlim(crop_xlim)
    ax.set_ylim(crop_ylim)
    
    # Gradients
    create_gradient_fade(ax, theme['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, theme['gradient_color'], location='top', zorder=10)
    
    # Typography
    spaced_city = "  ".join(list(city.upper()))
    base_font_size = 60
    city_char_count = len(city)
    if city_char_count > 10:
        scale_factor = 10 / city_char_count
        adjusted_font_size = max(base_font_size * scale_factor, 24)
    else:
        adjusted_font_size = base_font_size

    FONTS = load_fonts()
    if FONTS:
        font_main_adjusted = get_font_with_fallback(
            FONTS['bold'], size=adjusted_font_size, weight='bold', 
            verbose=False, text_sample=spaced_city
        )
        subtitle_text = f"{state_province} ({country})" if state_province else country
        font_sub = get_font_with_fallback(
            FONTS['light'], size=22, weight='light',
            verbose=False, text_sample=subtitle_text
        )
        font_coords = get_font_with_fallback(FONTS['regular'], size=14, weight='normal')
        font_attr = get_font_with_fallback(FONTS['light'], size=8, weight='light')
    else:
        font_main_adjusted = get_font_with_fallback(
            None, size=adjusted_font_size, weight='bold', 
            verbose=False, text_sample=spaced_city
        )
        subtitle_text = f"{state_province} ({country})" if state_province else country
        font_sub = get_font_with_fallback(
            None, size=22, weight='light',
            verbose=False, text_sample=subtitle_text
        )
        font_coords = get_font_with_fallback(None, size=14, weight='normal')
        font_attr = get_font_with_fallback(None, size=8, weight='light')

    draw_bottom_label(
        ax, city_name=spaced_city, country=country,
        state_province=state_province, point=point_coords,
        theme=theme, font_main=font_main_adjusted,
        font_sub=font_sub, font_coords=font_coords
    )

    ax.text(0.98, 0.02, "© OpenStreetMap contributors", transform=ax.transAxes,
            color=theme['text'], alpha=0.5, ha='right', va='bottom', 
            fontproperties=font_attr, zorder=11)

    # Save
    fmt = output_format.lower()
    save_kwargs = dict(facecolor=theme["bg"], bbox_inches="tight", pad_inches=0.05)
    if fmt == "png":
        save_kwargs["dpi"] = 200

    plt.savefig(output_file, format=fmt, **save_kwargs)
    plt.close()
    print(f"  ✓ Saved: {os.path.basename(output_file)}")
