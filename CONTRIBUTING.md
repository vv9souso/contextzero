# Contributing

ContextZero is a local-first developer tool. Contributions should keep the CLI small, predictable, and cross-platform.

## Development

```bash
python -m pip install -e .[dev]
pytest
```

## Guidelines

- Keep scans local.
- Use `pathlib`.
- Label token counts and savings as estimates.
- Add tests for scanner, memory, report, and CLI behavior changes.
- Avoid new dependencies unless they are clearly needed.
