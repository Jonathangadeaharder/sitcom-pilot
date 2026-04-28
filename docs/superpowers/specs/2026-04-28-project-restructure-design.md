# Project Restructure Design

**Date:** 2026-04-28  
**Epic:** E0 - Foundation & New Schema  
**Item:** E0.2 - Project layout: `src/sitcom_pilot/` + uv workspace  
**Status:** Design Complete - Ready for Implementation

---

## 1. Overview

### 1.1 Problem Statement

The current project uses a flat `orchestrator/` directory structure that:
- Doesn't follow modern Python packaging best practices
- Lacks uv workspace support for monorepo development
- Makes it difficult to add new packages (CLI, utilities, tests)
- Doesn't scale well for future growth

### 1.2 Goals

1. **Better Package Organization**: Move from `orchestrator/` to `src/sitcom_pilot/` structure
2. **uv Workspace Support**: Enable monorepo development with multiple packages
3. **Future-Proofing**: Create structure that accommodates future packages
4. **Maintainability**: Keep existing functionality while improving organization

### 1.3 Success Criteria

- All existing tests pass after restructuring
- uv workspace configuration works correctly
- CLI entry points function properly
- All imports are updated and working
- No breaking changes to existing functionality

---

## 2. Directory Structure

### 2.1 Proposed Structure

```
sitcom_pilot/
├── src/
│   ├── sitcom_pilot/           # Core package
│   │   ├── __init__.py
│   │   ├── assembler.py
│   │   ├── audio_builder.py
│   │   ├── comfyui_client.py
│   │   ├── config.py
│   │   ├── loader.py
│   │   ├── manifest.py
│   │   ├── node_map.py
│   │   ├── paths.py
│   │   ├── progress.py
│   │   ├── prompts.py
│   │   ├── renderer.py
│   │   ├── validator.py
│   │   └── cli/                # CLI subpackage
│   │       ├── __init__.py
│   │       └── main.py
│   ├── sitcom_pilot_utils/     # Utilities package
│   │   ├── __init__.py
│   │   └── helpers.py
│   └── sitcom_pilot_tests/     # Test utilities package
│       ├── __init__.py
│       └── fixtures.py
├── tests/                      # Root-level tests
│   ├── conftest.py
│   ├── test_assembler.py
│   ├── test_audio_builder.py
│   └── ... (other test files)
├── schemas/
│   └── episode_v2.schema.json
├── docs/
├── pyproject.toml              # Root-level workspace config
├── uv.lock
└── .gitignore
```

### 2.2 Key Design Decisions

1. **Flat src/ layout**: All packages directly in `src/` for simplicity
2. **CLI as subpackage**: CLI is part of the core package, not separate
3. **Tests at root**: Tests remain at root level, not as a package
4. **Schema at root**: Schema files stay at root level for easy access

---

## 3. pyproject.toml Configuration

### 3.1 Root Configuration

```toml
[project]
name = "sitcom-pilot"
version = "0.1.0"
description = "Beat-based AI sitcom pilot pipeline (Buffering S01)"
requires-python = ">=3.11"
dependencies = [
    # CLI
    "typer>=0.12.0",
    # Data modelling & config
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    # Structured logging
    "structlog>=24.0.0",
    # Episode schema validation
    "jsonschema>=4.21.0",
    # AIServices integration
    "aiservices-core",
    # Legacy audio pipeline deps
    "ormsgpack>=1.12.2",
]

[tool.uv]
dev-dependencies = [
    "mutmut>=3.5.0",
    "pytest>=9.0.3",
    "pytest-cov>=7.1.0",
]

[tool.uv.sources]
aiservices-core = { path = "../AIServices/packages/aiservices_core", editable = true }

[project.scripts]
sitcom-pilot = "sitcom_pilot.cli.main:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_paths = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
ignore = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sitcom_pilot", "src/sitcom_pilot_utils", "src/sitcom_pilot_tests"]
```

### 3.2 Key Configuration Points

