# PptAgente

AI-powered PowerPoint presentation generator. Provide a topic and PptAgente uses an LLM to produce a polished `.pptx` file automatically.

## Requirements

- Python 3.10+
- An [OpenAI](https://platform.openai.com/) API key

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
export OPENAI_API_KEY="sk-..."

# Generate a 5-slide presentation (default)
python main.py "Introduction to Machine Learning"

# Customize slide count and output file
python main.py "Climate Change" --slides 8 --output climate.pptx
```

The generated `.pptx` file will be saved to the path specified by `--output` (default: `presentation.pptx`).

## Project Structure

```
PptAgente/
├── main.py                  # CLI entry point
├── ppt_agente/
│   ├── agent.py             # LLM-based slide content generation
│   └── generator.py         # python-pptx presentation builder
├── tests/
│   ├── test_generator.py    # Generator unit tests
│   └── test_main.py         # CLI unit tests
└── requirements.txt
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```
