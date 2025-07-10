"""XML utilities for converting between nested dictionaries and XML format."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Union, List
import html


def dict_to_xml(data: Dict[str, Any], root_tag: str = "root") -> str:
    """Convert a nested dictionary to XML string format.

    Args:
        data: Dictionary to convert to XML
        root_tag: Tag name for the root element

    Returns:
        Pretty-printed XML string

    Notes:
        - None values are omitted from the output
        - List values create multiple elements with the same tag name
        - Special XML characters are automatically escaped
    """
    root = ET.Element(root_tag)
    _dict_to_element(data, root)

    # Convert to string with pretty printing
    xml_str = ET.tostring(root, encoding="unicode")
    return _pretty_print_xml(xml_str)


def xml_to_dict(xml_content: str) -> Dict[str, Any]:
    """Parse XML string back to a nested dictionary.

    Args:
        xml_content: XML string to parse

    Returns:
        Dictionary representation of the XML content (without root element)

    Notes:
        - Repeated elements are converted to lists
        - XML entities are automatically unescaped
    """
    root = ET.fromstring(xml_content)
    return _element_to_dict(root)


def write_xml_file(
    data: Dict[str, Any], file_path: Path, root_tag: str = "metadata"
) -> None:
    """Write dictionary data as an XML file.

    Args:
        data: Dictionary to write as XML
        file_path: Path where to write the XML file
        root_tag: Tag name for the root element

    Notes:
        - Creates parent directories if they don't exist
        - Overwrites existing files
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    xml_content = dict_to_xml(data, root_tag)
    file_path.write_text(xml_content)


def read_xml_file(file_path: Path) -> Dict[str, Any]:
    """Read an XML file and return its content as a dictionary.

    Args:
        file_path: Path to the XML file

    Returns:
        Dictionary representation of the XML content
    """
    xml_content = file_path.read_text()
    return xml_to_dict(xml_content)


def _dict_to_element(data: Dict[str, Any], parent: ET.Element) -> None:
    """Recursively convert dictionary data to XML elements.

    Args:
        data: Dictionary to convert
        parent: Parent XML element to add children to
    """
    for key, value in data.items():
        if value is None:
            # Skip None values
            continue

        if isinstance(value, list):
            # Create multiple elements for list values
            for item in value:
                elem = ET.SubElement(parent, key)
                if isinstance(item, dict):
                    _dict_to_element(item, elem)
                else:
                    elem.text = str(item)
        elif isinstance(value, dict):
            # Recursive case for nested dictionaries
            elem = ET.SubElement(parent, key)
            _dict_to_element(value, elem)
        else:
            # Simple value case
            elem = ET.SubElement(parent, key)
            elem.text = str(value)


def _element_to_dict(element: ET.Element) -> Dict[str, Any]:
    """Recursively convert XML element to dictionary.

    Args:
        element: XML element to convert

    Returns:
        Dictionary representation of the element
    """
    result = {}

    # Group children by tag name to handle lists
    children_by_tag = {}
    for child in element:
        tag = child.tag
        if tag not in children_by_tag:
            children_by_tag[tag] = []
        children_by_tag[tag].append(child)

    for tag, children in children_by_tag.items():
        if len(children) == 1:
            # Single element
            child = children[0]
            if len(child) == 0:
                # Leaf node - just text content
                result[tag] = child.text or ""
            else:
                # Has children - recurse
                result[tag] = _element_to_dict(child)
        else:
            # Multiple elements with same tag - create list
            result[tag] = []
            for child in children:
                if len(child) == 0:
                    # Leaf node
                    result[tag].append(child.text or "")
                else:
                    # Has children
                    result[tag].append(_element_to_dict(child))

    return result


def _pretty_print_xml(xml_str: str) -> str:
    """Add pretty printing (indentation) to XML string.

    Args:
        xml_str: Raw XML string

    Returns:
        Pretty-printed XML string with proper indentation
    """
    # Parse and re-format with indentation
    root = ET.fromstring(xml_str)
    _indent_element(root, 0)
    result = ET.tostring(root, encoding="unicode")
    # Remove trailing newline if present
    return result.rstrip("\n")


def _indent_element(element: ET.Element, level: int) -> None:
    """Add indentation to XML element and its children.

    Args:
        element: XML element to indent
        level: Current indentation level
    """
    indent = "\n" + "    " * level

    if len(element):
        if not element.text or not element.text.strip():
            element.text = indent + "    "
        if not element.tail or not element.tail.strip():
            element.tail = indent
        for elem in element:
            _indent_element(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
    else:
        # For empty elements, ensure they have proper formatting
        if level == 0:
            # Root element with no children - add newline inside
            element.text = "\n"
        elif not element.tail or not element.tail.strip():
            element.tail = indent
