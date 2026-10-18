# ID Generation

URL-safe nanoid generation.

## Simple generation

```python
from pw_foundation.utils.ids import generate_id

generate_id()  # "V1StGXR8_Z5j" (12 chars default)
generate_id(size=8)  # "k3J9xQ2m"
generate_id(size=20)  # "aB3kL9xQ2mR7nP4wT6yJ"
```

Characters are drawn from `0-9A-Za-z_-` (64-char URL-safe alphabet).

## Configuration

Default length is read from the `ID_LENGTH` environment variable. Clamped to 8–36; falls back to 12 when unset.

```bash
# In .env
ID_LENGTH=16
```

`generate_id()` reads `os.environ["ID_LENGTH"]` directly, not an `AppConfig` instance. Declaring `ID_LENGTH` on an `AppConfig` subclass only affects ID generation if the value also reaches the environment (e.g. set in `.env`, which dotenv loads).

The `size` parameter overrides the default when provided.

## Collision-safe allocation

For IDs stored in a database table, pw-core's `pw_core.db.ids.allocate_id` generates with `generate_id` and verifies uniqueness against the table before returning (preferred-id support, bounded retries). It needs a SQLAlchemy connection, so it lives with the database layer — see [pw-core's db-ids doc](https://github.com/phierceweb/pw-core/blob/main/src/pw_core/docs/db-ids.md).

## Migrating from consumer projects

**Ad-hoc UUID slicing** — replace `uuid.uuid4().hex[:12]`:

```python
# Before
import uuid

job_id = uuid.uuid4().hex[:12]

# After
from pw_foundation.utils.ids import generate_id

job_id = generate_id()
```
