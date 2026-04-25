import argparse
import git
import time
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

RATE_LIMIT_DELAY = 2 # Seconds to wait before each LLM request
MAX_RETRIES = 3  # Number of retries for the LLM API call
BASE_DELAY = 1  # Base delay in seconds between retries

DEBUG = False # Enable detailed error output for debugging

def is_git_repository(path: str) -> bool:
    try:
        _ = git.Repo(path).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False


def get_git_diffs(repo_path: str) -> str:
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

    commit_message = call_llm_api(prompt)

    if commit_message is None or not commit_message.strip():
        print("Using fallback commit message because the LLM failed.")
        if DEBUG:
            print(diffs)
        return fallback_commit_message(diffs)

    return commit_message.strip()

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
                temperature=0.4,
            )
            message = response.choices[0].message.content

            if message is None:
                return None
            return message.strip()

        except Exception as e:
            print(f"LLM API call failed on attempt {attempt + 1}.")

            if DEBUG:
                print(f"Debug details: {e}")

            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)

    return None

def fallback_commit_message(diffs: str) -> str:
    lower_diffs = diffs.lower()

    files = [
        line.replace("File: ", "").strip().lower()
        for line in diffs.splitlines()
        if line.startswith("File: ")
    ]

    if files and all(file.endswith(".md") or "readme" in file for file in files):
        return "docs: update documentation"

    if files and all("test" in file or "spec" in file for file in files):
        return "test: update tests"

    if "error" in lower_diffs or "exception" in lower_diffs or "fallback" in lower_diffs:
        return "fix: handle failure case"

    if any(keyword in lower_diffs for keyword in ["def ", "class ", "import ", "return "]):
        return "refactor: update implementation"

    return "chore: update project files"


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
