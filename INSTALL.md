# Install ContextZero

ContextZero requires Python 3.10 or newer.

## macOS

```bash
python3 --version
python3 -m pip install git+https://github.com/<your-username>/contextzero.git
contextzero init --install-claude --brain
contextzero doctor . --brain
```

For editable development:

```bash
git clone https://github.com/<your-username>/contextzero.git
cd contextzero
python3 -m pip install -e .[dev]
pytest
```

## Windows PowerShell

```powershell
py --version
py -m pip install git+https://github.com/<your-username>/contextzero.git
contextzero init --install-claude --brain
contextzero doctor . --brain
```

For editable development:

```powershell
git clone https://github.com/<your-username>/contextzero.git
cd contextzero
py -m pip install -e .[dev]
pytest
```

## WSL/Linux

```bash
python3 --version
python3 -m pip install git+https://github.com/<your-username>/contextzero.git
contextzero init --install-claude --brain
contextzero doctor . --brain
```

For editable development:

```bash
git clone https://github.com/<your-username>/contextzero.git
cd contextzero
python3 -m pip install -e .[dev]
pytest
```

## Claude Code

```bash
contextzero init --install-claude --brain
```

Then open Claude Code and type:

```text
/contextzero
```

or:

```text
/contextzero landing page patch
```

## Codex CLI

Run ContextZero before starting a task:

```bash
contextzero session-bootstrap . "landing page patch"
```

Use the `Read first` files as the initial context. Avoid stale files unless the user explicitly asks for them.
