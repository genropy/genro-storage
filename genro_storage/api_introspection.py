# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""API structure introspection utilities.

This module provides utilities to extract API metadata from classes decorated
with @apiready. Will be moved to genro-core in the future.
"""

from __future__ import annotations

import inspect
import json
from typing import Any, get_type_hints, get_origin, get_args


def get_api_structure(
    target: type | object, *, eager: bool = True, mode: str = "json"
) -> str | dict:
    """Extract API structure from an @apiready decorated class.

    Args:
        target: Class or instance to introspect
        eager: If True, recursively collect all API metadata (default: True)
        mode: Output format - "json" (default), "yaml", "markdown"/"md", or "html"

    Returns:
        API structure as JSON string, YAML string, Markdown string, HTML string, or dict (if mode not recognized)

    Example:
        >>> from genro_storage import StorageManager
        >>> structure = get_api_structure(StorageManager, mode="json")
        >>> print(structure)
    """
    # Get the class if instance was passed
    if not inspect.isclass(target):
        target = target.__class__

    # Check if class is decorated with @apiready
    if not hasattr(target, "_api_base_path"):
        raise ValueError(
            f"Class {target.__name__} is not decorated with @apiready. "
            "Only @apiready decorated classes can be introspected."
        )

    # Collect structure
    structure = {"class_name": target.__name__, "base_path": target._api_base_path, "endpoints": []}

    # Add class docstring if available
    if target.__doc__:
        structure["docstring"] = inspect.cleandoc(target.__doc__)

    # Iterate through class members to find decorated methods
    for name, method in inspect.getmembers(target, inspect.isfunction):
        # Check if method has API metadata
        if not hasattr(method, "_api_metadata"):
            continue

        metadata = method._api_metadata

        # Build full endpoint path
        full_path = structure["base_path"] + metadata["endpoint_path"]

        # Extract parameter information
        parameters = _extract_parameter_info(metadata["request_fields"])

        # Extract return type information
        return_info = _extract_type_info(metadata["return_type"])

        # Build endpoint entry
        endpoint = {
            "path": full_path,
            "method": metadata["http_method"],
            "function_name": name,
            "parameters": parameters,
            "return_type": return_info,
        }

        # Add docstring if available
        if metadata.get("docstring"):
            endpoint["docstring"] = inspect.cleandoc(metadata["docstring"])

        structure["endpoints"].append(endpoint)

    # Sort endpoints by path for consistent output
    structure["endpoints"].sort(key=lambda x: x["path"])

    # Format output according to mode
    if mode.lower() == "json":
        return json.dumps(structure, indent=2, default=str)
    elif mode.lower() == "yaml":
        try:
            import yaml

            return yaml.dump(structure, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML output. " "Install it with: pip install pyyaml"
            )
    elif mode.lower() in ("markdown", "md"):
        return _format_as_markdown(structure)
    elif mode.lower() == "html":
        return _format_as_html(structure)
    else:
        # Return raw dict if mode not recognized
        return structure


def _extract_parameter_info(request_fields: dict[str, tuple]) -> dict[str, dict]:
    """Extract detailed parameter information from request fields.

    Args:
        request_fields: Dictionary mapping parameter names to (type, default) tuples

    Returns:
        Dictionary with detailed parameter information
    """
    parameters = {}

    for param_name, (param_type, default_value) in request_fields.items():
        param_info = _extract_type_info(param_type)

        # Determine if parameter is required (no default value)
        param_info["required"] = default_value is ...

        # Add default value if present
        if default_value is not ...:
            param_info["default"] = default_value

        parameters[param_name] = param_info

    return parameters


def _extract_type_info(type_hint: Any) -> dict[str, Any]:
    """Extract information from a type hint.

    Handles:
    - Simple types (str, int, bool, etc.)
    - Union types (str | int)
    - Generic types (list[str], dict[str, int])
    - Annotated types with descriptions
    - Forward references ("ClassName")

    Args:
        type_hint: The type hint to analyze

    Returns:
        Dictionary with type information
    """
    info = {}

    # Handle None type
    if type_hint is type(None):
        info["type"] = "None"
        return info

    # Handle string forward references
    if isinstance(type_hint, str):
        info["type"] = type_hint
        return info

    # Check if it's an Annotated type with description
    origin = get_origin(type_hint)

    if origin is not None:
        # Handle typing.Annotated
        if hasattr(origin, "__name__") and origin.__name__ == "Annotated":
            args = get_args(type_hint)
            if args:
                # First arg is the actual type
                actual_type = args[0]
                info.update(_extract_type_info(actual_type))

                # Additional args are metadata (usually descriptions)
                if len(args) > 1:
                    for metadata in args[1:]:
                        if isinstance(metadata, str):
                            info["description"] = metadata
                            break
                return info

        # Handle Union types (including | syntax in Python 3.10+)
        if origin is type(None) or (hasattr(origin, "__name__") and "Union" in origin.__name__):
            args = get_args(type_hint)
            if args:
                type_names = []
                for arg in args:
                    if arg is type(None):
                        type_names.append("None")
                    elif hasattr(arg, "__name__"):
                        type_names.append(arg.__name__)
                    else:
                        type_names.append(str(arg))
                info["type"] = " | ".join(type_names)
                return info

        # Handle generic types (list, dict, etc.)
        if hasattr(origin, "__name__"):
            args = get_args(type_hint)
            if args:
                arg_names = []
                for arg in args:
                    if hasattr(arg, "__name__"):
                        arg_names.append(arg.__name__)
                    else:
                        arg_names.append(str(arg))
                info["type"] = f"{origin.__name__}[{', '.join(arg_names)}]"
            else:
                info["type"] = origin.__name__
            return info

    # Handle simple types with __name__
    if hasattr(type_hint, "__name__"):
        info["type"] = type_hint.__name__
        return info

    # Fallback: convert to string
    info["type"] = str(type_hint)
    return info


def get_api_structure_multi(
    *targets: type | object, eager: bool = True, mode: str = "json"
) -> str | list[dict]:
    """Extract API structure from multiple @apiready decorated classes.

    Args:
        *targets: Classes or instances to introspect
        eager: If True, recursively collect all API metadata (default: True)
        mode: Output format - "json" (default) or "yaml"

    Returns:
        API structures as JSON string, YAML string, or list of dicts

    Example:
        >>> from genro_storage import StorageManager
        >>> from genro_storage.node import StorageNode
        >>> structure = get_api_structure_multi(
        ...     StorageManager, StorageNode, mode="json"
        ... )
    """
    structures = []

    for target in targets:
        # Get structure as dict
        structure = get_api_structure(target, eager=eager, mode="dict")
        structures.append(structure)

    # Format output according to mode
    if mode.lower() == "json":
        return json.dumps(structures, indent=2, default=str)
    elif mode.lower() == "yaml":
        try:
            import yaml

            return yaml.dump(structures, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML output. " "Install it with: pip install pyyaml"
            )
    else:
        # Return raw list if mode not recognized
        return structures


def _format_as_html(structure: dict) -> str:
    """Format API structure as HTML.

    Args:
        structure: API structure dictionary

    Returns:
        HTML-formatted string
    """
    lines = []

    # HTML header with minimal CSS
    lines.append("<!DOCTYPE html>")
    lines.append("<html>")
    lines.append("<head>")
    lines.append(f"<title>{structure['class_name']} API</title>")
    lines.append("<style>")
    lines.append("body { font-family: monospace; margin: 20px; }")
    lines.append("h3 { color: #333; }")
    lines.append(".endpoint { margin-bottom: 20px; }")
    lines.append(".name { font-weight: bold; }")
    lines.append(".command { margin-left: 20px; line-height: 1.2; }")
    lines.append(".params { margin-left: 20px; line-height: 1.2; }")
    lines.append("</style>")
    lines.append("</head>")
    lines.append("<body>")

    # Title
    lines.append(f"<h3>{structure['class_name']} [{structure['base_path']}]</h3>")

    # Endpoints
    for endpoint in structure["endpoints"]:
        method = endpoint["method"]
        path = endpoint["path"]
        func = endpoint["function_name"]
        return_type = endpoint.get("return_type", {})
        return_type_str = return_type.get("type", "None")

        lines.append('<div class="endpoint">')
        lines.append(f'  <div class="name">{func}</div>')
        lines.append(f'  <div class="command">{method} {path} -&gt; {return_type_str}</div>')

        # Parameters
        params = endpoint.get("parameters", {})
        if params:
            param_list = []
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "Any")
                required = param_info.get("required", False)
                default = param_info.get("default", "")

                if required:
                    param_list.append(f"{param_name} {param_type}")
                else:
                    if default == "":
                        default_str = ""
                    elif default is None:
                        default_str = "None"
                    else:
                        default_str = str(default)
                    param_list.append(f"{param_name} {param_type}={default_str}")

            lines.append(f'  <div class="params">Parameters: {", ".join(param_list)}</div>')

        lines.append("</div>")

    # HTML footer
    lines.append("</body>")
    lines.append("</html>")

    return "\n".join(lines)


def _format_as_markdown(structure: dict) -> str:
    """Format API structure as compact Markdown list.

    Args:
        structure: API structure dictionary

    Returns:
        Markdown-formatted string (compact, no docstrings)
    """
    lines = []

    # Title: ClassName [/base_path]
    lines.append(f"### {structure['class_name']} [{structure['base_path']}]")
    lines.append("")

    for endpoint in structure["endpoints"]:
        method = endpoint["method"]
        path = endpoint["path"]
        func = endpoint["function_name"]
        return_type = endpoint.get("return_type", {})
        return_type_str = return_type.get("type", "None")

        # Parameters (compact, one line)
        params = endpoint.get("parameters", {})
        param_line = ""
        if params:
            param_list = []
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "Any")
                required = param_info.get("required", False)
                default = param_info.get("default", "")

                if required:
                    param_list.append(f"{param_name} {param_type}")
                else:
                    if default == "":
                        default_str = ""
                    elif default is None:
                        default_str = "None"
                    else:
                        default_str = str(default)
                    param_list.append(f"{param_name} {param_type}={default_str}")

            param_line = f"<br>&nbsp;&nbsp;Parameters: {', '.join(param_list)}"

        # Use HTML for tight control: name, command, params (tight), then space
        lines.append(
            f"**{func}**<br>" f"&nbsp;&nbsp;{method} {path} -> {return_type_str}" f"{param_line}"
        )
        lines.append("")

    return "\n".join(lines)
