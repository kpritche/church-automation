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
    extract_fill_color,
    wcag_contrast_ratio,
    is_full_bleed,
    generate_branded_cover_pdf,
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


# Phase 2: Color Analysis Tests


def test_full_bleed_detection_portrait():
    """Test that a portrait image matching page proportions is detected as full bleed."""
    # Letter size: 612 x 792 points (aspect ratio ~0.773)
    # Create an image with matching aspect ratio
    img = Image.new('RGB', (612, 792), color='blue')
    
    assert is_full_bleed(img, 612, 792) is True


def test_full_bleed_detection_square():
    """Test that a square image is not detected as full bleed."""
    img = Image.new('RGB', (1000, 1000), color='green')
    
    assert is_full_bleed(img, 612, 792) is False


def test_extract_fill_color_prefers_dark_palette_color():
    """Test that extract_fill_color selects a dark color with good contrast."""
    # Create an image with dark and light colors
    # Use a gradient to ensure multiple colors in palette
    img = Image.new('RGB', (100, 100))
    pixels = img.load()
    
    # Fill with mostly dark blue-green (good contrast with white)
    for x in range(100):
        for y in range(100):
            if y < 80:
                pixels[x, y] = (20, 60, 50)  # Dark teal (similar to church brand)
            else:
                pixels[x, y] = (200, 220, 240)  # Light blue
    
    color = extract_fill_color(img)
    
    # Should return the dark color, not the light one
    assert color[0] < 100 and color[1] < 150 and color[2] < 150
    # Verify it has reasonable contrast
    assert wcag_contrast_ratio(color) >= 4.5


def test_extract_fill_color_falls_back_when_all_colors_light():
    """Test that extract_fill_color falls back to church primary color when no dark colors have good contrast."""
    # Create an image with only very light colors
    img = Image.new('RGB', (100, 100), color=(240, 245, 250))
    
    color = extract_fill_color(img)
    
    # Should fall back to church primary color #16463E (22, 70, 62)
    assert color == (22, 70, 62)


def test_wcag_contrast_ratio_white():
    """Test WCAG contrast ratio calculation for white text on various backgrounds."""
    # Black background should have high contrast (21:1)
    black_contrast = wcag_contrast_ratio((0, 0, 0))
    assert black_contrast >= 21.0
    
    # Dark teal (church brand color) should have good contrast (>4.5:1)
    teal_contrast = wcag_contrast_ratio((22, 70, 62))
    assert teal_contrast >= 4.5
    
    # Light gray should have poor contrast (<3:1)
    light_gray_contrast = wcag_contrast_ratio((200, 200, 200))
    assert light_gray_contrast < 3.0
    
    # White background should have minimal contrast (1:1)
    white_contrast = wcag_contrast_ratio((255, 255, 255))
    assert 0.9 <= white_contrast <= 1.1


# Phase 3: Cover Page Renderer Tests


def test_generate_branded_cover_pdf_produces_valid_pdf():
    """Test that generate_branded_cover_pdf returns valid PDF bytes."""
    # Create a test image
    test_img = Image.new('RGB', (612, 792), color=(50, 100, 150))
    
    pdf_bytes = generate_branded_cover_pdf(
        image=test_img,
        service_name="Celebrate",
        liturgical_name="Second Sunday of Easter, Year A",
        service_date_str="April 12, 2026",
        fill_color=(22, 70, 62)
    )
    
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 100
    assert pdf_bytes[:4] == b'%PDF'


def test_generate_branded_cover_pdf_fullbleed_image():
    """Test cover generation with a full-bleed image."""
    # Create a full-page image (matches letter size aspect ratio)
    test_img = Image.new('RGB', (612, 792), color=(80, 120, 100))
    
    pdf_bytes = generate_branded_cover_pdf(
        image=test_img,
        service_name="First Up",
        liturgical_name="Third Sunday of Easter, Year A",
        service_date_str="April 19, 2026",
        fill_color=(30, 60, 80)
    )
    
    assert pdf_bytes is not None
    assert pdf_bytes[:4] == b'%PDF'


def test_generate_branded_cover_pdf_non_fullbleed_image():
    """Test cover generation with a non-full-bleed square image."""
    # Create a square image (will not fill the page)
    test_img = Image.new('RGB', (800, 800), color=(100, 150, 200))
    
    pdf_bytes = generate_branded_cover_pdf(
        image=test_img,
        service_name="Celebrate",
        liturgical_name="Fourth Sunday of Easter, Year A",
        service_date_str="April 26, 2026",
        fill_color=(40, 80, 70)
    )
    
    assert pdf_bytes is not None
    assert pdf_bytes[:4] == b'%PDF'
