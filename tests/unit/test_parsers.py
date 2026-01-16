"""Unit tests for parser modules - FIXED to match actual ParserFactory."""

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

        assert isinstance(result, str)
        assert "test document" in result.lower()
        assert unprocessed_images == 0

    def test_parse_md_file(self, tmp_path):
        """Test parsing a markdown file."""
        content = "# Header\n\nThis is markdown content."
        file_path = create_temp_file(tmp_path, "test.md", content)

        parser = TextParser()
        result, unprocessed_images = parser.parse(
            file_path, {"file_name": "test.md"}
        )

        assert isinstance(result, str)
        assert "Header" in result
        assert unprocessed_images == 0

    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist."""
        parser = TextParser()
        with pytest.raises((FileNotFoundError, OSError)):
            parser.parse(Path("nonexistent.txt"), {"file_name": "nonexistent.txt"})

    def test_parse_with_utf8_encoding(self, tmp_path):
        """Test parsing UTF-8 encoded file."""
        content = "Test with émojis: 🎉 and spëcial çharacters"
        file_path = create_temp_file(tmp_path, "test_utf8.txt", content)

        parser = TextParser()
        result, _ = parser.parse(file_path, {"file_name": "test_utf8.txt"})

        assert "émojis" in result or "emojis" in result  # May be normalized
        assert isinstance(result, str)


class TestDocxParser:
    """Tests for DocxParser."""

    def test_initialization(self):
        """Test DocxParser initialization."""
        config = create_sample_config()
        mock_llm = Mock()
        parser = DocxParser(config, mock_llm)
        assert parser.config == config

    def test_supports_docx_files(self):
        """Test that DocxParser supports .docx files."""
        parser = DocxParser()
        assert parser.supports_file_type(".docx")
        assert parser.supports_file_type(".DOCX")

    def test_does_not_support_other_files(self):
        """Test that DocxParser doesn't support other file types."""
        parser = DocxParser()
        assert not parser.supports_file_type(".txt")
        assert not parser.supports_file_type(".pdf")
        assert not parser.supports_file_type(".xlsx")


