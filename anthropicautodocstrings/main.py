import argparse
import ast
import asyncio
import astor
import os
import sys
import time
from typing import Dict, List
import black
import textwrap
import typer
import anthropic
from anthropic import RateLimitError


def set_env_variable_linux(var_name, value) -> None:
    """

    Set an environment variable in the user's .bashrc file on Linux.

    Parameters:
        var_name (str): The name of the environment variable to set.
        value (str): The value to assign to the environment variable.

    Raises:
        IOError: If there is an error writing to the .bashrc file.

    Returns:
        None

    """
    with open(f"{os.path.expanduser('~')}/.bashrc", "a") as f:
        f.write(f'\nexport {var_name}="{value}"\n')
    print(
        f"Added {var_name} to .bashrc. Restart the terminal or run 'source ~/.bashrc' to load the new variable."
    )


def set_env_variable_windows(var_name, value) -> None:
    """

    Set an environment variable on a Windows system.

    Parameters:
        var_name (str): The name of the environment variable to set.
        value (str): The value to set for the environment variable.

    Returns:
        None

    Raises:
        Exception: If there is an error setting the environment variable.

    """
    os.system(f'set {var_name}="{value}"')


BASE_DIR = ""


async def generate_docstring(code_block: str, block_name: str) -> str:
    """

    Generates a docstring for a given Python function.

    Parameters:
        code_block (str): The Python function code block to generate the docstring for.
        block_name (str): The name of the Python function.

    Returns:
        str: The generated docstring for the Python function.

    Exceptions:
        RateLimitError: If the Anthropic API rate limit is exceeded, the function will
            wait for 1 minute and retry up to 5 times before exiting.
        Exception: If the ANTHROPIC_API_KEY environment variable is not set, the
            function will exit.

    """
    try:
        ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
        client = anthropic.Anthropic()
        if not ANTHROPIC_API_KEY:
            print("Exiting, as ANTHROPIC_API_KEY is required for the program to run.")
            sys.exit(1)
    except Exception:
        print("Exiting, as ANTHROPIC_API_KEY is required for the program to run.")
        sys.exit(1)
    stripped_code_block = textwrap.dedent(code_block)
    model = "claude-3-haiku-20240307"
    prompt = f"""
    You are a documentation assistant. Your task is to generate a concise and informative docstring 
    for the following Python function. The docstring should include a summary of what the function does, 
    a description of its parameters and their types, the return type, and any exceptions that it might raise.

    Please ensure that the response is strictly the docstring content without any additional text, 
    code blocks, or conversational elements. Do not repeat the code block or include any commentary.

    Here is the function to document:

    {stripped_code_block}
    """
    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            message = client.messages.create(
                max_tokens=1024,
                messages=[{"role": "user", "content": f"{prompt}"}],
                model=model,
            )
            if message.content and len(message.content) > 0:
                content = message.content[0].text.strip()
                content = content.replace("```python", "").replace("```", "").strip()
                if content.startswith('"""') and content.endswith('"""'):
                    content = content[3:-3].strip()
                elif content.startswith("'''") and content.endswith("'''"):
                    content = content[3:-3].strip()
                final_docstring = f'"""\n{content}\n"""'
                print("Generated Docstring:", final_docstring)
                return final_docstring
            else:
                print("No message content found")
                return ""
        except RateLimitError:
            typer.secho(
                "####### Anthropic rate limit reached, waiting for 1 minute #######",
                fg=typer.colors.YELLOW,
            )
            time.sleep(60)
            retries += 1
    if retries == max_retries:
        typer.secho(
            "Maximum number of retries exceeded. Giving up.", fg=typer.colors.RED
        )
        sys.exit(1)
    return None


async def update_docstrings_in_file(
    file: str, replace_existing_docstrings: bool, skip_constructor_docstrings: bool
) -> None:
    """

    async def update_docstrings_in_file(file: str, replace_existing_docstrings: bool, skip_constructor_docstrings: bool) -> None:

        Updates the docstrings of functions and async functions in a Python file.

        Parameters:
        file (str): The path of the file to update.
        replace_existing_docstrings (bool): Whether to replace existing docstrings or skip them.
        skip_constructor_docstrings (bool): Whether to skip updating the docstring of the `__init__` constructor.

        Raises:
        ValueError: If the provided file path is invalid.


    """
    abs_path = os.path.abspath(os.path.join(BASE_DIR, file))
    file_contents = None
    if not abs_path.startswith(BASE_DIR):
        print("Error: Invalid file path.")
    else:
        with open(abs_path, "r") as f:
            file_contents = f.read()
    if file_contents:
        tree = ast.parse(file_contents)
        nodes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for node in nodes:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "__init__"
                and skip_constructor_docstrings
            ):
                continue
            has_docstring = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Str)
            )
            if not replace_existing_docstrings and has_docstring:
                continue
            if has_docstring:
                node.body.pop(0)
            typer.secho(
                f"Updating docstrings for {node.name} in {file}", fg=typer.colors.YELLOW
            )
            code_block = astor.to_source(node).strip()
            block_name = node.name
            docstring = await generate_docstring(code_block, block_name)
            if docstring:
                docstring = docstring.replace('"""', "")
                node.body.insert(
                    0,
                    ast.Expr(
                        value=ast.Constant(value="\n" + docstring + "\n", kind=None)
                    ),
                )
        with open(file, "w") as f:
            source = astor.to_source(tree)
            formatted_source = black.format_str(source, mode=black.FileMode())
            f.write(formatted_source)


