<p align="center">
  <img src="https://raw.githubusercontent.com/udbhav-44/zoekt-py/main/assets/logo.png" alt="ZoektPy Logo" width="400"/>
</p>

# ZoektPy

**Python client library and CLI for [Zoekt](https://github.com/sourcegraph/zoekt) code search.**

[![PyPI version](https://badge.fury.io/py/zoektpy.svg)](https://badge.fury.io/py/zoektpy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)


---

## Overview

**ZoektPy** is a modern, fully typed Python client and CLI for interacting with [Zoekt](https://github.com/sourcegraph/zoekt), a fast, scalable code search engine. It supports both synchronous and asynchronous usage, rich CLI output, and advanced search features.

- **Search code** across repositories using Zoekt's API
- **List repositories** and their metadata
- **Filter by language, file, repo, and more**
- **Rich CLI output** with syntax highlighting (via [rich](https://github.com/Textualize/rich))
- **Fully typed models** (via [pydantic](https://docs.pydantic.dev/))
- **Async and sync clients**

---

## Installation

```shell
pip install zoektpy
```

Or, for development:

```shell
git clone https://github.com/udbhav-44/zoekt-py.git
cd zoekt-py
pip install -e .[dev]
```

---

## Quickstart

### CLI Usage

After installation, the `zoekt` command is available:

```shell
zoekt search "def my_function" --host my.zoekt.server --language python --max-matches 10
```

**List repositories:**

```shell
zoekt list --host my.zoekt.server
```

See all options:

```shell
zoekt --help
```

### Python API Usage

```python
from zoektpy import ZoektClient

client = ZoektClient(host="my.zoekt.server", port=6070)
result = client.search("def my_function", options={"NumContextLines": 2})

for file in result.Files:
    print(file.FileName, file.Repository)
    for match in file.LineMatches or []:
        print(match.get_decoded_line())

client.close()
```

#### Async Usage

```python
import asyncio
from zoektpy import AsyncZoektClient

async def main():
    client = AsyncZoektClient(host="my.zoekt.server")
    result = await client.search("class MyClass")
    for file in result.Files:
        print(file.FileName)
    await client.close()

asyncio.run(main())
```

---

## Features

- Synchronous and asynchronous clients
- Advanced search: by language, file pattern, repo, case sensitivity, symbols, context lines
- List and filter repositories
- Rich CLI with colorized output and JSON export
- Fully typed models and robust error handling

---

## Command-Line Interface (CLI)

The CLI provides convenient access to Zoekt search and repository listing.

### Search

```shell
zoekt search "<query>" [OPTIONS]
```

**Options:**
- `--host` (default: localhost)
- `--port` (default: 6070)
- `--timeout` (default: 10.0)
- `--context`, `-c`: Number of context lines (default: 3)
- `--max-matches`, `-m`: Max matches to display (default: 20)
- `--language`, `-l`: Filter by language
- `--file`, `-f`: Filter by file pattern
- `--repo`, `-r`: Filter by repository
- `--case-sensitive`: Enable case sensitivity
- `--json`: Output raw JSON
- `--debug`: Enable debug output

### List Repositories

```shell
zoekt list [<query>] [OPTIONS]
```

**Options:**
- `--host`, `--port`, `--timeout` (as above)
- `--json`: Output raw JSON

---

## Python API

### ZoektClient (sync)

```python
from zoektpy import ZoektClient
client = ZoektClient(host="localhost", port=6070)
result = client.search("foo bar", options={"NumContextLines": 2})
repos = client.list_repositories("repo:myorg/")
client.close()
```

### AsyncZoektClient (async)

```python
from zoektpy import AsyncZoektClient
client = AsyncZoektClient(host="localhost")
result = await client.search("foo bar")
await client.close()
```

### Search Options

You can pass advanced options via the `options` argument (see `SearchOptions` in `zoektpy.models`).

### Error Handling

All errors inherit from `zoektpy.exceptions.ZoektError`.

---

## Development

1. **Clone the repo:**
   ```shell
   git clone https://github.com/udbhav-44/zoekt-py.git
   cd zoekt-py
   ```
2. **Install dependencies:**
   ```shell
   pip install -e .[dev]
   ```
3. **Run tests:**
   ```shell
   pytest
   ```
4. **Lint and format:**
   ```shell
   black zoektpy/ tests/
   flake8 zoektpy/
   mypy zoektpy/
   ```

---

## Contributing

Contributions are welcome! Please open issues or pull requests on [GitHub](https://github.com/udbhav-44/zoekt-py).

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a full list of changes.
 
---


<p align="center">
  <em>Made with ❤️ by Udbhav Agarwal</em>
</p>
