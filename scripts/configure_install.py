"""Write first-run defaults without overwriting an existing player's settings."""
import argparse
import hashlib
import json
from pathlib import Path

DEFAULTS = '''# Midnight Club L.A. Recompiled: first-run settings. In-game menus save your later choices.
mcla_ptbr = true
mcla_aspect_ratio = "auto"
mcla_hud_aspect = true
mcla_hud_edges = true
mcla_gps_full_width = true
mcla_world_icon_aspect = true
mcla_panel_aspect = true
mcla_phone_aspect = true
mcla_garage_aspect = true
mcla_gps_icon_aspect = true
mcla_gpu_backend = "any"
mcla_anti_aliasing = "msaa"
temporal_aa_quality = "native"
frame_generation = "off"
frame_generation_present = "tearing"
frame_generation_edge_pixels = 2
resolution_scale = 1
mcla_fps = 30
vsync = true
mcla_motion_blur = true
mcla_depth_of_field = true
mcla_fullscreen_blur = true
mcla_button_prompts = "xbox"
mcla_player_name = "User"
fullscreen = true
'''

def configure(build):
    build.mkdir(parents=True, exist_ok=True)
    settings = build / 'mcla.toml'
    try:
        with settings.open('x', encoding='utf8') as stream:
            stream.write(DEFAULTS)
        print('Created first-run settings; enable Frame Generation in-game on compatible hardware.')
    except FileExistsError:
        print('Kept existing mcla.toml and save paths.')
    executable = build / 'mcla.exe'
    if executable.exists():
        with executable.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        (build / 'launcher_capabilities.json').write_text(json.dumps(
            dict(aspect_patch=1, exe_sha256=digest), indent=2), encoding='utf8')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    configure(parser.parse_args().build.resolve())
