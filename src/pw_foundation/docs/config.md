# Configuration

`pw_foundation.config.AppConfig` is the base configuration class. Subclass it in each project to declare settings with defaults. Values resolve from env vars, YAML files, and defaults — in that priority order.

## Quick start

```python
from pw_foundation.config import AppConfig


class MyConfig(AppConfig):
    ENABLE_CACHE: bool = True
    MAX_WORKERS: int = 4
    CACHE_TTL_SECONDS: int = 300


cfg = MyConfig(env_file=".env", yaml_file="project.yaml")
```

**Do not** declare per-agent primary model or sampling fields here (e.g. `SUMMARIZER_MODEL`, `CLASSIFIER_TEMPERATURE`). Those live in `config/model_router.yaml` — see [model-router.md](https://github.com/phierceweb/pw-core/blob/main/src/pw_core/docs/model-router.md). `AppConfig` is for cross-cutting app settings and tunables that don't vary per agent.

## Resolution order

Each setting resolves in this order (highest priority wins):

1. **Explicit overrides** passed to the constructor
2. **Environment variables** (loaded from `.env` via python-dotenv)
3. **YAML config file** (project-level domain config)
4. **Class attribute defaults**

## Built-in settings

These are declared on `AppConfig` and available to every project:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `LOG_LEVEL` | `str` | `"INFO"` | Console log level |
| `LOG_FILE` | `str` | `""` | JSON-lines log file path (empty = disabled) |
| `APP_NAME` | `str` | `"App"` | Application name (sent in API headers) |
| `APP_URL` | `str` | `""` | Application URL (sent in API headers) |

pw-core's `pw_core.config.AppConfig` subclasses this one with the framework's settings (database, providers, web server, limits); a project on pw-core subclasses that class, and its config doc lists them.

## Type coercion

Env vars are strings. `AppConfig` coerces them based on the default value's type:

| Default type | Coercion |
|-------------|----------|
| `bool` | `"1"`, `"true"`, `"yes"`, `"on"` → `True`; everything else → `False` |
| `int` | `int(val)`, falls back to default on error |
| `float` | `float(val)`, falls back to default on error |
| `list[str]` | Comma-separated string → list (e.g. `"a, b, c"` → `["a", "b", "c"]`) |
| `str` | Stripped, no conversion |

## YAML access

The raw YAML dict is available as `cfg.yaml`:

```python
cfg = MyConfig(yaml_file="project.yaml")

# Access nested YAML values
categories = cfg.yaml.get("categories", [])
launch_date = cfg.yaml.get("launch_date")
```

Top-level YAML keys that exactly match a declared setting name (e.g. `APP_NAME`) resolve onto the attribute — below env vars, above the class default. String values get the same type coercion as env vars; other values arrive typed from YAML. All other keys (lower-case domain config) are never mapped to attributes — read them via `cfg.yaml`, which always holds the full raw dict, resolved keys included.

A missing `yaml_file` is ignored; a malformed one raises `ConfigurationError` naming the path. A repeated key counts as malformed — see [yaml-utils](yaml-utils.md).

## Dict-style access

```python
cfg.get("FEATURE_FLAG", False)  # like getattr with a default
```

## Example: a project config subclass

```python
class MyAppConfig(AppConfig):
    # In-call fallback knob — legit per-agent config. Primary per-agent
    # model + sampling live in config/model_router.yaml, not here.
    SUMMARIZE_MODEL_FALLBACK: str = "openai/gpt-4o-mini"
    CACHE_TTL_SECONDS: int = 300
    TASK_CACHE_TTL_SECONDS: int = 86400
    RESULT_CACHE: bool = True
    RESULT_CACHE_TTL_SECONDS: int = 90 * 86400


cfg = MyAppConfig(
    env_file=Path(__file__).parent.parent / ".env",
    yaml_file=Path(__file__).parent.parent / "project.yaml",
)
```
