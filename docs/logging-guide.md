# ActionMachine Logging: Practical Guide

## Table of Contents

- 1. Introduction
- 2. Setting Up Logging
  - 2.1 Creating a LogCoordinator
  - 2.2 Adding Loggers
  - 2.3 Passing the Coordinator to the Machine
- 3. Using the Logger in Aspects
  - 3.1 Aspect Signature
  - 3.2 Logging Methods
  - 3.3 Passing User Data
- 4. Template Language in Detail
  - 4.1 Variables
    - Available Namespaces
    - Dot‑Path Resolution
  - 4.2 Conditional Logic with `iif`
    - Syntax
    - Examples
    - Nested `iif`
  - 4.3 Color Filters and Functions
    - Filter Syntax (outside `iif`)
    - Function Syntax (inside `iif`)
    - Available Colors
  - 4.4 Sensitive Data Masking
    - Using the `@sensitive` Decorator
    - Parameters
    - Examples
  - 4.5 Strict Underscore Rule
  - 4.6 Debug Function
  - 4.7 Existence Check (`exists`)
- 5. Log Filtering
- 6. Creating a Custom Logger
- 7. Testing with Logging
- 8. Complete Example

---

## 1. Introduction

This guide explains how to use the cross‑cutting logging system in ActionMachine. You will learn how to configure loggers, write log messages from aspects, leverage the template language, and extend the system with your own loggers.

At the heart of the logging system is the **template language** used in log messages. It allows you to insert dynamic values, apply conditional logic, add colours, mask sensitive data, and inspect objects – all in a single line.

The template expressions are evaluated by `ExpressionEvaluator`, which provides a safe set of operations:

- **Comparison operators**: `==`, `!=`, `>`, `<`, `>=`, `<=`
- **Logical operators**: `and`, `or`, `not`
- **Arithmetic**: `+`, `-`, `*`, `/`
- **Built‑in functions**: `len()`, `upper()`, `lower()`, `str()`, `int()`, `float()`, `abs()`, `format_number()`
- **Colour functions**: `red()`, `green()`, `blue()`, `magenta()`, `cyan()`, `yellow()`, `white()`, `grey()`, and background variants (e.g., `bg_red()`)
- **Debug introspection**: `debug(obj)` – returns a formatted string showing the object’s public fields and properties
- **Existence check**: `exists('var.path')` – returns `True` if the variable is defined, otherwise `False`

**New in this version**: You can now use the `|debug` filter directly on a variable, for example `{%var.user|debug}`. This is a much cleaner alternative to wrapping `debug()` inside an `iif` expression. The filter works both outside and inside `iif` blocks, making debugging easier than ever.

---

## 4.6 Debug Function

The `debug()` function accepts any object and returns a formatted string showing its public fields and properties. It is intended for debugging and introspection.

### Using `|debug` Filter (recommended)

The simplest way to output an object’s structure is to append `|debug` to a variable:

{%var.user|debug}

This works both outside and inside `iif` constructs:

{iif(1==1; {%var.user|debug}; '')}

The filter is especially convenient because you don’t have to wrap the call in an `iif` – it works as a direct substitution.

### Using `debug()` Function (inside `iif`)

If you need to call `debug()` inside a conditional expression, you must use the function form. Because `debug()` is a function, it must be placed inside a template as part of an `iif` expression (even if the condition is always true). For example:

{iif(1==1; debug(context.user); '')}

### Output format

- One line per field/property.
- For each, the name, type, and value are shown.
- If the property is decorated with `@sensitive`, its masking configuration is displayed.
- The output is **non‑recursive** (`max_depth=1`). To inspect a nested object, call `debug` on that object directly.

Example output for `context.user`:

UserInfo:
  user_id: str = "bystrov.maxim"
  roles: list[str] = ["user", "admin"]
  extra: dict = {"org": "acme"}
  email: str (sensitive: max_chars=3, char='*', max_percent=50) = "max*****"

---

Остальные разделы остаются без изменений.