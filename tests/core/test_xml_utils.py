import tempfile
from pathlib import Path
from scaffold_learning.core.xml_utils import (
    dict_to_xml,
    xml_to_dict,
    write_xml_file,
    read_xml_file,
)


class TestDictToXml:
    def test_simple_dict(self):
        """Test basic dictionary to XML conversion."""
        data = {"name": "test", "value": "123"}
        result = dict_to_xml(data, "root")

        expected = """<root>
    <name>test</name>
    <value>123</value>
</root>"""
        assert result == expected

    def test_nested_dict(self):
        """Test nested dictionary conversion."""
        data = {"user": {"name": "John", "details": {"age": "30", "city": "NYC"}}}
        result = dict_to_xml(data, "root")

        expected = """<root>
    <user>
        <name>John</name>
        <details>
            <age>30</age>
            <city>NYC</city>
        </details>
    </user>
</root>"""
        assert result == expected

    def test_list_values(self):
        """Test handling of list values."""
        data = {"items": ["apple", "banana", "cherry"], "numbers": ["1", "2", "3"]}
        result = dict_to_xml(data, "root")

        expected = """<root>
    <items>apple</items>
    <items>banana</items>
    <items>cherry</items>
    <numbers>1</numbers>
    <numbers>2</numbers>
    <numbers>3</numbers>
</root>"""
        assert result == expected

    def test_none_values_omitted(self):
        """Test that None values are omitted from XML."""
        data = {"name": "test", "optional": None, "value": "123", "another_none": None}
        result = dict_to_xml(data, "root")

        expected = """<root>
    <name>test</name>
    <value>123</value>
</root>"""
        assert result == expected

    def test_empty_dict(self):
        """Test empty dictionary conversion."""
        data = {}
        result = dict_to_xml(data, "root")

        expected = "<root>\n</root>"
        assert result == expected

    def test_mixed_nested_with_none(self):
        """Test nested structure with None values mixed in."""
        data = {
            "user": {
                "name": "John",
                "email": None,
                "settings": {"theme": "dark", "notifications": None},
            },
            "metadata": None,
        }
        result = dict_to_xml(data, "root")

        expected = """<root>
    <user>
        <name>John</name>
        <settings>
            <theme>dark</theme>
        </settings>
    </user>
</root>"""
        assert result == expected

    def test_special_characters_escaped(self):
        """Test that special XML characters are properly escaped."""
        data = {
            "text": "This has <tags> & \"quotes\" and 'apostrophes'",
            "code": "if x < 5 && y > 10:",
        }
        result = dict_to_xml(data, "root")

        expected = """<root>
    <text>This has &lt;tags&gt; &amp; "quotes" and 'apostrophes'</text>
    <code>if x &lt; 5 &amp;&amp; y &gt; 10:</code>
</root>"""
        assert result == expected

    def test_numeric_and_boolean_strings(self):
        """Test handling of various string types."""
        data = {"count": "42", "enabled": "true", "rate": "3.14", "name": "test"}
        result = dict_to_xml(data, "root")

        expected = """<root>
    <count>42</count>
    <enabled>true</enabled>
    <rate>3.14</rate>
    <name>test</name>
</root>"""
        assert result == expected

    def test_empty_string_values(self):
        """Test handling of empty string values."""
        data = {"name": "test", "empty": "", "value": "123"}
        result = dict_to_xml(data, "root")

        expected = """<root>
    <name>test</name>
    <empty />
    <value>123</value>
</root>"""
        assert result == expected

    def test_default_root_tag(self):
        """Test using default root tag."""
        data = {"key": "value"}
        result = dict_to_xml(data)  # No root_tag specified

        expected = """<root>
    <key>value</key>
</root>"""
        assert result == expected


