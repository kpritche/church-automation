"""Tests for cover_generator module."""
import pytest
from datetime import date
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io

from bulletins_app.cover_generator import (
    CoverWeekInfo,
    scrape_week_info,
    download_bulletin_image,
)


@pytest.fixture
def mock_lectionary_html():
    """Mock HTML from the lectionary index page."""
    return """
    <html>
        <body>
            <h2>April 2026</h2>
            <div class="entry">
                APRIL 12, 2026 SECOND SUNDAY OF EASTER, YEAR A
                <a href="https://www.umcdiscipleship.org/worship-planning/stories-that-matter/week-1-second-sunday-of-easter-year-a">
                    Week 1 – Second Sunday of Easter, Year A
                </a>
            </div>
            <div class="entry">
                APRIL 19, 2026 THIRD SUNDAY OF EASTER, YEAR A
                <a href="https://www.umcdiscipleship.org/worship-planning/stories-that-matter/week-2-third-sunday-of-easter-year-a">
                    Week 2 – Third Sunday of Easter, Year A
                </a>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_graphics_page_html():
    """Mock HTML from a graphics page with bulletin download link."""
    return """
    <html>
        <body>
            <h1>Graphics Download - Week 1 – Second Sunday of Easter</h1>
            <div>
                BULLETIN – SECOND SUNDAY OF EASTER (WEEK 1)
                <a href="https://s3.us-east-1.amazonaws.com/gbod-assets/graphics/Week1_StoriesMatter_Worship_Series_Bulletin.jpg">Download</a>
            </div>
            <div>
                POWERPOINT (DARK) – SECOND SUNDAY OF EASTER (WEEK 1)
                <a href="https://s3.us-east-1.amazonaws.com/gbod-assets/graphics/Week1_StoriesMatter_Worship_Series_PPT-Dark.jpg">Download</a>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_old_series_lectionary_html():
    """Mock HTML for an older series with -lectionary-planning-notes suffix."""
    return """
    <html>
        <body>
            <h2>March 2026</h2>
            <div class="entry">
                MARCH 22, 2026 FIFTH SUNDAY IN LENT, YEAR A
                <a href="https://www.umcdiscipleship.org/worship-planning/renewed-in-mercy/fifth-sunday-in-lent-year-a-lectionary-planning-notes">
                    Fifth Sunday in Lent, Year A - Lectionary Planning Notes
                </a>
            </div>
        </body>
    </html>
    """


def test_lectionary_page_finds_matching_date(mock_lectionary_html):
    """Test that scrape_week_info finds the correct entry for a given date."""
    with patch('bulletins_app.cover_generator.requests.get') as mock_get:
        # Mock lectionary page response
        mock_lectionary_response = Mock()
        mock_lectionary_response.text = mock_lectionary_html
        mock_lectionary_response.raise_for_status = Mock()
        
        # Mock graphics page response
        mock_graphics_response = Mock()
        mock_graphics_response.text = """
            <html><body>
                BULLETIN<a href="https://s3.example.com/bulletin.jpg">Download</a>
            </body></html>
        """
        mock_graphics_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_lectionary_response, mock_graphics_response]
        
        result = scrape_week_info(date(2026, 4, 12))
        
        assert result.liturgical_name == "SECOND SUNDAY OF EASTER, YEAR A"
        assert "bulletin.jpg" in result.image_url


def test_graphics_url_clean_slug(mock_lectionary_html, mock_graphics_page_html):
    """Test graphics URL derivation for clean week slugs."""
    with patch('bulletins_app.cover_generator.requests.get') as mock_get:
        mock_lectionary_response = Mock()
        mock_lectionary_response.text = mock_lectionary_html
        mock_lectionary_response.raise_for_status = Mock()
        
        mock_graphics_response = Mock()
        mock_graphics_response.text = mock_graphics_page_html
        mock_graphics_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_lectionary_response, mock_graphics_response]
        
        result = scrape_week_info(date(2026, 4, 12))
        
        # Verify the graphics URL was correctly derived
        expected_graphics_url = "https://www.umcdiscipleship.org/worship-planning/stories-that-matter/week-1-second-sunday-of-easter-year-a-graphics"
        assert mock_get.call_args_list[1][0][0] == expected_graphics_url


def test_graphics_url_strips_planning_notes_suffix(mock_old_series_lectionary_html):
    """Test that -lectionary-planning-notes suffix is stripped before adding -graphics."""
    with patch('bulletins_app.cover_generator.requests.get') as mock_get:
        mock_lectionary_response = Mock()
        mock_lectionary_response.text = mock_old_series_lectionary_html
        mock_lectionary_response.raise_for_status = Mock()
        
        mock_graphics_response = Mock()
        mock_graphics_response.text = """
            <html><body>
                BULLETIN<a href="https://s3.example.com/bulletin.jpg">Download</a>
            </body></html>
        """
        mock_graphics_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_lectionary_response, mock_graphics_response]
        
        result = scrape_week_info(date(2026, 3, 22))
        
        # Verify the graphics URL has -graphics appended, not -lectionary-planning-notes-graphics
        expected_graphics_url = "https://www.umcdiscipleship.org/worship-planning/renewed-in-mercy/fifth-sunday-in-lent-year-a-graphics"
        assert mock_get.call_args_list[1][0][0] == expected_graphics_url


def test_graphics_page_extracts_bulletin_image_url(mock_lectionary_html, mock_graphics_page_html):
    """Test that bulletin image URL is correctly extracted from graphics page."""
    with patch('bulletins_app.cover_generator.requests.get') as mock_get:
        mock_lectionary_response = Mock()
        mock_lectionary_response.text = mock_lectionary_html
        mock_lectionary_response.raise_for_status = Mock()
        
        mock_graphics_response = Mock()
        mock_graphics_response.text = mock_graphics_page_html
        mock_graphics_response.raise_for_status = Mock()
        
        mock_get.side_effect = [mock_lectionary_response, mock_graphics_response]
        
        result = scrape_week_info(date(2026, 4, 12))
        
        assert result.image_url == "https://s3.us-east-1.amazonaws.com/gbod-assets/graphics/Week1_StoriesMatter_Worship_Series_Bulletin.jpg"


def test_no_matching_date_raises_value_error():
    """Test that ValueError is raised when no entry matches the service date."""
    with patch('bulletins_app.cover_generator.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.text = """
            <html><body>
                <h2>April 2026</h2>
                <div>APRIL 12, 2026 SECOND SUNDAY OF EASTER, YEAR A</div>
            </body></html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="No lectionary entry found"):
            scrape_week_info(date(2026, 12, 25))  # Date not in mock data


def test_download_bulletin_image_returns_pil_image():
    """Test that download_bulletin_image returns a valid PIL Image."""
    # Create a simple test image
    test_img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    test_img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    with patch('bulletins_app.cover_generator.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = download_bulletin_image("https://example.com/image.jpg")
        
        assert isinstance(result, Image.Image)
        assert result.size == (100, 100)
