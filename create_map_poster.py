#!/usr/bin/env python3
"""
City Map Poster Generator - Main CLI Script

Generate beautiful map posters for any city using OpenStreetMap data.
"""

import sys
import os
import argparse

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from map_poster_generator.cache import set_cache_city, configure_osmnx_cache
from map_poster_generator.fonts import rebuild_font_cache
from map_poster_generator.geocoding import get_coordinates, get_state_province
from map_poster_generator.themes import load_theme, get_available_themes, list_themes_info
from map_poster_generator.data_processing import fetch_and_process_map_data
from map_poster_generator.rendering import render_poster_from_processed_data
from map_poster_generator.svg_renderer import render_svg_poster_from_processed_data
from map_poster_generator.utils import generate_output_filename, parse_aspect_ratio


def print_examples():
    """Print usage examples."""
    print("""
City Map Poster Generator
=========================

Usage:
  python create_map_poster.py --city <city> --country <country> [options]

Examples:
  # Basic usage (automatic geocoding)
  python create_map_poster.py -c "New York" -C "USA" -t noir -d 12000
  python create_map_poster.py -c "Barcelona" -C "Spain" -t warm_beige -d 8000
  
  # Generate ALL themes at once (data processed only once!)
  python create_map_poster.py -c "Tokyo" -C "Japan" -d 15000 --theme all
  python create_map_poster.py -c "Paris" -C "France" -d 10000 --theme all --ratio 16:9
  
  # Generate layered SVG for post-processing in Illustrator/Inkscape
  python create_map_poster.py -c "Tokyo" -C "Japan" -d 15000 --format svg-layered
  python create_map_poster.py -c "Paris" -C "France" -d 10000 --format svg-layered -t noir
  
  # Using manual coordinates (bypasses geocoding for coordinates only)
  python create_map_poster.py -c "Beijing" -C "China" --lat 39.916535 --lon 116.397067 -d 20000
  python create_map_poster.py -c "Tokyo" -C "Japan" --lat 35.6762 --lon 139.6503 -t japanese_ink
  
  # Combining manual coordinates with shift
  python create_map_poster.py -c "Paris" -C "France" --lat 48.8566 --lon 2.3522 --shift 2n -d 10000
  
  # Using shift to adjust framing (with automatic geocoding)
  python create_map_poster.py -c "London" -C "UK" -d 15000 --shift 3.5sw
  python create_map_poster.py -c "Beijing" -C "China" -t parchment -d 18000 --ratio 1:1 --shift 32s
  
  # Generate all themes with shift
  python create_map_poster.py -c "Sydney" -C "Australia" -d 12000 --theme all --shift 3ne
  
  # Waterfront & canals
  python create_map_poster.py -c "Venice" -C "Italy" -t blueprint -d 4000
  python create_map_poster.py -c "Amsterdam" -C "Netherlands" -t ocean -d 6000
  
  # List themes
  python create_map_poster.py --list-themes

Options:
  --city, -c        City name (required)
  --country, -C     Country name (required)
  --lat             Latitude (optional, overrides geocoding for coordinates)
  --lon, --long     Longitude (optional, overrides geocoding for coordinates)
  --theme, -t       Theme name or "all" for all themes (default: feature_based)
  --distance, -d    Map radius in meters (default: 29000)
  --shift, -s       Shift map center (e.g., "2w", "5ne", "3.5s", "4nnw")
  --ratio, -r       Aspect ratio (default: 1:1). Examples: 1:1, 4:3, 16:9, 3:4, 9:16
  --format, -f      Output format: png, svg, pdf (default: png)
  --list-themes     List all available themes
  --rebuild-fonts   Rebuild matplotlib font cache (fixes CJK display issues)
          
Note: When using --lat and --lon:
      - Both must be provided together
      - The script will still geocode the city to get state/province info
      - Only the coordinates are overridden, not the location metadata
          
Shift directions (16-point compass):
  Cardinal: n, e, s, w
  Ordinal: ne, se, sw, nw
  Intercardinal: nne, ene, ese, sse, ssw, wsw, wnw, nnw
  Examples: 2w (2km west), 5ne (5km northeast), 4nnw (4km north-northwest)
          
Aspect ratio examples:
  1:1     Square poster (Instagram)
  4:3     Traditional landscape
  3:4     Traditional portrait
  16:9    Widescreen landscape
  9:16    Widescreen portrait
          
Distance guide:
  4000-6000m   Small/dense cities (Venice, Amsterdam old center)
  8000-12000m  Medium cities, focused downtown (Paris, Barcelona)
  15000-20000m Large metros, full city view (Tokyo, Mumbai)

Performance tip: Use --theme all to generate all themes at once!
  The expensive data processing (OSM download, graph projection, geometry processing)
  happens only ONCE, then all themes are rendered quickly.

Available themes can be found in the 'themes/' directory.
Generated posters are saved to 'posters/' directory.
""")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Generate beautiful map posters for any city",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_map_poster.py --city "New York" --country "USA"
  python create_map_poster.py --city Tokyo --country Japan --theme midnight_blue
  python create_map_poster.py --city Paris --country France --theme all --distance 15000
  python create_map_poster.py --city Beijing --country China --lat 39.916535 --lon 116.397067
  python create_map_poster.py --city London --country UK --shift 3sw --ratio 16:9
  python create_map_poster.py --list-themes
        """
    )
    
    parser.add_argument('--city', '-c', type=str, help='City name (required)')
    parser.add_argument('--country', '-C', type=str, help='Country name (required)')
    parser.add_argument('--lat', type=float, default=None, 
                       help='Latitude (optional, overrides geocoding for coordinates)')
    parser.add_argument('--lon', '--long', type=float, default=None, dest='lon', 
                       help='Longitude (optional, overrides geocoding for coordinates)')
    parser.add_argument('--theme', '-t', type=str, default='feature_based', 
                       help='Theme name or "all" for all themes (default: feature_based)')
    parser.add_argument('--distance', '-d', type=int, default=29000, 
                       help='Map radius in meters (default: 29000)')
    parser.add_argument('--shift', '-s', type=str, default=None, 
                       help='Shift map center. Supports 16-point compass (e.g., "2w", "5ne", "4nnw", "3.5ese")')
    parser.add_argument('--ratio', '-r', type=str, default='1:1', 
                       help='Aspect ratio (default: 1:1). Examples: 1:1, 4:3, 16:9, 3:4, 9:16')
    parser.add_argument('--list-themes', action='store_true', help='List all available themes')
    parser.add_argument('--rebuild-fonts', action='store_true', 
                       help='Rebuild matplotlib font cache (fixes CJK character display issues)')
    parser.add_argument('--format', '-f', default='png', 
                       choices=['png', 'svg', 'pdf', 'svg-layered'],
                       help='Output format for the poster (default: png). Use svg-layered for editable layered SVG')
    
    args = parser.parse_args()
    
    # If no arguments provided, show examples
    if len(sys.argv) == 1:
        print_examples()
        sys.exit(0)
    
    # Rebuild font cache if requested
    if args.rebuild_fonts:
        print("Rebuilding matplotlib font cache...")
        rebuild_font_cache()
        print("\nFont cache rebuilt. Try running your command again.")
        sys.exit(0)
    
    # List themes if requested
    if args.list_themes:
        list_themes_info()
        sys.exit(0)
    
    # Validate required arguments
    if not args.city or not args.country:
        print("Error: --city and --country are required.\n")
        print_examples()
        sys.exit(1)
    
    # Validate lat/lon - both must be provided if either is provided
    if (args.lat is not None) != (args.lon is not None):
        print("Error: Both --lat and --lon must be provided together.\n")
        sys.exit(1)
    
    # Validate theme exists (unless "all" is specified)
    available_themes = get_available_themes()
    if args.theme.lower() == 'all':
        print(f"\n{'='*50}")
        print(f"Will generate posters for ALL {len(available_themes)} themes")
        print(f"{'='*50}")
        themes_to_process = available_themes
    elif args.theme not in available_themes:
        print(f"Error: Theme '{args.theme}' not found.")
        print(f"Available themes: {', '.join(available_themes)}")
        sys.exit(1)
    else:
        themes_to_process = [args.theme]
    
    print("=" * 50)
    print("City Map Poster Generator")
    print("=" * 50)
    
    # Set up city-based cache directory
    cache_dir = set_cache_city(args.city, args.country)
    configure_osmnx_cache(cache_dir)
    
    # Get coordinates and generate poster(s)
    try:
        # Use provided coordinates or fetch them
        if args.lat is not None and args.lon is not None:
            print(f"Using provided coordinates: {args.lat}, {args.lon}")
            
            # Still fetch state/province info using city and country
            state_province = get_state_province(args.city, args.country)
            
            coords = (args.lat, args.lon, state_province)
        else:
            # Standard geocoding - gets coordinates and state/province
            coords = get_coordinates(args.city, args.country)
            print(f"Coordinates for {args.city}, {args.country}: {coords}")
        
        # Parse aspect ratio
        figsize = parse_aspect_ratio(args.ratio)
        print(f"Using aspect ratio: {args.ratio} ({figsize[0]:.1f}\" x {figsize[1]:.1f}\")")
        
        # FETCH AND PROCESS DATA ONCE (expensive)
        processed_data = fetch_and_process_map_data(
            args.city, args.country, coords, args.distance, figsize, shift=args.shift
        )
        
        # RENDER FOR EACH THEME (cheap)
        print(f"\n{'='*50}")
        print(f"Rendering {len(themes_to_process)} theme(s)...")
        print(f"{'='*50}\n")
        
        generated_files = []
        for i, theme_name in enumerate(themes_to_process, 1):
            if len(themes_to_process) > 1:
                print(f"[{i}/{len(themes_to_process)}] Theme: {theme_name}")
            
            # Load theme (just sets colors)
            theme = load_theme(theme_name)
            
            # Generate output filename
            output_file = generate_output_filename(
                args.city, theme_name, args.distance, args.format, shift=args.shift
            )
            
            # Render with this theme
            if args.format == 'svg-layered':
                # Use SVG layered renderer (uses aspect_ratio from processed_data)
                render_svg_poster_from_processed_data(
                    processed_data, output_file, theme
                )
            else:
                # Use standard PNG/PDF renderer
                render_poster_from_processed_data(
                    processed_data, output_file, args.format, theme
                )
            
            generated_files.append(output_file)
        
        print("\n" + "=" * 50)
        print("✓ Poster generation complete!")
        if len(generated_files) > 1:
            print(f"✓ Generated {len(generated_files)} posters:")
            for f in generated_files:
                print(f"  • {os.path.basename(f)}")
        else:
            print(f"✓ Saved: {os.path.basename(generated_files[0])}")
        print("=" * 50)
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
