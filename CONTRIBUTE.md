# Contribute to ISF

Welcome to the ISF contributor guide!

Contents:
- [Code of Conduct](#code-of-conduct)
- [Who can contribute?](#who-can-contribute)
- [How to contribute](#how-to-contribute)
  - [What to consider](#what-to-consider)
  - [Setting up the development environment](#setting-up-the-development-environment)
  - [Coding Standards and Guidelines](#coding-standards-and-guidelines)
  - [Testing](#testing)
  - [Commits](#commits)
  - [Pull Request Process](#pull-request-process)
- [Issue Tracking](#issue-tracking)
- [Documentation](#documentation)
  - [Documentation format](#documentation-format)
  - [Common mistakes](#common-mistakes)
  - [Sphinx](#sphinx)
- [Database](#database)
  - [Database Modularity](#database-modularity)

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for all. Please read and adhere to our [Code of Conduct](./CODE_OF_CONDUCT.md).

## Who can contribute?

Anyone who uses ISF and has ideas on how to improve or extend the functionality is welcome to contribute!

## How to contribute

### What to consider

Before you start implementing a feature or fixing a bug, please [open an issue](https://github.com/mpinb/in_silico_framework/issues/new/choose) first.
It is not unlikely that some functionality may already be available, or at least possible with ISF. At the same time, not every possibility needs to be part of ISF's source code. 

In the issues tracker, you can also count on the expertise and advice of the developers who have been using and develping ISF for some time now.
That being said, we are also welcome new ideas, and are very excited to hear how you are using ISF!

### Setting up the development environment

ISF uses [`pixi`](https://pixi.sh/latest) for managing environments. The default environment includes the`run dependencies`: everything you need to run ISF.
These are often sufficient to implement new ideas. However, if you require additional dependenices, you can simply `pixi add xyz`. Before adding new dependencies to ISF, please consider the following:

- Dependencies are not always maintained forever. `pandas-msgpack` and `sumatra` have been two examples of packages we had to deprecate or work around in ISF.
- Maintenance costs tend to scale exponentially with additional dependencies
- Can your dependency be reasonably omitted in favor of the standard library, or other core packages such as `numpy` or `scipy`?

### Coding Standards and Guidelines

Please follow these coding standards and guidelines:

- **Code Style**: Follow PEP 8 for Python code.
- **Naming Conventions**: Use descriptive names for variables, functions, and classes.
- **Documentation**: Write docstrings for *all* public functions, classes, and methods.
- **Comments**: Use comments to explain complex logic and important decisions.
- **Formatting**: We prefer the `black` coding style.


### Testing

To test if a new feature works as advertised, we **strongly** recommend you write tests for it. This may not be the flashiest aspect of coding, but untested code can lead to infinitely more hassle and lost time compared to whatever time it takes to write the tests.

While this is not explicit in ISF, you can categorize a test in one of three areas:

- **Unit tests**: Isolated tests that checks if a single object operates as expected under various conditions. Example: what happens if I pass wrong types, negative values ... to a single function?
- **Integration tets**: Broader-scoped tests that check if a piece of software integrates well with existing code. Example: does my new pipeline work well with ISF's existing `data_base` functionality?
- **End-to-end (E2E) tests**: Does my pipeline still operate as expected from start to finish? Example: if I adapt the file format of the cell parameters, can I still run `simrun.run_new_simulations()`?

Running test requires additional dependencies, such as `pytest`. These are defined in our `test` environment. To run the test suite in the test environment, we preconfigured the following command:

```bash
pixi run test
```

To run any other command within the test environment, you can simply prefix the command with:

```bash
pixi run -e test my_command
```

### Commits

Please keep commits single-purpose with descriptive commit messages. Avoid adding all changes in a single monolithic commit.
Write clear and descriptive commit messages. Follow these guidelines:

- **Title**: A short summary of the changes (50 characters or less).
- **Body**: A detailed description of the changes, if necessary. Explain the "why" and "how" of the changes.

### Pull Request Process

To submit a pull request:

1. **Fork the repository** and create your branch from your version of `develop`.
2. **Commit your changes** with clear commit messages.
3. **Push your branch** to your forked repository.
4. **Open a pull request** against ISF's `develop` branch.

In your pull request description, include:

- A summary of the changes.
- Any related issues or pull requests.
- Steps to test the changes.

## Issue Tracking

We use GitHub Issues to track bugs and feature requests. When reporting an issue, please include:

- A clear and descriptive title.
- A detailed description of the problem or request.
- Steps to reproduce the issue, if applicable.
- Any relevant logs, screenshots, or code snippets.

Label your issue appropriately (e.g., `bug`, `enhancement`, `question`).

## Documentation

Our documentation is generated using Sphinx, together with the `autoapi` extension.
Invoking `pixi run build_docs` triggers the Sphinx build process. This is simply a convenience alias for `make html`.
If you are adapting the documentation configuration, you may need to delete the `docs/_build` and `docs/tutorials` directories before rebuilding.

### Documentation format

We use the Google-style documentation format. The Google documentation guidelines can be broadly summarized by just a handful of rules:

- The first line is a short description. This will appear in summary tables in the documentation.
- Attribute blocks, argument blocks and other blocks are indented. Note that indentation also impacts rst (see example below)
- Arguments and attributes are listed with their type in brackets: `attr_arg (type): descr`

In addition to these guidelines, ISF imposes one additional rule for docstrings:

- Class docstrings always end with a list of their attributes. This is in contrast to the [PEP-257 convention](https://peps.python.org/pep-0257/) where attribute docstrings come after each attribute. We use Jinja templating to parse out the attributes from the Attribute block rather than the PEP-257 convention, because the PEP-257 convention is just honestly quite a bit of work. That being said, you are of course also allowed to use the PEP-257 convention. Just don't mix the two.

Classes tend to be the most documentation work, so we've opted to give you an example class to showcase what you can do with documentation. `rst` directives in the docstring are allowed. most HTML themes also support example blocks, attention blocks, "see also" blocks etc.

```python
class DocumentMePlease():
  """A short sentence.
  
  This class serves as an example. It shows how a docstring should look like.

  You can use example blocks like below. Mind the fact that code blocks in rst are defined by their indentation and a preceding double colon.

  Example::

      >>> code(
      ... arg=1
      ... )
      output
      >>> more_code()

  Example:

      Another example, just in text.

  See also:
      A link to :py:class:`~package.subpackage.module.AnotherClass`

  Attributes:
      test_attribute (bool): a test attribute
      esc (bool): Another test attribute
      attribute_not_arg (int): An attribute that is not in the init docstring.
  """
  def __init__(self, test_arg, escape_me_):
    """
    Args:
        test_arg (bool): A test argument.
        escape_me\_ (bool): An argument ending in an underscore, which should b escaped.
    """
    self.test_attribute = test
    self.esc = escape_me_
    """esc (bool): This is a PEP-257 docstring example. Because I'm now mixing conventions, this will appear twice"""
    self.attribute_not_arg = self.test_attribute + self.esc
```

### Common mistakes

Here are some common things to look out for when writing documentation:

- **Indentation**: rst is strict on indentation. It is also conventionally indented with $3$ spaces rather than $4$. In most cases, rst works fine with $4$ as well (as long as you're consistent), but if you're e.g. adapting the Jinja templates, you will need to stick with the convention.
- **Newlines**: Sphinx relies heavily on neewlines to recognize blocks. For example, *al* lists (numbered or bullet) must start and end with a newline. This can lead to some weird-looking docstrings if you want e.g. a bullet list inside of an attribute block. But it works.
- **Forgetting the module-level docstring**: please don't forget it! It's the most easily overlooked, but stands out the most in the final HTML page, as it yields a near-blank page.

### Sphinx

A comprehensive overview of how Sphinx reads in source files (i.e. our Python code) and builds documentation is given at https://www.sphinx-doc.org/en/master/extdev/event_callbacks.html
However, we summarize some key concepts below.

- All configuration (with the exception of templates) is defined in `docs/conf.py`.
- Our documentation uses custom templates, provided in `docs/_templates/autoapi/python`
- When Sphinx writes out documentation, it first writes our "stub pages" that contain the overall structure of the documentation page. These stub pages are reStructuredText (`.rst`) files with structural information of the page, but (generally) no explicit content yet. Only afterwards does it generate HTML (or PDF if you want) from these stub pages.
- Sphinx and reStructuredText heavily rely on directives to make documentation. While there are many extensions with custom directives, this project
  relies on just a handful of core built-in directives: `.. py:obj::` and `.. toctree::`.
- The look and ufnctionality of the documentation website can still *heavily* depend on which HTML theme you are using.
  Often, HTML themes offer very functional extensions beyond what one would consider "just a theme". 
  For example, our current HTML theme (last checked 27/02/2025) is `immaterial`, which ships with a reflinking extension for Graphviz.
- For debugging purposes, you can inspect what the stub files look like in `docs/autoapi` (only if `autoapi_keep_files = True` in `conf.py`)

## Database
The database system in ISF is modular, meaning that new file formats or entirely new database systems can be implemented if needed.

Implementing new file formats is easy:

1. Identify the current database system (should be `data_base.isf_data_base` as of 04/03/2025)
2. Add a new module to ``IO.LoaderDumper`` containing:
  a. A writer function under the name ``dump()``
  b. A reader class under the name ``Loader``

That's it! You can now use this data format to save data:

```python
db.set("key", my_data, dumper=dumper_module_name)
db["key"]  # returns my_data
```

The database will automatically use your `dump()` and `Loader` to save and read your data.

### Database modularity

This codebase has been a little over 15 years in the making (depending on who you ask). Inevitably, data formats have come and passed. `pandas-msgpack` used to be the crème de la crème with its `blosc` compression, until it stopped being maintained. To balance long term support with cutting-edge file formats, we must be modular in our database system.

What do we meean when we say a "modular data base system"? In the past, we have used `model_data_base` instead of `isf_data_base`. `model_data_base` differed from the current database system in the following aspects:
- It used the `.pickle` format for saving metadata, and `LoaderDumper` information. This introduced the issue that nothing could be refactored, moved or renamed in the source code of the database, or the pickled Loader object would not work anymore. 
- It used SQLite to save and fetch metadata. This then required filelocking to prevent concurrent writes to the metadata file.

Both issues introduced significant overhead in usage and maintenance. However, simply changing the way it worked would invalidate all old data. As we didn't want to convert exabytes of data when we could still simply read it in, but also wanted to avoid these issues in the future, we opted for the current "modular" approach, where we can use both `isf_data_base`, and `model_data_base` (if necessary), and even extend it to some mysterious third future option (God help us all if we need to, but we could).

This modular approach is possible because we have one wrapper `data_base` package, and a corresponding `DataBase` wrapper class. Give the wrapper class a path to a database, it will infer which database system was used, and give you the correct source code to read, inspect, and write data.

Throughout ISF, all other packages simply rely on the wrapper `data_base`, and do not know which database system will actually take care of saving their precious data. This agnosticism is achieved by dynamically adding the latest `IO` and `db_initializers` subpackages to the Python namespace at runtime, i.e. as soon as `data_base` is imported. Exactly which subpackages are the "latest" can then be configured in the `data_base` package.

You may have noticed that we do **not** recommend changing the database system. It is tedious, and introduces avoidable technical debt. Generally, 99% of all flexibility you could ever want can be achieved by implementing new `LoaderDumper` modules in the current database system.