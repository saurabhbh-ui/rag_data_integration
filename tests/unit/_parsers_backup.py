"""Unit tests for parser modules."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from ETL.document_processor.parsers.text_parser import TextParser
from ETL.document_processor.parsers.docx_parser import DocxParser
from ETL.document_processor.parsers.excel_parser import ExcelParser
from ETL.document_processor.parsers.factory import ParserFactory
from ETL.document_processor.base.models import ProcessingConfig, ParserType
from tests.fixtures import create_sample_config, create_temp_file, SAMPLE_TEXT_MEDIUM


class TestTextParser:
    """Tests for TextParser."""

    def test_initialization(self):
        """Test TextParser initialization."""
        config = create_sample_config()
        parser = TextParser(config)
        assert parser.config == config

    def test_supports_txt_files(self):
        """Test that TextParser supports .txt files."""
        parser = TextParser()
        assert parser.supports_file_type(".txt")
        assert parser.supports_file_type(".TXT")
        assert parser.supports_file_type(".text")

    def test_supports_md_files(self):
        """Test that TextParser supports .md files."""
        parser = TextParser()
        assert parser.supports_file_type(".md")
        assert parser.supports_file_type(".MD")

    def test_does_not_support_other_files(self):
        """Test that TextParser doesn't support other file types."""
        parser = TextParser()
        assert not parser.supports_file_type(".pdf")
        assert not parser.supports_file_type(".docx")
        assert not parser.supports_file_type(".xlsx")

    def test_parse_txt_file(self, tmp_path):
        """Test parsing a text file."""
        # Create a temp text file
        content = "This is a test document.\nWith multiple lines."
        file_path = create_temp_file(tmp_path, "test.txt", content)

        parser = TextParser()
        result, unprocessed_images = parser.parse(
            file_path, {"file_name": "test.txt"}
        )

        assert result == content
        assert unprocessed_images == 0

    def test_parse_md_file(self, tmp_path):
        """Test parsing a markdown file."""
        file_path = create_temp_file(tmp_path, "test.md", SAMPLE_TEXT_MEDIUM)

        parser = TextParser()
        result, unprocessed_images = parser.parse(
            file_path, {"file_name": "test.md"}
        )

        assert "# Main Title" in result
        assert "## Section 1" in result
        assert unprocessed_images == 0

    def test_parse_utf8_file(self, tmp_path):
        """Test parsing file with UTF-8 encoding."""
        content = "Test with special chars: é, ñ, ü, 中文"
        file_path = create_temp_file(tmp_path, "test.txt", content)

        parser = TextParser()
        result, _ = parser.parse(file_path, {})

        assert result == content

    def test_parse_nonexistent_file(self):
        """Test that parsing nonexistent file raises error."""
        parser = TextParser()
        with pytest.raises(Exception):
            parser.parse(Path("nonexistent.txt"), {})

    def test_parse_empty_file(self, tmp_path):
        """Test parsing an empty file."""
        file_path = create_temp_file(tmp_path, "empty.txt", "")

        parser = TextParser()
        result, _ = parser.parse(file_path, {})

        assert result == ""


class TestDocxParser:
    """Tests for DocxParser."""

    def test_initialization(self):
        """Test DocxParser initialization."""
        config = create_sample_config()
        parser = DocxParser(config)
        assert parser.config == config

    def test_supports_docx_files(self):
        """Test that DocxParser supports .docx files."""
        parser = DocxParser()
        assert parser.supports_file_type(".docx")
        assert parser.supports_file_type(".DOCX")
        assert parser.supports_file_type(".doc")

    def test_does_not_support_other_files(self):
        """Test that DocxParser doesn't support other file types."""
        parser = DocxParser()
        assert not parser.supports_file_type(".txt")
        assert not parser.supports_file_type(".pdf")
        assert not parser.supports_file_type(".xlsx")

    @patch("ETL.document_processor.parsers.docx_parser.Document")
    def test_parse_docx_file(self, mock_document):
        """Test parsing a DOCX file with mock."""
        # Mock the Document object
        mock_doc = MagicMock()
        mock_para1 = MagicMock()
        mock_para1.text = "First paragraph"
        mock_para2 = MagicMock()
        mock_para2.text = "Second paragraph"
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_document.return_value = mock_doc

        parser = DocxParser()
        result, unprocessed_images = parser.parse(
            Path("test.docx"), {"file_name": "test.docx"}
        )

        # Verify content (exact format may vary based on implementation)
        assert "First paragraph" in result or "First paragraph".lower() in result.lower()
        assert unprocessed_images == 0


