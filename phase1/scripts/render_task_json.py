from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Iterable, Sequence


ARC_PALETTE = {
    0: "#000000",
    1: "#0074d9",
    2: "#ff4136",
    3: "#2ecc40",
    4: "#ffdc00",
    5: "#aaaaaa",
    6: "#f012be",
    7: "#ff851b",
    8: "#7fdbff",
    9: "#870c25",
}

BG_COLOR = "#f6f7f9"
PANEL_BG = "#ffffff"
BORDER_COLOR = "#ccd0d6"
TEXT_COLOR = "#212529"
META_TEXT_COLOR = "#5a626c"
ACCENT_COLOR = "#4c6ef5"
UNKNOWN_COLOR = "#505050"
FONT_STACK = "Iosevka Aile, DejaVu Sans, sans-serif"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render ARC-style task JSON files to SVG previews and build a gallery."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a task JSON file or a directory containing JSON files.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("renders"),
        help="Directory where rendered SVG files will be written.",
    )
    parser.add_argument(
        "--cell-size",
        type=int,
        default=32,
        help="Pixel size of each grid cell.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Limit the number of JSON files when rendering a directory.",
    )
    parser.add_argument(
        "--hide-values",
        action="store_true",
        help="Do not draw the numeric color value inside each cell.",
    )
    parser.add_argument(
        "--gallery-title",
        default="Phase 1 ARC Gallery",
        help="Title used for the generated gallery page.",
    )
    parser.add_argument(
        "--no-gallery",
        action="store_true",
        help="Render SVG files only and skip gallery generation.",
    )
    return parser.parse_args()


def iter_json_files(input_path: Path, max_files: int | None) -> Iterable[Path]:
    if input_path.is_file():
        yield input_path
        return

    files = sorted(path for path in input_path.rglob("*.json") if path.is_file())
    if max_files is not None:
        files = files[:max_files]
    yield from files


def load_task(task_path: Path) -> dict:
    with task_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def grid_dimensions(grid: Sequence[Sequence[int]] | None) -> tuple[int, int]:
    if not grid:
        return 0, 0
    rows = len(grid)
    cols = max((len(row) for row in grid), default=0)
    return rows, cols


def flatten_grid_values(grid: Sequence[Sequence[int]] | None) -> list[int]:
    if not grid:
        return []
    return [value for row in grid for value in row]


def colors_used(grid: Sequence[Sequence[int]] | None) -> str:
    values = sorted(set(flatten_grid_values(grid)))
    return ",".join(str(value) for value in values) if values else "-"


def max_grid_size(entries: Sequence[dict]) -> tuple[int, int]:
    max_rows = 0
    max_cols = 0
    for entry in entries:
        for key in ("input", "output"):
            rows, cols = grid_dimensions(entry.get(key))
            max_rows = max(max_rows, rows)
            max_cols = max(max_cols, cols)
    return max_rows, max_cols


def estimate_text_width(text: str, font_size: int) -> int:
    return max(1, int(len(text) * font_size * 0.62))


def contrast_text_color(hex_color: str) -> str:
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    return "#ffffff" if luminance < 140 else "#141414"


def svg_text(x: int, y: int, text: str, size: int, fill: str, weight: int = 400) -> str:
    escaped = html.escape(text)
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT_STACK}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}">{escaped}</text>'
    )


def svg_rect(x: int, y: int, width: int, height: int, fill: str, stroke: str, radius: int = 0) -> str:
    rounded = f' rx="{radius}" ry="{radius}"' if radius else ""
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'fill="{fill}" stroke="{stroke}"{rounded} />'
    )


def entry_metadata_lines(entry: dict, key: str) -> tuple[str, str]:
    grid = entry.get(key)
    rows, cols = grid_dimensions(grid)
    return f"{key} {rows}x{cols}", f"colors {colors_used(grid)}"


def grid_block_size(entry: dict, key: str, cell_size: int, meta_font_size: int) -> tuple[int, int]:
    grid = entry.get(key)
    rows, cols = grid_dimensions(grid)
    meta_primary, meta_secondary = entry_metadata_lines(entry, key)
    meta_width = max(
        estimate_text_width(meta_primary, meta_font_size),
        estimate_text_width(meta_secondary, meta_font_size),
    )
    width = max(cols * cell_size, meta_width)
    height = rows * cell_size + 40
    return width, height


def measure_pair(entry: dict, cell_size: int) -> tuple[int, int]:
    gap = 36
    input_width, input_height = grid_block_size(entry, "input", cell_size, 14)
    output_grid = entry.get("output")
    if output_grid is None:
        return input_width, input_height + 26
    output_width, output_height = grid_block_size(entry, "output", cell_size, 14)
    return input_width + gap + output_width, max(input_height, output_height) + 26


