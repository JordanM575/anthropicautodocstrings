import pytest
import os
import tempfile
import sys
import anthropicautodocstrings
import anthropicautodocstrings.main
from anthropicautodocstrings.main import (
    update_docstrings_in_directory,
    update_docstrings,
    _extract_exclude_list,
)

# Fixture to setup and cleanup API key
@pytest.fixture(scope="function")
def setup_api_key():
    try:
        # Check if ANTHROPIC_API_KEY is set, if not, it'll raise a KeyError
        os.environ["ANTHROPIC_API_KEY"]
    except KeyError:
        # Set a fake API key if not found
        os.environ["ANTHROPIC_API_KEY"] = "FAKE_API_KEY"
    
    # Provide the API key to the test function if needed
    yield os.environ["ANTHROPIC_API_KEY"]
    
    # Cleanup after test (optional)
    if os.environ["ANTHROPIC_API_KEY"] == "FAKE_API_KEY":
        del os.environ["ANTHROPIC_API_KEY"]


def create_test_file_with_docstring(docstring: str) -> tempfile.NamedTemporaryFile:
    """
    create_test_file_with_docstring(docstring: str) -> tempfile.NamedTemporaryFile

    Creates a temporary file containing a function with the given docstring. The file is returned as a NamedTemporaryFile instance.

    Parameters:
        docstring: str
            The docstring to include in the temporary file

    Returns:
            tempfile.NamedTemporaryFile
                A file-like object representing the temporary file created, which must be closed by the caller.

    """
    file_contents = f"\ndef foo():\n{docstring}\npass\n"
    test_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    test_file.write(file_contents)
    test_file.close()
    return test_file


def create_test_file_with_constructor() -> tempfile.NamedTemporaryFile:
    """

    def create_test_file_with_constructor() -> tempfile.NamedTemporaryFile:
        Create a test file with constructor.
        Create a temporary NamedTemporaryFile to contain some file contents and return it without deleting.
        Parameters:
            None
        Returns:
            tempfile.NamedTemporaryFile: Returns the test file object without deleting it.
        Raises:
            None
        File_contents is written to a NamedTemporaryFile which is returned without deleting. This allows the contents to be accessed later for testing.
    """
    file_contents = """
    def __init__():
        pass
    """
    test_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    test_file.write(file_contents)
    test_file.close()
    return test_file

@pytest.mark.asyncio
# Using the setup_api_key fixture
async def test_update_docstrings_in_directory(mocker, setup_api_key: str) -> None:
    test_dir = tempfile.TemporaryDirectory()
    subdir_1 = os.path.join(test_dir.name, "subdir_1")
    os.makedirs(subdir_1)
    file_1 = os.path.join(test_dir.name, "file_1.py")
    file_2 = os.path.join(subdir_1, "file_2.py")
    open(file_1, "w").close()
    open(file_2, "w").close()
    mocker.patch.object(
        anthropicautodocstrings.main, "update_docstrings_in_file", return_value=None
    )
    await update_docstrings_in_directory(test_dir.name, True, False, [], [])
    anthropicautodocstrings.main.update_docstrings_in_file.assert_any_call(
        file_1, True, False
    )
    anthropicautodocstrings.main.update_docstrings_in_file.assert_any_call(
        file_2, True, False
    )
    test_dir.cleanup()


@pytest.mark.asyncio
async def test_update_docstrings_in_directory_with_exclude_files(mocker) -> None:
    test_dir = tempfile.TemporaryDirectory()
    file_1 = os.path.join(test_dir.name, "file_1.py")
    open(file_1, "w").close()
    mocker.patch.object(
        anthropicautodocstrings.main, "update_docstrings_in_file", return_value=None
    )
    await update_docstrings_in_directory(test_dir.name, True, False, [], ["file_1.py"])
    anthropicautodocstrings.main.update_docstrings_in_file.assert_not_called()
    test_dir.cleanup()