class TestExcelParser:
    """Tests for ExcelParser."""

    def test_initialization(self):
        """Test ExcelParser initialization."""
        config = create_sample_config()
        parser = ExcelParser(config)
        assert parser.config == config

    def test_supports_excel_files(self):
        """Test that ExcelParser supports Excel files."""
        parser = ExcelParser()
        assert parser.supports_file_type(".xlsx")
        assert parser.supports_file_type(".XLSX")
        assert parser.supports_file_type(".xls")
        assert parser.supports_file_type(".xlsm")

    def test_does_not_support_other_files(self):
        """Test that ExcelParser doesn't support other file types."""
        parser = ExcelParser()
        assert not parser.supports_file_type(".txt")
        assert not parser.supports_file_type(".pdf")
        assert not parser.supports_file_type(".docx")

    @patch("ETL.document_processor.parsers.excel_parser.pd.read_excel")
    def test_parse_excel_file(self, mock_read_excel):
        """Test parsing an Excel file with mock."""
        # Mock pandas DataFrame
        import pandas as pd
        mock_df = pd.DataFrame({
            "Column1": ["A", "B", "C"],
            "Column2": [1, 2, 3]
        })
        mock_read_excel.return_value = mock_df

        parser = ExcelParser()
        result, unprocessed_images = parser.parse(
            Path("test.xlsx"), {"file_name": "test.xlsx"}
        )

        # Verify result contains data
        assert isinstance(result, str)
        assert len(result) > 0
        assert unprocessed_images == 0


class TestParserFactory:
    """Tests for ParserFactory."""

    def test_create_text_parser_for_txt(self):
        """Test creating TextParser for .txt files."""
        config = create_sample_config()
        parser = ParserFactory.create_parser(".txt", config)
        assert isinstance(parser, TextParser)

    def test_create_text_parser_for_md(self):
        """Test creating TextParser for .md files."""
        config = create_sample_config()
        parser = ParserFactory.create_parser(".md", config)
        assert isinstance(parser, TextParser)

    def test_create_docx_parser(self):
        """Test creating DocxParser for .docx files."""
        config = create_sample_config()
        parser = ParserFactory.create_parser(".docx", config)
        assert isinstance(parser, DocxParser)

    def test_create_excel_parser(self):
        """Test creating ExcelParser for .xlsx files."""
        config = create_sample_config()
        parser = ParserFactory.create_parser(".xlsx", config)
        assert isinstance(parser, ExcelParser)

    def test_create_parser_case_insensitive(self):
        """Test that factory handles case-insensitive extensions."""
        config = create_sample_config()
        
        parser1 = ParserFactory.create_parser(".TXT", config)
        assert isinstance(parser1, TextParser)

        parser2 = ParserFactory.create_parser(".DOCX", config)
        assert isinstance(parser2, DocxParser)

    def test_create_parser_unsupported_extension(self):
        """Test that factory raises error for unsupported extensions."""
        config = create_sample_config()
        with pytest.raises(ValueError, match="Unsupported file type"):
            ParserFactory.create_parser(".unknown", config)

    def test_factory_creates_new_instances(self):
        """Test that factory creates new instances each time."""
        config = create_sample_config()
        parser1 = ParserFactory.create_parser(".txt", config)
        parser2 = ParserFactory.create_parser(".txt", config)
        assert parser1 is not parser2

    def test_get_parser_for_pdf_document_intelligence(self):
        """Test getting document intelligence parser for PDF."""
        config = create_sample_config(parser_type=ParserType.DOCUMENT_INTELLIGENCE)
        # This test would need actual DocumentIntelligenceParser
        # We can't fully test without Azure credentials
        # Just verify it doesn't crash
        try:
            parser = ParserFactory.create_parser(".pdf", config, None)
            # If we get here, parser was created
            assert parser is not None
        except (ImportError, AttributeError):
            # Expected if DocumentIntelligenceParser isn't available
            pytest.skip("DocumentIntelligenceParser not available")


class TestParserIntegration:
    """Integration tests for parsers."""

    def test_all_text_based_parsers_work(self, tmp_path):
        """Test that all text-based parsers can process content."""
        # Test with TextParser
        txt_file = create_temp_file(tmp_path, "test.txt", "Sample text content")
        parser = TextParser()
        result, _ = parser.parse(txt_file, {})
        assert result == "Sample text content"

        # Test with markdown
        md_file = create_temp_file(tmp_path, "test.md", "# Markdown\n\nContent here")
        parser = TextParser()
        result, _ = parser.parse(md_file, {})
        assert "# Markdown" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