def measure_split(entries: Sequence[dict], cell_size: int) -> tuple[int, int]:
    if not entries:
        return 260, 56
    width = 0
    height = 42
    for entry in entries:
        pair_width, pair_height = measure_pair(entry, cell_size)
        width = max(width, pair_width)
        height += pair_height + 18
    return width, height


def task_metadata(task: dict, task_name: str, task_path: Path) -> list[str]:
    train_entries = task.get("train", [])
    test_entries = task.get("test", [])
    train_rows, train_cols = max_grid_size(train_entries)
    test_rows, test_cols = max_grid_size(test_entries)
    return [
        f"task: {task_name}",
        f"source: {task_path.as_posix()}",
        f"train pairs: {len(train_entries)}",
        f"test pairs: {len(test_entries)}",
        f"max grid size: {max(train_rows, test_rows)}x{max(train_cols, test_cols)}",
    ]


def detect_source_base(input_path: Path) -> Path:
    anchor = input_path.parent if input_path.is_file() else input_path
    for candidate in (anchor, *anchor.parents):
        if candidate.name == "raw" and candidate.parent.name == "datasets":
            return candidate
        if candidate.name == "datasets":
            return candidate
    return anchor


def output_relative_svg_path(task_path: Path, source_base: Path) -> Path:
    try:
        relative = task_path.relative_to(source_base)
    except ValueError:
        relative = Path(task_path.name)
    return relative.with_suffix(".svg")


def metadata_panel(metadata: Sequence[str], x: int, y: int, width: int) -> tuple[list[str], int]:
    line_height = 22
    height = 18 + len(metadata) * line_height + 18
    elements = [svg_rect(x, y, width, height, PANEL_BG, BORDER_COLOR, radius=12)]
    elements.append(svg_text(x + 14, y + 24, "metadata", 16, ACCENT_COLOR, weight=500))
    current_y = y + 48
    for line in metadata:
        elements.append(svg_text(x + 14, current_y, line, 14, META_TEXT_COLOR))
        current_y += line_height
    return elements, height


def render_grid(
    grid: Sequence[Sequence[int]],
    x: int,
    y: int,
    cell_size: int,
    show_values: bool,
) -> tuple[list[str], int, int]:
    rows, cols = grid_dimensions(grid)
    width = cols * cell_size
    height = rows * cell_size
    elements = [svg_rect(x, y, width, height, PANEL_BG, BORDER_COLOR, radius=8)]

    for row_index, row in enumerate(grid):
        for col_index, value in enumerate(row):
            color = ARC_PALETTE.get(value, UNKNOWN_COLOR)
            cell_x = x + col_index * cell_size
            cell_y = y + row_index * cell_size
            elements.append(svg_rect(cell_x, cell_y, cell_size, cell_size, color, BORDER_COLOR))
            if show_values:
                text_x = cell_x + cell_size // 2
                text_y = cell_y + cell_size // 2 + max(4, cell_size // 8)
                elements.append(
                    f'<text x="{text_x}" y="{text_y}" text-anchor="middle" '
                    f'font-family="{FONT_STACK}" font-size="{max(12, cell_size // 3)}" '
                    f'fill="{contrast_text_color(color)}">{value}</text>'
                )

    return elements, width, height


def render_block(
    entry: dict,
    key: str,
    x: int,
    y: int,
    cell_size: int,
    show_values: bool,
) -> tuple[list[str], int, int]:
    meta_primary, meta_secondary = entry_metadata_lines(entry, key)
    grid = entry.get(key)
    rows, cols = grid_dimensions(grid)
    grid_width = cols * cell_size
    meta_width = max(estimate_text_width(meta_primary, 14), estimate_text_width(meta_secondary, 14))
    block_width = max(grid_width, meta_width)
    elements = [
        svg_text(x, y + 14, meta_primary, 14, META_TEXT_COLOR),
        svg_text(x, y + 31, meta_secondary, 14, META_TEXT_COLOR),
    ]
    grid_elements, _, grid_height = render_grid(grid, x, y + 40, cell_size, show_values)
    elements.extend(grid_elements)
    return elements, block_width, grid_height + 40