1. **Build System**: Uses hatchling for modern Python packaging
2. **CLI Entry Point**: Updated to `sitcom_pilot.cli.main:app`
3. **Package Discovery**: Includes all packages in `src/`
4. **Test Configuration**: Adds `src` to Python path for imports
5. **uv Workspace**: Supports monorepo development

---

## 4. Import Updates

### 4.1 Import Migration Strategy

**Current imports:**
```python
from orchestrator.loader import EpisodeLoader
from orchestrator.config import PipelineConfig
from orchestrator.validator import EpisodeValidator
```

**New imports:**
```python
from sitcom_pilot.loader import EpisodeLoader
from sitcom_pilot.config import PipelineConfig
from sitcom_pilot.validator import EpisodeValidator
```

### 4.2 Files Requiring Updates

1. **Core package files**: All files in `src/sitcom_pilot/`
2. **Test files**: All files in `tests/`
3. **CLI files**: Files in `src/sitcom_pilot/cli/`
4. **Utility files**: Files in `src/sitcom_pilot_utils/`
5. **Documentation**: Any docs referencing `orchestrator`

### 4.3 Migration Commands

```bash
# Update imports in all Python files
find . -name "*.py" -type f -exec sed -i 's/orchestrator\./sitcom_pilot./g' {} \;

# Update relative imports within package
find src/sitcom_pilot -name "*.py" -type f -exec sed -i 's/from \./from sitcom_pilot./g' {} \;
```

---

## 5. CLI Structure

### 5.1 CLI Package Structure

```
src/sitcom_pilot/
├── cli/
│   ├── __init__.py
│   └── main.py
├── __init__.py
└── ... (other modules)
```

### 5.2 CLI Implementation

**main.py:**
```python
from __future__ import annotations

import typer
from pathlib import Path
from sitcom_pilot.config import PipelineConfig
from sitcom_pilot.loader import EpisodeLoader
from sitcom_pilot.validator import EpisodeValidator

app = typer.Typer(help="Sitcom Pilot CLI")

@app.command()
def validate(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    strict: bool = typer.Option(False, help="Enable strict validation"),
) -> None:
    """Validate an episode JSON file."""
    validator = EpisodeValidator()
    errors = validator.validate_file(Path(episode_path), strict=strict)
    if errors:
        for error in errors:
            typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1)
    typer.echo("Episode is valid!")

@app.command()
def run(
    episode_path: str = typer.Argument(..., help="Path to episode JSON file"),
    config_file: str = typer.Option(None, help="Path to config file"),
) -> None:
    """Run the sitcom pilot pipeline."""
    # Implementation here
    pass

if __name__ == "__main__":
    app()
```

### 5.3 Entry Point

**pyproject.toml:**
```toml
[project.scripts]
sitcom-pilot = "sitcom_pilot.cli.main:app"
```

---

## 6. Testing Strategy

### 6.1 Test Configuration

**pyproject.toml:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_paths = ["src"]
```

### 6.2 Test Import Updates

**Current:**
```python
from orchestrator.loader import EpisodeLoader
from orchestrator.config import PipelineConfig
```

**New:**
```python
from sitcom_pilot.loader import EpisodeLoader
from sitcom_pilot.config import PipelineConfig
```

### 6.3 Test Utilities Package

**src/sitcom_pilot_tests/fixtures.py:**
```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

@pytest.fixture
def sample_episode():
    """Provide a sample episode for testing."""
    return {
        "show": "Buffering",
        "season": 1,
        "episode": 1,
        "title": "Test Episode",
        "schema_version": "2.0",
        "cast": {},
        "environments": {},
        "scenes": []
    }
