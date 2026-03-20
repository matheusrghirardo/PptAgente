#!/usr/bin/env python3
"""PptAgente — AI-powered PowerPoint presentation generator.

Usage:
    python main.py "Your topic here" [--slides N] [--output file.pptx]
"""

import argparse
import sys

from ppt_agente.agent import generate_slides
from ppt_agente.generator import create_presentation


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ppt-agente",
        description="Generate a PowerPoint presentation from a topic using AI.",
    )
    parser.add_argument("topic", help="Topic or title for the presentation.")
    parser.add_argument(
        "--slides",
        type=int,
        default=5,
        metavar="N",
        help="Number of slides to generate (default: 5).",
    )
    parser.add_argument(
        "--output",
        default="presentation.pptx",
        metavar="FILE",
        help="Output .pptx file path (default: presentation.pptx).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print(f"Generating {args.slides}-slide presentation about: {args.topic!r}")
    slides = generate_slides(args.topic, num_slides=args.slides)

    output = create_presentation(slides, output_path=args.output)
    print(f"Presentation saved to: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
