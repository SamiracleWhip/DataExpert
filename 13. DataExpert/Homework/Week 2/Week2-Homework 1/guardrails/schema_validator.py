"""
schema_validator.py — Guardrail 1
Validates that a Claude response dict matches an expected schema (keys + types).
Raises ValueError with a clear message if validation fails.
"""

def validate_schema(data: dict, schema: dict) -> dict:
    """
    Validate that `data` conforms to `schema`.

    `schema` is a dict mapping key names to expected types, e.g.:
        {
            "severity": str,
            "priority": str,
            "labels": list,
            "recommended_owner": str,
        }

    Returns the validated `data` dict unchanged, or raises ValueError.
    """
    missing = [k for k in schema if k not in data]
    if missing:
        raise ValueError(f"Schema validation failed — missing keys: {missing}")

    type_errors = []
    for key, expected_type in schema.items():
        actual = data[key]
        if not isinstance(actual, expected_type):
            type_errors.append(
                f"  '{key}': expected {expected_type.__name__}, got {type(actual).__name__} ({actual!r})"
            )

    if type_errors:
        raise ValueError("Schema validation failed — type mismatches:\n" + "\n".join(type_errors))

    return data