```

---

## 7. Migration Steps

### 7.1 Step-by-Step Migration

**Step 1: Create directory structure**
```bash
mkdir -p src/sitcom_pilot/cli
mkdir -p src/sitcom_pilot_utils
mkdir -p src/sitcom_pilot_tests
```

**Step 2: Move orchestrator/ to src/sitcom_pilot/**
```bash
mv orchestrator/* src/sitcom_pilot/
```

**Step 3: Create __init__.py files**
```bash
touch src/sitcom_pilot/__init__.py
touch src/sitcom_pilot/cli/__init__.py
touch src/sitcom_pilot_utils/__init__.py
touch src/sitcom_pilot_tests/__init__.py
```

**Step 4: Update imports in all Python files**
```bash
find . -name "*.py" -type f -exec sed -i 's/orchestrator\./sitcom_pilot./g' {} \;
```

**Step 5: Update pyproject.toml**
- Update build system to hatchling
- Update package configuration
- Update CLI entry point

**Step 6: Create CLI main.py**
- Move CLI logic from orchestrator to `src/sitcom_pilot/cli/main.py`

**Step 7: Update test imports**
```bash
find tests -name "*.py" -type f -exec sed -i 's/orchestrator\./sitcom_pilot./g' {} \;
```

**Step 8: Remove old orchestrator/ directory**
```bash
rm -rf orchestrator/
```

**Step 9: Run tests to verify**
```bash
uv run pytest
```

**Step 10: Update documentation**
- Update any references to `orchestrator` in docs

### 7.2 Rollback Plan

If issues arise:
1. Restore `orchestrator/` from git
2. Revert pyproject.toml changes
3. Revert import changes
4. Run tests to verify

---

## 8. Risk Assessment

### 8.1 Potential Risks

1. **Import Breakage**: Some imports may not update correctly
   - **Mitigation**: Use find/sed carefully, verify with tests
   
2. **CLI Entry Point**: CLI may not work after restructuring
   - **Mitigation**: Test CLI separately after migration
   
3. **Test Failures**: Tests may fail due to import issues
   - **Mitigation**: Run tests after each step
   
4. **uv Workspace Issues**: uv may not recognize new structure
   - **Mitigation**: Verify uv workspace configuration

### 8.2 Success Metrics

- All existing tests pass
- CLI commands work correctly
- uv workspace recognizes all packages
- No import errors in any package

---

## 9. Future Considerations

### 9.1 Potential Additions

1. **sitcom_pilot_web**: Web interface for the pipeline
2. **sitcom_pilot_api**: REST API for the pipeline
3. **sitcom_pilot_monitor**: Monitoring and logging package
4. **sitcom_pilot_deploy**: Deployment utilities

### 9.2 Scalability

The new structure supports:
- Adding new packages without restructuring
- Independent versioning of packages
- Clear separation of concerns
- Easy dependency management between packages

---

## 10. Approval

**Design Approved:** 2026-04-28  
**Approved By:** User  
**Next Step:** Implementation Planning

---

## Appendix A: File Checklist

### Files to Create
- [ ] `src/sitcom_pilot/__init__.py`
- [ ] `src/sitcom_pilot/cli/__init__.py`
- [ ] `src/sitcom_pilot/cli/main.py`
- [ ] `src/sitcom_pilot_utils/__init__.py`
- [ ] `src/sitcom_pilot_utils/helpers.py`
- [ ] `src/sitcom_pilot_tests/__init__.py`
- [ ] `src/sitcom_pilot_tests/fixtures.py`

### Files to Modify
- [ ] `pyproject.toml`
- [ ] All Python files in `src/sitcom_pilot/`
- [ ] All test files in `tests/`
- [ ] Documentation files

### Files to Delete
- [ ] `orchestrator/` (after migration)

---

## Appendix B: Commands Reference

### Migration Commands
```bash
# Create directory structure
mkdir -p src/sitcom_pilot/cli src/sitcom_pilot_utils src/sitcom_pilot_tests

# Move orchestrator to new location
mv orchestrator/* src/sitcom_pilot/

# Create __init__.py files
touch src/sitcom_pilot/__init__.py src/sitcom_pilot/cli/__init__.py src/sitcom_pilot_utils/__init__.py src/sitcom_pilot_tests/__init__.py

# Update imports
find . -name "*.py" -type f -exec sed -i 's/orchestrator\./sitcom_pilot./g' {} \;

# Remove old directory
rm -rf orchestrator/

# Run tests
uv run pytest
```

### Verification Commands
```bash
# Check imports
python -c "from sitcom_pilot.loader import EpisodeLoader; print('Import OK')"

# Check CLI
sitcom-pilot --help

# Check uv workspace
uv workspace list
```
