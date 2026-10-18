---
description: The pw_foundation.exceptions hierarchy, log_exception, catch patterns, CLI and web boundaries
alwaysApply: true
---

# Error Handling

All exceptions thrown from service and orchestrator code must use the hierarchy in
`pw_foundation.exceptions`. Never raise bare `Exception` — it loses structured context and produces an
unsearchable log key.

---

## Exception hierarchy

### `FlowException` — expected domain failures, not bugs

| Class | When to use |
|---|---|
| `InvalidInputError` | Caller supplied invalid parameters or data |
| `PreconditionError` | Required state not met — task already complete, resource locked, step out of order |
| `NotFoundError` | The entity does not exist |
| `ActionNotAllowedError` | A business rule says no |
| `ConfigurationError` | Required config missing or invalid — a setting unset, a config file malformed |

`FlowException` exceptions have no `context` dict — they carry only a message.

`InvalidInputError` is also a `ValueError` and `PreconditionError` a `RuntimeError`, so replacing
a builtin raise with one keeps existing `except` clauses and `pytest.raises` working.

### `AppError` — actual errors, always log with traceback

| Class | When to use |
|---|---|
| `ClientError` | An external API call failed |
| `DataError` | A database or file write or read failed |
| `TaskError` | Task-level failure — carries `task_id` + optional `running_log` |

Projects subclass these for domain-specific errors:

```python
from pw_foundation.exceptions import ClientError


class UploadError(ClientError):
    """External upload API call failed."""
```

**Constructor:** `AppError(message, context=None, *, cause=None)`

```python
raise UploadError(
    "upload API timed out",
    context={"task_id": task_id, "endpoint": endpoint},
    cause=original_exc,
)
```

---

## `log_exception()` — the logging function

```python
from pw_foundation.log import log_exception

log_exception(
    exc,
    message_prepend="upload failed",
    additional_context={"record_id": 7},
    log_level="warning",
    event_prefix="UPL",  # default "APP"
)
```

**Log event key:** `{prefix}-{ClassName}` — the search key in log files.

---

## Catch patterns

### Pattern 1 — Let FlowException bubble (most common)
The CLI/API boundary handles it. No catch required.

### Pattern 2 — Wrap an unexpected exception in a domain error
```python
except Exception as e:
    log_exception(
        UploadError("unexpected failure", context={"task_id": tid}, cause=e),
        message_prepend="upload step failed",
    )
```

### Pattern 3 — Log with context and re-raise
```python
except UploadError as e:
    log_exception(e, additional_context={"task_id": tid})
    raise
```

### Pattern 4 — Non-halting (loop-safe)
```python
for task in pending:
    try:
        run_task(task)
    except Exception as e:
        log_exception(TaskError("failed", context={"task_id": task.id}, cause=e))
        # continue loop
```

---

## CLI and API boundaries

**CLI:** catch `FlowException` → print message, exit 1. Catch `AppError` → `log_exception` + print,
exit 1.

**Web:** map `FlowException` → 4xx and `AppError` → 500. pw-core's app factory does this for
FastAPI; a boundary you write yourself does the same.

Both boundaries also answer a pydantic `ValidationError` that wraps a validator's
`InvalidInputError` as that `InvalidInputError` — `pw_foundation.exceptions.unwrap_flow_exception`.
