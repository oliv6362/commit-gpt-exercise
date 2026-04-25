# Commit GPT

Commit GPT is a small CLI tool that suggests a Git commit message based on the current changes in a repository.

It reads the Git diff, sends it to a local LLM through Ollama, and prints a suggested semantic commit message.

## Prerequisites

Make sure Ollama is running locally and that you have pulled an Ollama model, for example `gemma4:latest`.

## Installation

Install Python dependencies:

    pip install -r requirements.txt

## Configuration

The tool uses Ollama through the OpenAI-compatible API:

    http://localhost:11434/v1

The selected model is configured in `main.py`:

    MODEL_NAME = "gemma4:latest"

To show detailed errors, set this in `main.py`:

    DEBUG = True

## Usage

    python main.py <path-to-git-repository>

The repository must contain uncommitted changes.

## Example Output

    Suggested commit message:
    refactor: add fallback commit message handling

## Reliability

The tool includes simple reliability handling:

- Validates that the path is a Git repository
- Retries failed LLM requests
- Uses exponential backoff between retries
- Provides a fallback commit message if the LLM fails
- Uses basic rate limiting before LLM requests