class TestXmlToDict:
    def test_simple_xml_parsing(self):
        """Test basic XML to dictionary conversion."""
        xml = """<root>
    <name>test</name>
    <value>123</value>
</root>"""
        result = xml_to_dict(xml)
        expected = {"name": "test", "value": "123"}
        assert result == expected

    def test_nested_xml_parsing(self):
        """Test nested XML parsing."""
        xml = """<root>
    <user>
        <name>John</name>
        <details>
            <age>30</age>
            <city>NYC</city>
        </details>
    </user>
</root>"""
        result = xml_to_dict(xml)
        expected = {"user": {"name": "John", "details": {"age": "30", "city": "NYC"}}}
        assert result == expected

    def test_list_elements_parsing(self):
        """Test parsing XML with repeated elements (lists)."""
        xml = """<root>
    <items>apple</items>
    <items>banana</items>
    <items>cherry</items>
    <count>3</count>
</root>"""
        result = xml_to_dict(xml)
        expected = {"items": ["apple", "banana", "cherry"], "count": "3"}
        assert result == expected

    def test_empty_elements(self):
        """Test parsing empty XML elements."""
        xml = """<root>
    <name>test</name>
    <empty />
    <value>123</value>
</root>"""
        result = xml_to_dict(xml)
        expected = {"name": "test", "empty": "", "value": "123"}
        assert result == expected

    def test_special_characters_unescaped(self):
        """Test that XML entities are properly unescaped."""
        xml = """<root>
    <text>This has &lt;tags&gt; &amp; &quot;quotes&quot; and &apos;apostrophes&apos;</text>
</root>"""
        result = xml_to_dict(xml)
        expected = {"text": "This has <tags> & \"quotes\" and 'apostrophes'"}
        assert result == expected


class TestRoundTripConversion:
    def test_simple_round_trip(self):
        """Test that dict -> XML -> dict is lossless for simple data."""
        original = {"name": "test", "value": "123", "flag": "true"}
        xml = dict_to_xml(original, "root")
        result = xml_to_dict(xml)
        assert result == original

    def test_nested_round_trip(self):
        """Test round trip with nested data."""
        original = {
            "user": {"name": "John", "settings": {"theme": "dark", "count": "5"}},
            "active": "true",
        }
        xml = dict_to_xml(original, "root")
        result = xml_to_dict(xml)
        assert result == original

    def test_round_trip_with_lists(self):
        """Test round trip with list data."""
        original = {"items": ["apple", "banana", "cherry"], "metadata": {"count": "3"}}
        xml = dict_to_xml(original, "root")
        result = xml_to_dict(xml)
        assert result == original

    def test_round_trip_omits_none(self):
        """Test that None values are omitted and don't round trip."""
        original_with_none = {"name": "test", "optional": None, "value": "123"}
        expected_without_none = {"name": "test", "value": "123"}

        xml = dict_to_xml(original_with_none, "root")
        result = xml_to_dict(xml)
        assert result == expected_without_none

    def test_round_trip_special_characters(self):
        """Test round trip with special characters."""
        original = {"text": 'This has <tags> & "quotes"', "code": "if x < 5:"}
        xml = dict_to_xml(original, "root")
        result = xml_to_dict(xml)
        assert result == original


class TestWriteXmlFile:
    def test_write_simple_xml_file(self):
        """Test writing a simple dictionary to XML file."""
        data = {"name": "test", "value": "123"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.xml"
            write_xml_file(data, file_path, "metadata")

            assert file_path.exists()
            content = file_path.read_text()
            expected = """<metadata>
    <name>test</name>
    <value>123</value>
</metadata>"""
            assert content == expected

    def test_write_creates_parent_directories(self):
        """Test that writing XML file creates parent directories."""
        data = {"test": "value"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "sub" / "directory" / "test.xml"
            write_xml_file(data, file_path, "metadata")

            assert file_path.exists()
            assert file_path.parent.exists()
            content = file_path.read_text()
            expected = """<metadata>
    <test>value</test>
</metadata>"""
            assert content == expected

    def test_write_default_root_tag(self):
        """Test writing with default root tag."""
        data = {"key": "value"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.xml"
            write_xml_file(data, file_path)  # No root_tag specified

            content = file_path.read_text()
            expected = """<metadata>
    <key>value</key>
</metadata>"""
            assert content == expected


class TestReadXmlFile:
    def test_read_xml_file(self):
        """Test reading an XML file."""
        data = {"name": "test", "value": "123"}
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.xml"
            write_xml_file(data, file_path, "metadata")
            result = read_xml_file(file_path)
            assert result == data
