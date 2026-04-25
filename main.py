import argparse
import os
import git
import json
import time
import requests
from typing import List, Dict
import openai

SYSTEM_PROMPT = """
You are an assistant that writes concise Git commit messages from git diffs.

Return only the commit message.
Do not include markdown.
Do not explain the diff.

Rules:
- Use conventional commit style when possible.
- Examples: feat:, fix:, refactor:, docs:, test:, chore:
- Keep the first line under 72 characters.
- Use imperative mood, for example: "add", "fix", "update", "refactor".
"""

MODEL_NAME = "gemma4:latest"

client = openai.OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

RATE_LIMIT_DELAY = 2
MAX_RETRIES = 3  # Number of retries for the LLM API call
BASE_DELAY = 1  # Base delay in seconds between retries


def is_git_repository(path: str) -> bool:
    try:
        _ = git.Repo(path).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False


def get_git_diffs(repo_path: str) -> str:
    """
    Get the git diffs for the repository.
    --------------------------------------------------------------------------------
    Example output:
    [
        {
            "file": "main.py",
            "changes": "diff --git a/main.py b/main.py
            index c174289..6a1b2a8 100644
            --- a/main.py
            +++ b/main.py
            @@ -23,8 +23,10 @@ def is_git_repository(path: str) -> bool:
                def get_git_diffs(repo_path: str) -> List[Dict[str, str]]:
                    repo = git.Repo(repo_path)
                    diffs = []
                    -    for diff in repo.index.diff(None):
                    -        diffs.append({\"file\": diff.a_path, \"changes\": diff.diff.decode(\"utf-8\")})
                    +    for item in repo.index.diff(None):
                    +        diff_text = repo.git.diff(item.a_path)
                    +        diffs.append({\"file\": item.a_path, \"changes\": diff_text})
                    +    print(diffs)
                            return diffs


                    @@ -35,7 +37,7 @@ def generate_commit_message(diffs: List[Dict[str, str]]) -> str | None:
                    def call_llm_api(prompt: str) -> str | None:
                    # TODO: Implement LLM API call to generate commit message
                    -    return None
                    +    return \"hahah\"


                        def main():"
        }
    ]
    --------------------------------------------------------------------------------
    Args:
        repo_path (str): The path to the git repository.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing the file path and the changes.
    """
    repo = git.Repo(repo_path)
    diffs = []

    for item in repo.index.diff(None):
        diff_text = repo.git.diff(item.a_path)

        useful_lines = []
        for line in diff_text.split("\n"):
            if (
                line.startswith("diff --git")
                or line.startswith("@@")
                or line.startswith("+")
                or line.startswith("-")
            ):
                useful_lines.append(line)

        formatted_diff = f"File: {item.a_path}\n" + "\n".join(useful_lines)
        diffs.append(formatted_diff)

    return "\n\n".join(diffs)


def generate_commit_message(diffs: str) -> str | None:
    prompt = f"""
    Generate a Git commit message for the following diffs:
    
    {diffs}
    """
    return call_llm_api(prompt)

def call_llm_api(prompt: str) -> str | None:
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(RATE_LIMIT_DELAY)

            # noinspection PyTypeChecker
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )
            message = response.choices[0].message.content

            if message is None:
                return None
            return message.strip()

        except Exception as e:
            print(f"LLM API call failed on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)

    return None

def main():
    parser = argparse.ArgumentParser(
        description="Generate commit message suggestions using an LLM."
    )
    parser.add_argument("repo_path", help="Path to the git repository")
    args = parser.parse_args()

    if not is_git_repository(args.repo_path):
        print("Error: The specified path is not a valid git repository.")
        return

    diffs = get_git_diffs(args.repo_path)
    if not diffs:
        print("No changes detected in the repository.")
        return

    try:
        commit_message = generate_commit_message(diffs)
        if commit_message is None:
            print("No commit message generated.")
            return

        print("Suggested commit message: ")
        print(commit_message)
    except Exception as e:
        print(f"An error occurred while generating the commit message: {str(e)}")
        print("Please try again later or write the commit message manually.")


if __name__ == "__main__":
    main()
