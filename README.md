Anthropicautodocstrings is a command-line tool with the following key features:

* Updates the docstrings in Python files using the Anthropic API.
* Can process a single file or a directory of files, including all subdirectories.

Anthropicautodocstrings uses the Anthropic API to generate docstrings, so these are not guaranteed to be perfect. However, they are a good starting point for writing your own docstrings.

The claude-instat-1.2 model is used to generate the docstrings. This is fast af. The version this was forked from is slow in comparison. To increase raw speed! This runs asyncronously

Anthropicautodocstrings will work best for code that already has good type hints. Without type hints, the Anthropic API will have to guess input and return types, which may not be accurate.

---

## Requirements

* Python 3.8+
* A valid anthropic api key. 

---

## Installation
To install the dependencies for this tool, run the following command:



```console
$ pip install anthropicautodocstrings
```



---
## Usage
To use this tool, run the following commands:



```console
$ export ANTHROPIC_API_KEY=1234567890
$ autodocstrings INPUT `       
    [--replace-existing-docstrings] `
    [--skip-constructor-docstrings] `
    [--exclude-directories EXCLUDE_DIRECTORIES] `
    [--exclude-files EXCLUDE_FILES]
```



Where INPUT is a Python file or directory containing Python files to update the docstrings in, API_KEY is your Anthropic API key, and the optional flags --replace-existing-docstrings and --skip-constructor-docstrings can be used to skip updating docstrings for constructors (__init__ methods) and replacing existing docstirngs. EXCLUDE_DIRECTORIES and EXCLUDE_FILES are comma-separated lists of directories and files to exclude from the update.

---
## Examples
Update the docstrings in all Python files in the my_code directory:



```console
$ aads cool_code/
```



Update the docstrings in the my_file.py file:



```console
$ aads awesome_script.py
```



Update the docstrings in all Python files in the my_code directory and replace existing ones:



```console
$ aads cool_code/ --replace-existing-docstrings
```



Update the docstrings in all Python files in the my_code directory, but skip updating docstrings for class constructors (__init__ methods):



```console
$ aads cool_code/ --skip-constructor-docstrings
```



Update the docstrings in all Python files in the my_code directory, but exlcude the exclude_dir directory and the exclude_file_1.py and exclude_file_2.py files:



```console
$ aads my_code/ --exclude-directories exclude_dir --exclude-files exclude_file_1.py,exclude_file_2.py
```


---

## Limitations

* The python functions are being passed to the Anthropic API as independent code blocks. This means that the docstrings are not aware of the context of the function. If functions are written independently of each other, then this should not be a problem.
* ~~The format of the docstring is not always consistent, so you may need to manually fix some of the docstrings. You shouldn't use this in a ci/cd pipeline.~~
* ~~Input length is limited to the maximum input length of the Anthropic API. This is currently 2048 characters. If your function is larger than this then the docstring will not be updated.~~
* ~~Anthropic API can be slow.~~
---# anthropicautodocstrings
# anthropicautodocstrings
