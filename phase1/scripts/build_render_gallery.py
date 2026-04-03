from __future__ import annotations

import argparse
from pathlib import Path

from render_task_json import build_gallery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a grouped HTML gallery for rendered ARC SVG files."
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing rendered SVG files.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=Path,
        default=None,
        help="HTML file path. Defaults to <input_dir>/index.html.",
    )
    parser.add_argument(
        "--title",
        default="Phase 1 ARC Gallery",
        help="Gallery page title.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gallery_path = build_gallery(
        args.input_dir.resolve(),
        title=args.title,
        gallery_file=args.output_file.resolve() if args.output_file else None,
    )
    print(gallery_path)


if __name__ == "__main__":
    main()