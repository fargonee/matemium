#!/usr/bin/env python3
"""Matemium CLI — simple commands for rendering canvas videos."""

from __future__ import annotations

import argparse
import sys

from .__version__ import __version__
from .paths import ensure_on_path, output_media_dir
from .projects import (
    default_scene,
    list_projects,
    list_scenes,
    load_scene_class,
    scaffold_project,
)
from .render import render_scene_class

# Built-in demo shortcuts (project demo, scene name)
DEMO_SCENES = {
    "portrait": "PortraitDemo",
    "reels": "PortraitDemo",
    "landscape": "LandscapeDemo",
    "youtube": "LandscapeDemo",
    "builder": "BuilderDemo",
    "tictactoe": "TicTacToeTutorial",
    "ttt": "TicTacToeTutorial",
    "tutorial": "TicTacToeTutorial",
    "flex": "TicTacToeTutorial",
}


def cmd_demo(args: argparse.Namespace) -> int:
    variant = (args.variant or "portrait").lower()
    scene = DEMO_SCENES.get(variant)
    if not scene:
        print(f"Unknown demo variant: {variant}. Choose: {', '.join(DEMO_SCENES)}")
        return 1
    return cmd_render(
        argparse.Namespace(
            project="demo",
            scene=scene,
            quality=args.quality,
            output=args.output,
            resolution=args.resolution,
        )
    )


def cmd_render(args: argparse.Namespace) -> int:
    project = args.project
    scene_name = args.scene or default_scene(project)
    scene_cls = load_scene_class(project, scene_name)

    resolution = None
    if args.resolution and args.resolution.lower() != "native":
        try:
            w, h = args.resolution.split(",")
            resolution = (int(w), int(h))
        except Exception:
            print("--resolution must be WIDTH,HEIGHT or 'native'")
            return 1

    video = render_scene_class(
        scene_cls,
        project=project,
        output_name=args.output,
        quality=args.quality,
        resolution=resolution,
    )
    print(f"\nDone.\n  Project: {project}\n  Scene:   {scene_name}\n  Video:   {video}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    projects = list_projects()
    if not projects:
        print("No projects found. Create one: matemium new my_video")
        return 0
    print("Projects:")
    for slug in projects:
        scenes = list_scenes(slug)
        out = output_media_dir(slug)
        print(f"  {slug}")
        print(f"    scenes: {', '.join(scenes)}")
        print(f"    output: {out}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    path = scaffold_project(args.name)
    print(f"Created project: {path}")
    print(f"  Edit:  projects/{args.name}/scenes.py")
    print(f"  Render: matemium render {args.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="matemium",
        description="Matemium — render structured visual explanations from projects/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quick start:
  matemium demo              # test portrait demo → outputs/demo/
  matemium demo landscape    # landscape demo
  matemium list              # show all projects
  matemium new my_topic      # scaffold a new video project
  matemium render my_topic   # render projects/my_topic/scenes.py
        """.strip(),
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_demo = sub.add_parser("demo", help="Render the built-in test demo (default: portrait)")
    p_demo.add_argument(
        "variant",
        nargs="?",
        default="portrait",
        help="portrait | landscape | builder | tictactoe (multi-scenario tutorial)",
    )
    p_demo.add_argument(
        "-q",
        "--quality",
        default="low",
        choices=["preview", "draft", "low", "medium", "high", "final"],
        help="preview | draft | low | medium | high | final",
    )
    p_demo.add_argument("-o", "--output", default=None)
    p_demo.add_argument("-r", "--resolution", default=None)
    p_demo.set_defaults(func=cmd_demo)

    p_render = sub.add_parser("render", help="Render a project scene")
    p_render.add_argument("project", help="Project folder name under projects/")
    p_render.add_argument("scene", nargs="?", default=None, help="Scene class name (default: first/main)")
    p_render.add_argument(
        "-q",
        "--quality",
        default="low",
        choices=["preview", "draft", "low", "medium", "high", "final"],
        help="preview | draft | low | medium | high | final",
    )
    p_render.add_argument("-o", "--output", default=None)
    p_render.add_argument("-r", "--resolution", default=None)
    p_render.set_defaults(func=cmd_render)

    p_list = sub.add_parser("list", help="List projects, scenes, and output paths")
    p_list.set_defaults(func=cmd_list)

    p_new = sub.add_parser("new", help="Create a new project from template")
    p_new.add_argument("name", help="Project slug, e.g. quadratic_factoring")
    p_new.set_defaults(func=cmd_new)

    return parser


def main(argv: list[str] | None = None) -> int:
    ensure_on_path()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
