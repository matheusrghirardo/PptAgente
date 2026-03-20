"""Tests for the CLI entry point (no LLM / network calls required)."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from main import main, parse_args


def test_parse_args_defaults():
    args = parse_args(["My Topic"])
    assert args.topic == "My Topic"
    assert args.slides == 5
    assert args.output == "presentation.pptx"


def test_parse_args_custom():
    args = parse_args(["AI", "--slides", "8", "--output", "out.pptx"])
    assert args.topic == "AI"
    assert args.slides == 8
    assert args.output == "out.pptx"


MOCK_SLIDES = [
    {"title": "Intro", "bullets": ["Point A", "Point B", "Point C"]},
    {"title": "Main", "bullets": ["Detail 1", "Detail 2", "Detail 3"]},
    {"title": "End", "bullets": ["Recap 1", "Recap 2", "Recap 3"]},
]


def test_main_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        output = os.path.join(tmpdir, "result.pptx")
        with patch("main.generate_slides", return_value=MOCK_SLIDES) as mock_gen:
            rc = main(["Test Topic", "--slides", "3", "--output", output])
        assert rc == 0
        assert os.path.isfile(output)
        mock_gen.assert_called_once_with("Test Topic", num_slides=3)
