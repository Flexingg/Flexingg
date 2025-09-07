# Core Template Tags Documentation

## Overview
The `Flexingg/core/templatetags/` directory contains custom Django template filters for math operations, form attributes, time formatting, fitness data, UI utilities, and trigonometry for layouts (e.g., circular positioning). Filters are registered via `@register.filter` in separate modules: custom_filters.py, filters.py, fitness_filters.py, math_filters.py. Load with `{% load custom_filters %}` (or specific name) in templates. These enhance template logic without views. No inclusion tags or custom tags; only filters.

## custom_filters.py
- **get_width(size_class)**:
  - **Description**: Extracts the numeric width from a size_class string (e.g., 'w-100' -> '100'). Returns '' if invalid.
  - **Parameters**: size_class (str).
  - **Example Usage**:
    ```
    {% load custom_filters %}
    {% width 'w-50' as w %}  <!-- w = '50' -->
    <div style="width: {{ w }}px;">Content</div>
    ```
  - **Use Case**: Parsing CSS utility classes for dynamic styling.

## filters.py
This file has the most filters, covering math, time, forms, utilities.

### Math Filters
- **multiply(value, arg)**:
  - **Description**: Multiplies value by arg (floats to ints); returns 0 on error.
  - **Example**: `{{ 5|multiply:2 }}` → 10.
- **divide(value, arg)**:
  - **Description**: Divides value by arg (int division, handles list len); 0 on error/zero.
  - **Example**: `{{ 10|divide:2 }}` → 5.0.
- **intdiv(value, arg)**:
  - **Description**: Integer division; 0 on error.
  - **Example**: `{{ 10|intdiv:3 }}` → 3.
- **modulo(value, arg)**:
  - **Description**: Remainder; 0 on error.
  - **Example**: `{{ 10|modulo:3 }}` → 1.
- **subtract(value, arg)**:
  - **Description**: value - arg; 0 on error.
  - **Example**: `{{ 10|subtract:3 }}` → 7.
- **length(value)**:
  - **Description**: len of list/tuple/str; 0 on error.
  - **Example**: `{{ mylist|length }}` → number of items.

### Time Filter
- **duration2time(value)**:
  - **Description**: Converts seconds to 'HH:MM:SS'; None on error.
  - **Example**: `{{ 3661|duration2time }}` → '01:01:01'.
  - **Use Case**: Formatting activity durations.

### Form Filters
- **addclass(field, css)**:
  - **Description**: Adds CSS class to form field widget.
  - **Example**: `{{ form.field|addclass:'pixel-input' }}`.
- **attr(field, attr_args)**:
  - **Description**: Sets HTML attr:value on field (e.g., 'style:background:red').
  - **Example**: `{{ form.username|attr:"placeholder:Enter name" }}`.

### Utility Filters
- **range_filter(start, end)**:
  - **Description**: Generates range(start, end); empty range(0) on error.
  - **Example**: `{% for i in 1|range_filter:5 %}{{ i }}{% endfor %}` → 1 2 3 4.
- **sin(value)**, **cos(value)**:
  - **Description**: Math.sin/cos of radians.
  - **Example**: `{{ 3.14|sin }}` → ~0.00 (approx).
- **get_item(dictionary, key)**:
  - **Description**: Safe dict.get(key); None if no dict.
  - **Example**: `{{ my_dict|get_item:'key' }}`.

## fitness_filters.py
- **format_duration_seconds(value)**:
  - **Description**: Formats seconds to 'HH:MM:SS'; '00:00:00' if None.
  - **Example**: `{{ activity.duration|format_duration_seconds }}` → '00:30:45'.
  - **Use Case**: Displaying Garmin activity durations in templates.

## math_filters.py
- **calculate_x(index, total)**:
  - **Description**: Cos-based x position for circular layout (angle = (index*360/total)-90, radius 100).
  - **Example**: `{{ 0|calculate_x:8 }}` → ~0.00 (starting point).
  - **Use Case**: Positioning items in a circle (e.g., stat icons).
- **calculate_y(index, total)**:
  - **Description**: Sin-based y position (-200 + 100*sin(angle)).
  - **Example**: `{{ 0|calculate_y:8 }}` → -100.00.
  - **Use Case**: With calculate_x for radial UI elements.

## Usage Notes
- **Loading**: `{% load filters %}` for filters.py; specific for others.
- **Error Handling**: Most return 0/None on errors for safe templating.
- **Dependencies**: Import math where needed; no external libs.
- **Best Practices**: Use for simple calculations to avoid view bloat; test with invalid inputs.
- **Integration**: Used in components/templates for dynamic content (e.g., charts, forms).

These filters support the pixel-art, fitness-focused UI with calculations for charts and layouts.