@pytest.mark.asyncio
async def test_update_docstrings_in_directory_with_exclude_dirs(mocker) -> None:
    test_dir = tempfile.TemporaryDirectory()
    subdir_1 = os.path.join(test_dir.name, "subdir_1")
    os.makedirs(subdir_1)
    file_2 = os.path.join(subdir_1, "file_2.py")
    open(file_2, "w").close()
    mocker.patch.object(
        anthropicautodocstrings.main, "update_docstrings_in_file", return_value=None
    )
    await update_docstrings_in_directory(test_dir.name, True, False, ["subdir_1"], [])
    anthropicautodocstrings.main.update_docstrings_in_file.assert_not_called()
    test_dir.cleanup()


@pytest.mark.asyncio
async def test_update_docstrings_input_is_valid_file(mocker) -> None:
    os.environ["ANTHROPIC_API_KEY"] = "test_key"
    open("test_file.py", "w").close()
    mocker.patch.object(
        anthropicautodocstrings.main, "update_docstrings_in_file", return_value=None
    )
    await update_docstrings(
        "test_file.py",
        replace_existing_docstrings=True,
        skip_constructor_docstrings=False,
        exclude_directories=[],
        exclude_files=["test_file.py"],
    )
    anthropicautodocstrings.main.update_docstrings_in_file.assert_not_called()
    await update_docstrings(
        "test_file.py",
        replace_existing_docstrings=True,
        skip_constructor_docstrings=False,
    )
    anthropicautodocstrings.main.update_docstrings_in_file.assert_called_once_with(
        "test_file.py", True, False
    )
    os.unlink("test_file.py")


@pytest.mark.asyncio
async def test_update_docstrings_input_is_valid_directory(mocker) -> None:
    os.environ["ANTHROPIC_API_KEY"] = "test_key"
    test_dir = tempfile.TemporaryDirectory()
    mocker.patch.object(
        anthropicautodocstrings.main,
        "update_docstrings_in_directory",
        return_value=None,
    )
    await update_docstrings(
        test_dir.name,
        replace_existing_docstrings=True,
        skip_constructor_docstrings=False,
        exclude_directories=[os.path.basename(test_dir.name)],
        exclude_files=[],
    )
    anthropicautodocstrings.main.update_docstrings_in_directory.assert_not_called()
    await update_docstrings(
        test_dir.name,
        replace_existing_docstrings=True,
        skip_constructor_docstrings=False,
    )
    anthropicautodocstrings.main.update_docstrings_in_directory.assert_called_once_with(
        test_dir.name, True, False, [], []
    )
    test_dir.cleanup()


def test_extract_exclude_list(mocker) -> None:
    """
    test_extract_exclude_list(mocker):
            Extract exclude list from a string.

            Arguments:
                mocker: Mock object

            Returns:
                list - List of excluded files

            Raises:
                No exceptions
    """
    assert _extract_exclude_list("") == []
    assert _extract_exclude_list("test.py") == ["test.py"]
    assert _extract_exclude_list("test1.py,test2.py,test3.py") == [
        "test1.py",
        "test2.py",
        "test3.py",
    ]
    assert _extract_exclude_list(" test1.py , test2.py , test3.py ") == [
        "test1.py",
        "test2.py",
        "test3.py",
    ]


@pytest.mark.asyncio
async def test_main(mocker):
    mocker.patch.object(
        anthropicautodocstrings.main, "update_docstrings", return_value=None
    )
    sys.argv = [
        "autodocstrings",
        "input_path",
        "--replace-existing-docstrings",
        "--skip-constructor-docstrings",
        "--exclude-directories",
        "dir1,dir2",
        "--exclude-files",
        "file1,file2",
    ]
    await anthropicautodocstrings.main.main()
    anthropicautodocstrings.main.update_docstrings.assert_called_once_with(
        "input_path", True, True, ["dir1", "dir2"], ["file1", "file2"]
    )