async def update_docstrings_in_directory(
    directory: str,
    replace_existing_docstrings: bool,
    skip_constructor_docstrings: bool,
    exclude_directories: List[str] = [],
    exclude_files: List[str] = [],
) -> None:
    """

    Update docstrings in a directory recursively.

    This function updates the docstrings in all Python files within a given
    directory and its subdirectories. It can be configured to replace existing
    docstrings or skip constructor docstrings, and to exclude specific
    directories or files.

    Args:
        directory (str): The path to the directory to process.
        replace_existing_docstrings (bool): Whether to replace existing docstrings.
        skip_constructor_docstrings (bool): Whether to skip updating constructor
            docstrings.
        exclude_directories (List[str]): A list of directories to exclude from
            processing.
        exclude_files (List[str]): A list of files to exclude from processing.

    Raises:
        OSError: If there is an issue accessing the directory or files.
        ValueError: If the provided directory does not exist.

    """
    for path in os.listdir(directory):
        full_path = os.path.join(directory, path)
        if os.path.isfile(full_path) and full_path.endswith(".py"):
            if os.path.basename(path) in exclude_files:
                continue
            await update_docstrings_in_file(
                full_path, replace_existing_docstrings, skip_constructor_docstrings
            )
        elif os.path.isdir(full_path):
            if os.path.basename(full_path) in exclude_directories:
                continue
            await update_docstrings_in_directory(
                full_path,
                replace_existing_docstrings,
                skip_constructor_docstrings,
                exclude_directories,
                exclude_files,
            )


async def update_docstrings(
    input: str,
    replace_existing_docstrings: bool,
    skip_constructor_docstrings: bool,
    exclude_directories: List[str] = [],
    exclude_files: List[str] = [],
) -> None:
    """

    Update the docstrings of Python files.

    Parameters:
        input (str): The path to a Python file or directory to update.
        replace_existing_docstrings (bool): Whether to replace existing docstrings or append to them.
        skip_constructor_docstrings (bool): Whether to skip updating constructor docstrings.
        exclude_directories (List[str]): Directories to exclude from the update.
        exclude_files (List[str]): Files to exclude from the update.

    Returns:
        None

    Raises:
        None

    """
    if os.path.isfile(input) and input.endswith(".py"):
        if os.path.basename(input) in exclude_files:
            return
        await update_docstrings_in_file(
            input, replace_existing_docstrings, skip_constructor_docstrings
        )
    elif os.path.isdir(input):
        if os.path.basename(input) in exclude_directories:
            return
        await update_docstrings_in_directory(
            input,
            replace_existing_docstrings,
            skip_constructor_docstrings,
            exclude_directories,
            exclude_files,
        )


def _extract_exclude_list(exclude: str) -> List[str]:
    """

    Extracts a list of values from a comma-separated string, excluding any empty strings.

    Parameters:
        exclude (str): A comma-separated string of values to be extracted.

    Returns:
        List[str]: A list of extracted values, excluding any empty strings.

    """
    return [x.strip() for x in exclude.split(",") if x.strip() != ""]


async def main() -> None:
    """

    main() -> None

    Executes the main functionality of the program, which involves updating docstrings in a specified input directory.

    Parameters:
        input (str): The input directory or file path to process.
        replace_existing_docstrings (bool): If True, replaces existing docstrings. Otherwise, adds new docstrings.
        skip_constructor_docstrings (bool): If True, skips updating constructor docstrings.
        exclude_directories (list[str]): List of directory paths to exclude from processing.
        exclude_files (list[str]): List of file paths to exclude from processing.

    Returns:
        None

    Raises:
        SystemExit: If the ANTHROPIC_API_KEY environment variable is not set.

    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Exiting, as ANTHROPIC_API_KEY is required for the program to run.")
        sys.exit(1)
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--replace-existing-docstrings", action="store_true")
    parser.add_argument("--skip-constructor-docstrings", action="store_true")
    parser.add_argument("--exclude-directories", default="")
    parser.add_argument("--exclude-files", default="")
    args = parser.parse_args()
    exclude_directories = _extract_exclude_list(args.exclude_directories)
    exclude_files = _extract_exclude_list(args.exclude_files)
    await update_docstrings(
        args.input,
        args.replace_existing_docstrings,
        args.skip_constructor_docstrings,
        exclude_directories,
        exclude_files,
    )


def run() -> None:
    """

    Run the main coroutine.

    This function is a wrapper around asyncio.run() that calls the main() coroutine and runs it until it completes.

    Returns:
        None

    Raises:
        RuntimeError: If there is no running event loop.

    """
    asyncio.run(main())
