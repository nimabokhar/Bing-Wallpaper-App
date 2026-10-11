#!/usr/bin/env python3
"""Regenerates the PNG and ICO exports from icon.svg. Needs `pip install cairosvg` and ImageMagick."""
import pathlib, subprocess
import cairosvg

here = pathlib.Path(__file__).parent
png = here / "png"
png.mkdir(exist_ok=True)
sizes = [16, 24, 32, 48, 64, 128, 256, 512, 1024]
for size in sizes:
    cairosvg.svg2png(url=str(here / "icon.svg"), write_to=str(png / f"bing-wallpaper-{size}.png"),
                     output_width=size, output_height=size)
subprocess.run(["convert", *[str(png / f"bing-wallpaper-{s}.png") for s in (16, 24, 32, 48, 64, 128, 256)],
                str(here / "bing-wallpaper.ico")], check=True)
