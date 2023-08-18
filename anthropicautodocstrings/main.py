import argparse
import ast
import asyncio
import astor
import os
import sys
import time
from typing import List
import black
import textwrap
import typer
from anthropic import AsyncAnthropic, HUMAN_PROMPT, AI_PROMPT
from anthropic import (
    APIError,
    ConflictError,
    NotFoundError,
    APIStatusError,
    RateLimitError,
    APITimeoutError,
)
import dotenv

# Load .env file if it exists
dotenv.load_dotenv()

# Get ANTHROPIC_API_KEY from environment
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# If not available in environment, ask user for it
if not ANTHROPIC_API_KEY:
    confirmation = input("ANTHROPIC_API_KEY not found. Would you like to enter it now? (yes or no) ").lower()
    
    if confirmation == "yes":
        ANTHROPIC_API_KEY = input("Please enter your ANTHROPIC_API_KEY: ")
        
        # Save the key to .env file
        with open(".env", "a") as env_file:
            env_file.write(f"\nANTHROPIC_API_KEY={ANTHROPIC_API_KEY}\n")
            
        # Load the newly added environment variable
        dotenv.load_dotenv()
    else:
        typer.secho("Exiting, as ANTHROPIC_API_KEY is required for the program to run.")
        sys.exit(1)

anthropic = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
BASE_DIR = ""


async def generate_docstring(code_block: str, block_name: str):
    stripped_code_block = textwrap.dedent(code_block)
    model = "claude-instant-1.2"
    prompt = f"""
    Make sure to include type or annotation for parameters and return values.
    Include exceptions, parameters, and return values.
    See the below examples for reference.
    Only return the DocString with no special characters as a response.
    Examples:
    ""\"Example Google style docstrings.

        This module demonstrates documentation as specified by the `Google Python
        Style Guide`_. Docstrings may extend over multiple lines. Sections are created
        with a section header and a colon followed by a block of indented text.

        Example:
            Examples can be given using either the ``Example`` or ``Examples``
            sections. Sections support any reStructuredText formatting, including
            literal blocks::

                $ python example_google.py

        Section breaks are created by resuming unindented text. Section breaks
        are also implicitly created anytime a new section starts.

        Attributes:
            module_level_variable1 (int): Module level variables may be documented in
                either the ``Attributes`` section of the module docstring, or in an
                inline docstring immediately following the variable.

                Either form is acceptable, but the two should not be mixed. Choose
                one convention to document module level variables and be consistent
                with it.
        ""\"
    Actualy Code Block to create Doc String for:
    {stripped_code_block}
    """
    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            completion = await anthropic.completions.create(
                model=model,
                max_tokens_to_sample=500,
                prompt=f"{HUMAN_PROMPT}{prompt}{AI_PROMPT}",
            )
            output = completion.completion.strip()
            return output
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


async def update_docstrings_in_file(
    file: str, replace_existing_docstrings: bool, skip_constructor_docstrings: bool
) -> None:
    abs_path = os.path.abspath(os.path.join(BASE_DIR, file))
    file_contents = None
    if not abs_path.startswith(BASE_DIR):
        print("Error: Invalid file path.")
    else:
        with open(abs_path, "r") as f:
            file_contents = f.read()
    if file_contents:
        tree = ast.parse(file_contents)
        nodes = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        for node in nodes:
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "__init__"
                and skip_constructor_docstrings
            ):
                continue
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Str)
            ):
                if not replace_existing_docstrings:
                    continue
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

    _extract_exclude_list(exclude: str) -> List[str]

        Extracts a list of excluded items from a comma separated string.

        Parameters:
            exclude: str
                The comma separated string of excluded items.

        Returns:
            List[str]:
                A list containing the excluded items stripped of whitespace.

        Raises:
            None

        This function takes a comma separated string of excluded items and returns
        a list containing the same items stripped of any surrounding whitespace.
    """
    return [x.strip() for x in exclude.split(",") if x.strip() != ""]


async def main() -> None:
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


def run():
    """
    main()

            This function is the entry point for the program. It calls the async function run().

            Returns:
                None

            Raises:
                asyncio.CancelledError: if the task is cancelled.
    """
    asyncio.run(main())