def render_split(
    split_name: str,
    entries: Sequence[dict],
    x: int,
    y: int,
    cell_size: int,
    show_values: bool,
) -> tuple[list[str], int, int]:
    gap = 36
    elements = [svg_text(x, y + 20, split_name.upper(), 18, TEXT_COLOR, weight=600)]
    current_y = y + 42
    max_width = 0

    for index, entry in enumerate(entries, start=1):
        elements.append(svg_text(x, current_y + 16, f"{split_name} #{index}", 16, TEXT_COLOR, weight=500))
        pair_top = current_y + 26
        input_elements, input_width, input_height = render_block(
            entry,
            "input",
            x,
            pair_top,
            cell_size,
            show_values,
        )
        elements.extend(input_elements)

        output_grid = entry.get("output")
        pair_width = input_width
        pair_height = input_height
        if output_grid is not None:
            output_x = x + input_width + gap
            output_elements, output_width, output_height = render_block(
                entry,
                "output",
                output_x,
                pair_top,
                cell_size,
                show_values,
            )
            elements.extend(output_elements)
            pair_width = input_width + gap + output_width
            pair_height = max(input_height, output_height)

        max_width = max(max_width, pair_width)
        current_y = pair_top + pair_height + 18

    return elements, max_width, current_y - y


def render_task(
    task: dict,
    cell_size: int,
    task_name: str,
    task_path: Path,
    show_values: bool,
) -> str:
    padding = 24
    gutter = 34
    metadata = task_metadata(task, task_name, task_path)
    meta_width = max(estimate_text_width(line, 14) for line in metadata) + 40
    train_entries = task.get("train", [])
    test_entries = task.get("test", [])

    train_width, train_height = measure_split(train_entries, cell_size)
    test_width, test_height = measure_split(test_entries, cell_size)
    content_width = max(meta_width, train_width, test_width)

    meta_height = 18 + len(metadata) * 22 + 18
    canvas_width = content_width + padding * 2
    canvas_height = padding * 4 + 30 + meta_height + train_height + test_height + gutter

    elements = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}" '
            f'height="{canvas_height}" viewBox="0 0 {canvas_width} {canvas_height}">'
        ),
        f'<rect width="100%" height="100%" fill="{BG_COLOR}" />',
        svg_text(padding, padding + 20, task_name, 22, TEXT_COLOR, weight=600),
    ]

    current_y = padding + 34
    meta_elements, used_meta_height = metadata_panel(metadata, padding, current_y, content_width)
    elements.extend(meta_elements)
    current_y += used_meta_height + gutter

    train_elements, _, used_train_height = render_split(
        "train", train_entries, padding, current_y, cell_size, show_values
    )
    elements.extend(train_elements)
    current_y += used_train_height + gutter

    test_elements, _, _ = render_split(
        "test", test_entries, padding, current_y, cell_size, show_values
    )
    elements.extend(test_elements)
    elements.append("</svg>")
    return "\n".join(elements)


def render_file(
    task_path: Path,
    output_dir: Path,
    cell_size: int,
    show_values: bool,
    source_base: Path,
) -> Path:
    task = load_task(task_path)
    display_path = output_relative_svg_path(task_path, source_base)

    svg_content = render_task(
        task,
        cell_size=cell_size,
        task_name=task_path.stem,
        task_path=display_path,
        show_values=show_values,
    )
    output_path = output_dir / display_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_content, encoding="utf-8")
    return output_path


def collect_svg_files(output_dir: Path) -> list[Path]:
    return sorted(path for path in output_dir.rglob("*.svg") if path.is_file())


def dataset_and_subgroup(root: Path, image_path: Path) -> tuple[str, str]:
    relative = image_path.relative_to(root)
    parts = relative.parts
    if len(parts) == 1:
        return "root", "root"
    dataset = parts[0]
    subgroup = "/".join(parts[1:-1]) or "root"
    return dataset, subgroup


def split_bucket(dataset: str, subgroup: str) -> str:
        subgroup_lower = subgroup.lower()
        dataset_lower = dataset.lower()
        if dataset_lower == "arc-agi-2":
                if "training" in subgroup_lower:
                        return "training"
                if "evaluation" in subgroup_lower:
                        return "evaluation"
        return "other"


def gallery_card(root: Path, image_path: Path) -> str:
    relative_path = image_path.relative_to(root).as_posix()
    dataset, subgroup = dataset_and_subgroup(root, image_path)
    split = split_bucket(dataset, subgroup)
    return f"""
        <article class=\"card\" data-dataset=\"{html.escape(dataset.lower())}\" data-split=\"{split}\">
      <a class=\"preview\" href=\"{html.escape(relative_path)}\" target=\"_blank\">
        <img src=\"{html.escape(relative_path)}\" alt=\"{html.escape(image_path.stem)}\" loading=\"lazy\" />
      </a>
      <div class=\"card-body\">
        <h4>{html.escape(image_path.stem)}</h4>
                <p class=\"meta\">dataset: {html.escape(dataset)} | subgroup: {html.escape(subgroup)} | split: {split}</p>
        <p class=\"path\">{html.escape(relative_path)}</p>
      </div>
    </article>
    """.strip()


