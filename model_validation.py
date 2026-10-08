#!/usr/bin/env python3
"""
model_validation
================

Shared TOML model validation utilities for PukahaPai.

The model developer may (optionally) specify hard admissibility limits in the
TOML file under

    [limits.parameters.<name>]
    [limits.initial_conditions.<name>]

Supported fields are:

    min = <number>
    max = <number>
    min_inclusive = true|false   # default: true
    max_inclusive = true|false   # default: true
    description = "optional human-readable explanation"

Only quantities for which the model developer supplies limits are checked.
This is deliberate: exploratory models are not required to constrain every
parameter or initial condition.
"""

from pathlib import Path
from numbers import Real


class ModelValidationError(ValueError):
    """Raised when a TOML model violates its declared admissibility rules."""

    def __init__(self, errors, model_name=None):
        self.errors = list(errors)
        self.model_name = model_name
        label = f" for '{model_name}'" if model_name else ""
        message = f"Model validation failed{label}:\n" + "\n".join(
            f"  - {error}" for error in self.errors
        )
        super().__init__(message)


def _is_number(value):
    """True for real numeric values, but not bool (which subclasses int)."""
    return isinstance(value, Real) and not isinstance(value, bool)


def _format_bound(name, rule):
    """Return a compact human-readable mathematical bound."""
    parts = []
    if "min" in rule:
        op = ">=" if rule.get("min_inclusive", True) else ">"
        parts.append(f"{name} {op} {rule['min']}")
    if "max" in rule:
        op = "<=" if rule.get("max_inclusive", True) else "<"
        parts.append(f"{name} {op} {rule['max']}")
    return " and ".join(parts) if parts else "no bound"


def _validate_rule_schema(group_name, quantity_name, rule, errors):
    if not isinstance(rule, dict):
        errors.append(
            f"limits.{group_name}.{quantity_name} must be a TOML table"
        )
        return False

    allowed = {
        "min",
        "max",
        "min_inclusive",
        "max_inclusive",
        "description",
    }
    unknown = sorted(set(rule) - allowed)
    if unknown:
        errors.append(
            f"limits.{group_name}.{quantity_name} has unknown field(s): "
            + ", ".join(unknown)
        )

    for bound in ("min", "max"):
        if bound in rule and not _is_number(rule[bound]):
            errors.append(
                f"limits.{group_name}.{quantity_name}.{bound} must be numeric"
            )

    for flag in ("min_inclusive", "max_inclusive"):
        if flag in rule and not isinstance(rule[flag], bool):
            errors.append(
                f"limits.{group_name}.{quantity_name}.{flag} must be true or false"
            )

    if "description" in rule and not isinstance(rule["description"], str):
        errors.append(
            f"limits.{group_name}.{quantity_name}.description must be a string"
        )

    if "min" not in rule and "max" not in rule:
        errors.append(
            f"limits.{group_name}.{quantity_name} must specify min and/or max"
        )
        return False

    if (
        "min" in rule
        and "max" in rule
        and _is_number(rule["min"])
        and _is_number(rule["max"])
    ):
        if rule["min"] > rule["max"]:
            errors.append(
                f"limits.{group_name}.{quantity_name}: min exceeds max"
            )
        elif rule["min"] == rule["max"] and (
            not rule.get("min_inclusive", True)
            or not rule.get("max_inclusive", True)
        ):
            errors.append(
                f"limits.{group_name}.{quantity_name}: empty interval at "
                f"{rule['min']}"
            )

    return True


def _violates(value, rule):
    if "min" in rule:
        if rule.get("min_inclusive", True):
            if value < rule["min"]:
                return True
        elif value <= rule["min"]:
            return True

    if "max" in rule:
        if rule.get("max_inclusive", True):
            if value > rule["max"]:
                return True
        elif value >= rule["max"]:
            return True

    return False


def validate_model_spec(config, model_name=None):
    """
    Validate only the limits explicitly declared by the model developer.

    Returns the original config unchanged on success.  Raises
    ModelValidationError containing all detected problems on failure.
    """
    if model_name is None:
        model_name = config.get("model_name")

    errors = []
    limits = config.get("limits", {})

    if not isinstance(limits, dict):
        raise ModelValidationError(
            ["[limits] must be a TOML table"], model_name=model_name
        )

    supported_groups = {
        "parameters": config.get("parameters", {}),
        "initial_conditions": config.get("initial_conditions", {}),
    }

    unknown_groups = sorted(set(limits) - set(supported_groups))
    if unknown_groups:
        errors.append(
            "[limits] has unsupported group(s): " + ", ".join(unknown_groups)
        )

    for group_name, values in supported_groups.items():
        group_limits = limits.get(group_name, {})
        if not isinstance(group_limits, dict):
            errors.append(f"[limits.{group_name}] must be a TOML table")
            continue

        for quantity_name, rule in group_limits.items():
            schema_ok = _validate_rule_schema(
                group_name, quantity_name, rule, errors
            )

            if quantity_name not in values:
                errors.append(
                    f"limits.{group_name}.{quantity_name} refers to an undefined "
                    f"{group_name[:-1] if group_name.endswith('s') else group_name}"
                )
                continue

            value = values[quantity_name]
            if not _is_number(value):
                errors.append(
                    f"{group_name}.{quantity_name} must be numeric to use limits"
                )
                continue

            if schema_ok and not any(
                msg.startswith(f"limits.{group_name}.{quantity_name}")
                for msg in errors
            ):
                if _violates(value, rule):
                    description = rule.get("description")
                    extra = f" ({description})" if description else ""
                    errors.append(
                        f"{group_name}.{quantity_name} = {value} violates "
                        f"{_format_bound(quantity_name, rule)}{extra}"
                    )

    if errors:
        raise ModelValidationError(errors, model_name=model_name)

    return config


def get_model_limits(config, group=None):
    """
    Return the declared limit metadata.

    This is intentionally simple so a future GUI can use the same TOML limits
    to configure widgets without duplicating model rules in GUI source code.
    """
    limits = config.get("limits", {})
    if group is None:
        return limits
    return limits.get(group, {})


def load_and_validate_model(path):
    """Load a TOML model and validate its declared limits."""
    path = Path(path)

    try:
        import tomllib
    except ModuleNotFoundError:  # Python <= 3.10
        import toml
        config = toml.load(path)
    else:
        with path.open("rb") as f:
            config = tomllib.load(f)

    return validate_model_spec(config, model_name=config.get("model_name", path.stem))