class TestExcelParser:
    """Tests for ExcelParser."""

    def test_initialization(self):
        """Test ExcelParser initialization."""
        config = create_sample_config()
        parser = ExcelParser(config)
        assert parser.config == config


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
    """Tests for ParserFactory - FIXED to use actual get_parser method."""

    def test_get_parser_text_for_txt(self):
        """Test getting TextParser for .txt files."""
        config = create_sample_config()
        parser = ParserFactory.get_parser(
            file_type="txt",
            parser_type="text",
            config=config
        )
        assert isinstance(parser, TextParser)

    def test_get_parser_text_for_md(self):
        """Test getting TextParser for .md files."""
        config = create_sample_config()
        parser = ParserFactory.get_parser(
            file_type="md",
            parser_type="text",
            config=config
        )
        assert isinstance(parser, TextParser)

    def test_get_parser_docx(self):
        """Test getting DocxParser for .docx files."""
        config = create_sample_config()
        mock_llm = Mock()
        parser = ParserFactory.get_parser(
            file_type="docx",
            parser_type="docx",
            llm=mock_llm,
            config=config
        )
        assert isinstance(parser, DocxParser)

    def test_get_parser_excel(self):
        """Test getting ExcelParser for .xlsx files."""
        config = create_sample_config()
        parser = ParserFactory.get_parser(
            file_type="xlsx",
            parser_type="excel",
            config=config
        )
        assert isinstance(parser, ExcelParser)

    def test_get_parser_case_insensitive(self):
        """Test that factory handles case-insensitive file types."""
        config = create_sample_config()
        
        parser1 = ParserFactory.get_parser(
            file_type="TXT",
            parser_type="text",
            config=config
        )
        assert isinstance(parser1, TextParser)

        mock_llm = Mock()
        parser2 = ParserFactory.get_parser(
            file_type="DOCX",
            parser_type="docx",
            llm=mock_llm,
            config=config
        )
        assert isinstance(parser2, DocxParser)

    def test_get_parser_unsupported_file_type(self):
        """Test that factory raises error for unsupported file types."""
        config = create_sample_config()
        with pytest.raises(ValueError, match="Unsupported file type"):
            ParserFactory.get_parser(
                file_type="unknown",
                parser_type="unknown",
                config=config
            )

    def test_get_parser_unsupported_parser_type(self):
        """Test that factory raises error for unsupported parser type."""
        config = create_sample_config()
        with pytest.raises(ValueError, match="not supported for file type"):
            ParserFactory.get_parser(
                file_type="txt",
                parser_type="invalid_parser",
                config=config
            )

    def test_get_parser_strips_leading_dot(self):
        """Test that factory handles extensions with leading dot."""
        config = create_sample_config()
        
        parser = ParserFactory.get_parser(
            file_type=".txt",  # With dot
            parser_type="text",
            config=config
        )
        assert isinstance(parser, TextParser)

    def test_get_supported_file_types(self):
        """Test getting list of supported file types."""
        file_types = ParserFactory.get_supported_file_types()
        
        assert isinstance(file_types, list)
        assert "txt" in file_types
        assert "md" in file_types
        assert "docx" in file_types
        assert "xlsx" in file_types
        assert "pdf" in file_types

    def test_get_supported_parsers_for_txt(self):
        """Test getting supported parsers for txt files."""
        parsers = ParserFactory.get_supported_parsers_for_file_type("txt")
        
        assert isinstance(parsers, list)
        assert "text" in parsers

    def test_get_supported_parsers_for_pdf(self):
        """Test getting supported parsers for PDF files."""
        parsers = ParserFactory.get_supported_parsers_for_file_type("pdf")
        
        assert isinstance(parsers, list)
        assert "document_intelligence" in parsers
        assert "vision" in parsers

    def test_get_supported_parsers_for_unknown_type(self):
        """Test getting parsers for unknown file type returns empty list."""
        parsers = ParserFactory.get_supported_parsers_for_file_type("unknown")
        
        assert isinstance(parsers, list)
        assert len(parsers) == 0

    def test_register_new_parser(self):
        """Test registering a new parser type."""
        # Create a mock parser class
        class MockParser:
            pass
        
        # Register it
        ParserFactory.register_parser("test", "mock", MockParser)
        
        # Verify it was registered
        parsers = ParserFactory.get_supported_parsers_for_file_type("test")
        assert "mock" in parsers


class TestParserIntegration:
    """Integration tests for parsers."""

    def test_all_parsers_implement_interface(self):
        """Test that all parsers implement the Parser interface."""
        from ETL.document_processor.base.interfaces import Parser
        
        config = create_sample_config()
        mock_llm = Mock()
        
        # Test each parser
        parsers = [
            TextParser(config),
            DocxParser(config, mock_llm),
            ExcelParser(config),
        ]
        
        for parser in parsers:
            assert isinstance(parser, Parser)
            assert hasattr(parser, 'parse')
            assert hasattr(parser, 'supports_file_type')

    def test_factory_creates_correct_instances(self):
        """Test that factory creates the correct parser instances."""
        config = create_sample_config()
        mock_llm = Mock()
        
        # Test mappings
        test_cases = [
            ("txt", "text", TextParser),
            ("md", "text", TextParser),
            ("xlsx", "excel", ExcelParser),
        ]
        
        for file_type, parser_type, expected_class in test_cases:
            parser = ParserFactory.get_parser(
                file_type=file_type,
                parser_type=parser_type,
                llm=mock_llm if file_type == "docx" else None,
                config=config
            )
            assert isinstance(parser, expected_class), \
                f"Expected {expected_class.__name__} for {file_type}, got {type(parser).__name__}"