def build_gallery_html(title: str, root: Path, images: list[Path]) -> str:
    grouped: dict[str, dict[str, list[Path]]] = {}
    for image_path in images:
        dataset, subgroup = dataset_and_subgroup(root, image_path)
        grouped.setdefault(dataset, {}).setdefault(subgroup, []).append(image_path)

    dataset_options = ['<option value="all">全部数据集</option>']
    for dataset in grouped:
        dataset_options.append(
            f'<option value="{html.escape(dataset.lower())}">{html.escape(dataset)}</option>'
        )
    dataset_options_markup = "\n".join(dataset_options)

    sections: list[str] = []
    for dataset, subgroup_map in grouped.items():
        subgroup_sections: list[str] = []
        for subgroup, subgroup_images in subgroup_map.items():
            cards = "\n".join(gallery_card(root, image_path) for image_path in subgroup_images)
            subgroup_sections.append(
                f"""
                <section class=\"subgroup\" data-subgroup=\"{html.escape(subgroup.lower())}\">
                  <div class=\"subgroup-header\">
                    <h3>{html.escape(subgroup)}</h3>
                    <p>{len(subgroup_images)} task(s)</p>
                  </div>
                  <div class=\"card-grid\">
                    {cards}
                  </div>
                </section>
                """.strip()
            )
        subgroup_markup = "\n".join(subgroup_sections)
        sections.append(
            f"""
            <section class=\"dataset-section\" data-dataset=\"{html.escape(dataset.lower())}\">
              <div class=\"dataset-header\">
                <h2>{html.escape(dataset)}</h2>
                <p>{sum(len(items) for items in subgroup_map.values())} task(s)</p>
              </div>
              {subgroup_markup}
            </section>
            """.strip()
        )

    total_images = len(images)
    total_datasets = len(grouped)
    sections_markup = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{html.escape(title)}</title>
    <style>
        :root {{
            --bg: #f3f1ea;
            --paper: #fffdf8;
            --ink: #1f2933;
            --muted: #67707a;
            --accent: #146356;
            --line: #ddd7c9;
            --chip: #efe8d8;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: "Iosevka Aile", "DejaVu Sans", sans-serif;
            color: var(--ink);
            background:
                radial-gradient(circle at top left, rgba(20, 99, 86, 0.12), transparent 28%),
                linear-gradient(180deg, #f7f4ec 0%, var(--bg) 100%);
        }}
        header {{
            max-width: 1280px;
            margin: 0 auto;
            padding: 32px 24px 16px;
        }}
        h1 {{
            margin: 0 0 8px;
            font-size: clamp(28px, 4vw, 44px);
            letter-spacing: 0.02em;
        }}
        .subtitle {{
            margin: 0 0 20px;
            color: var(--muted);
            max-width: 760px;
            line-height: 1.5;
        }}
        .toolbar {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
        }}
        .select {{
            flex: 0 0 180px;
            padding: 12px 14px;
            border: 1px solid var(--line);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.88);
            color: var(--ink);
            font: inherit;
        }}
        .stat {{
            display: inline-flex;
            align-items: center;
            padding: 10px 12px;
            border-radius: 999px;
            background: var(--chip);
            color: var(--muted);
            font-size: 13px;
        }}
        .hint {{
            margin: 12px 0 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.5;
        }}
        main {{
            max-width: 1280px;
            margin: 0 auto;
            padding: 8px 24px 48px;
        }}
        .dataset-section {{
            margin-top: 28px;
            padding: 18px;
            border: 1px solid var(--line);
            border-radius: 20px;
            background: rgba(255, 253, 248, 0.8);
            box-shadow: 0 10px 24px rgba(34, 36, 38, 0.05);
        }}
        .dataset-header, .subgroup-header {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: baseline;
        }}
        .dataset-header h2, .subgroup-header h3, .card-body h4 {{
            margin: 0;
        }}
        .dataset-header p, .subgroup-header p {{
            margin: 0;
            color: var(--muted);
            font-size: 13px;
        }}
        .subgroup {{
            margin-top: 18px;
            padding-top: 14px;
            border-top: 1px dashed var(--line);
        }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 18px;
            margin-top: 12px;
        }}
        .card {{
            background: var(--paper);
            border: 1px solid var(--line);
            border-radius: 18px;
            overflow: hidden;
        }}
        .preview {{
            display: block;
            padding: 12px;
            background: linear-gradient(180deg, #ffffff 0%, #f1ede4 100%);
            min-height: 220px;
        }}
        img {{
            display: block;
            width: 100%;
            height: auto;
            background: #ffffff;
            border-radius: 10px;
            border: 1px solid var(--line);
        }}
        .card-body {{
            padding: 14px 16px 18px;
        }}
        .meta {{
            margin: 8px 0 6px;
            color: var(--accent);
            font-size: 13px;
        }}
        .path {{
            margin: 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.4;
            word-break: break-all;
        }}
        [hidden] {{
            display: none !important;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{html.escape(title)}</h1>
        <p class=\"subtitle\">批量渲染原始 JSON 任务为 SVG，并按数据集与子目录自动分组展示。页面支持按数据集和训练/评估切分筛选。</p>
        <div class=\"toolbar\">
            <select id=\"dataset-filter\" class=\"select\" aria-label=\"数据集筛选\">
                {dataset_options_markup}
            </select>
            <select id=\"split-filter\" class=\"select\" aria-label=\"数据切分筛选\">
                <option value=\"all\">全部切分</option>
                <option value=\"training\">只看训练</option>
                <option value=\"evaluation\">只看评估</option>
            </select>
            <span class=\"stat\">datasets: {total_datasets}</span>
            <span class=\"stat\">visible: <span id=\"visible-count\">{total_images}</span> / {total_images}</span>
        </div>
        <p id=\"filter-hint\" class=\"hint\" hidden>ConceptARC 没有官方 training/evaluation 目录切分；每个任务文件内部同时包含 train/test 示例。</p>
    </header>
    <main>
        {sections_markup}
    </main>
    <script>
        const datasetFilter = document.getElementById('dataset-filter');
        const splitFilter = document.getElementById('split-filter');
        const filterHint = document.getElementById('filter-hint');
        const cards = Array.from(document.querySelectorAll('.card'));
        const subgroups = Array.from(document.querySelectorAll('.subgroup'));
        const datasets = Array.from(document.querySelectorAll('.dataset-section'));
        const visibleCount = document.getElementById('visible-count');

        function applyFilter() {{
            const dataset = datasetFilter.value;
            const split = splitFilter.value;
            const splitApplies = dataset !== 'conceptarc';
            let shown = 0;

            splitFilter.disabled = !splitApplies;
            filterHint.hidden = splitApplies;

            cards.forEach((card) => {{
                const datasetValue = card.dataset.dataset || 'root';
                const splitValue = card.dataset.split || 'other';
                const datasetMatched = dataset === 'all' || datasetValue === dataset;
                const splitMatched = !splitApplies || split === 'all' || splitValue === split;
                const matched = datasetMatched && splitMatched;
                card.hidden = !matched;
                if (matched) {{
                    shown += 1;
                }}
            }});

            subgroups.forEach((group) => {{
                group.hidden = !group.querySelector('.card:not([hidden])');
            }});

            datasets.forEach((section) => {{
                section.hidden = !section.querySelector('.subgroup:not([hidden])');
            }});

            visibleCount.textContent = String(shown);
        }}

        datasetFilter.addEventListener('change', applyFilter);
        splitFilter.addEventListener('change', applyFilter);
        applyFilter();
    </script>
</body>
</html>
"""


def build_gallery(output_dir: Path, title: str, gallery_file: Path | None = None) -> Path:
    images = collect_svg_files(output_dir)
    if not images:
        raise SystemExit(f"No SVG files found under {output_dir}")

    gallery_path = gallery_file or (output_dir / "index.html")
    gallery_path.parent.mkdir(parents=True, exist_ok=True)
    gallery_path.write_text(build_gallery_html(title, output_dir, images), encoding="utf-8")
    return gallery_path


def main() -> None:
    args = parse_args()
    input_path = args.input_path.resolve()
    output_dir = args.output_dir.resolve()
    source_base = detect_source_base(input_path)

    rendered = []
    for task_path in iter_json_files(input_path, args.max_files):
        rendered_path = render_file(
            task_path,
            output_dir,
            args.cell_size,
            show_values=not args.hide_values,
            source_base=source_base,
        )
        rendered.append(rendered_path)
        print(rendered_path)

    if not rendered:
        raise SystemExit(f"No JSON files found under {input_path}")

    print(f"Rendered {len(rendered)} file(s) to {output_dir}")

    if not args.no_gallery:
        gallery_path = build_gallery(output_dir, title=args.gallery_title)
        print(f"Gallery written to {gallery_path}")


if __name__ == "__main__":
    main()