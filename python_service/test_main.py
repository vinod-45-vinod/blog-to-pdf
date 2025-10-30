import pytest
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
from unittest.mock import patch, Mock
import requests

from main import (
    app,
    fetch_html,
    parse_article_text_and_headings,
    preserve_inline_images,
    remove_ads_and_banners,
    exclude_sidebars_and_comments,
    integrate_pdf_library,
    generate_secure_download_link
)

client = TestClient(app)

# Test URL - Wikipedia India
TEST_URL = "https://en.wikipedia.org/wiki/India"


class TestFetchHTML:
    """Tests for Story 2.1: Fetch HTML"""
    
    @patch('main.requests.get')
    def test_fetch_html_success(self, mock_get):
        """Test successful HTML fetch from Wikipedia India"""
        mock_response = Mock()
        mock_response.text = "<html><body><h1>India</h1><p>India is a country...</p></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_html(TEST_URL)
        assert "India" in result
        mock_get.assert_called_once()
    
    @patch('main.requests.get')
    def test_fetch_html_failure(self, mock_get):
        """Test HTML fetch failure"""
        mock_get.side_effect = requests.RequestException("Connection error")
        
        with pytest.raises(Exception) as exc_info:
            fetch_html("https://invalid-url.com")
        assert "Failed to fetch URL" in str(exc_info.value.detail)


class TestParseArticleTextAndHeadings:
    """Tests for Story 2.2: Parse Article Text and Headings"""
    
    def test_parse_with_article_tag(self):
        """Test parsing when article tag exists"""
        html = "<html><body><article><h1>India</h1><p>Content about India</p></article></body></html>"
        result = parse_article_text_and_headings(html)
        assert result.find('h1') is not None
        assert result.find('p') is not None
    
    def test_parse_with_main_tag(self):
        """Test parsing when main tag exists"""
        html = "<html><body><main><h1>Title</h1><p>Content</p></main></body></html>"
        result = parse_article_text_and_headings(html)
        assert result.find('h1') is not None
    
    def test_parse_with_content_class(self):
        """Test parsing when content class exists"""
        html = '<html><body><div class="content"><h1>Title</h1><p>Content</p></div></body></html>'
        result = parse_article_text_and_headings(html)
        assert result.find('h1') is not None
    
    def test_parse_fallback_to_full_html(self):
        """Test parsing falls back to full HTML when no article container found"""
        html = "<html><body><div><p>Content</p></div></body></html>"
        result = parse_article_text_and_headings(html)
        assert result is not None


class TestPreserveInlineImages:
    """Tests for Story 2.3: Preserve Inline Images"""
    
    @patch('main.requests.get')
    def test_preserve_images_converts_relative_urls(self, mock_get):
        """Test that relative image URLs are converted to base64 or removed"""
        # Mock failed image fetch - image will be removed
        mock_get.side_effect = requests.RequestException("Failed")
        
        html = '<img src="/images/india-flag.jpg">'
        soup = BeautifulSoup(html, 'html.parser')
        result = preserve_inline_images(soup, TEST_URL)
        
        # Image should be removed if fetch fails
        img = result.find('img')
        assert img is None
    
    @patch('main.requests.get')
    def test_preserve_images_keeps_absolute_urls(self, mock_get):
        """Test that absolute URLs are converted to base64"""
        # Mock successful image fetch
        mock_response = Mock()
        mock_response.content = b'fake_image_data'
        mock_response.headers = {'content-type': 'image/jpeg'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        html = '<img src="https://upload.wikimedia.org/wikipedia/commons/india.jpg">'
        soup = BeautifulSoup(html, 'html.parser')
        result = preserve_inline_images(soup, TEST_URL)
        
        img = result.find('img')
        assert img is not None
        assert 'data:image' in img['src']
    
    @patch('main.requests.get')
    def test_preserve_images_handles_data_src(self, mock_get):
        """Test that lazy-loaded images (data-src) are handled"""
        # Mock failed fetch
        mock_get.side_effect = requests.RequestException("Failed")
        
        html = '<img data-src="/lazy-image.jpg">'
        soup = BeautifulSoup(html, 'html.parser')
        result = preserve_inline_images(soup, TEST_URL)
        
        # Image should be removed if no valid src
        img = result.find('img')
        assert img is None


class TestRemoveAdsAndBanners:
    """Tests for Story 3.1: Remove Ads and Banners"""
    
    def test_remove_ad_class(self):
        """Test removal of elements with ad-related classes"""
        html = '<div class="ad-banner">Ad</div><p>Content about India</p>'
        soup = BeautifulSoup(html, 'html.parser')
        result = remove_ads_and_banners(soup)
        
        assert result.find('div', class_='ad-banner') is None
        assert result.find('p') is not None
    
    def test_remove_ad_id(self):
        """Test removal of elements with ad-related IDs"""
        html = '<div id="google-ad">Ad</div><p>Content</p>'
        soup = BeautifulSoup(html, 'html.parser')
        result = remove_ads_and_banners(soup)
        
        assert result.find('div', id='google-ad') is None
        assert result.find('p') is not None
    
    def test_remove_scripts_and_styles(self):
        """Test removal of script and style tags"""
        html = '<script>alert("ad")</script><style>.ad{}</style><p>Content</p>'
        soup = BeautifulSoup(html, 'html.parser')
        result = remove_ads_and_banners(soup)
        
        assert result.find('script') is None
        assert result.find('style') is None
        assert result.find('p') is not None


class TestExcludeSidebarsAndComments:
    """Tests for Story 3.2: Exclude Sidebars and Comments"""
    
    def test_exclude_sidebar_class(self):
        """Test removal of sidebar elements"""
        html = '<div class="sidebar">Sidebar</div><p>India content</p>'
        soup = BeautifulSoup(html, 'html.parser')
        result = exclude_sidebars_and_comments(soup)
        
        assert result.find('div', class_='sidebar') is None
        assert result.find('p') is not None
    
    def test_exclude_comments_section(self):
        """Test removal of comments section"""
        html = '<div class="comments">Comments</div><p>Content</p>'
        soup = BeautifulSoup(html, 'html.parser')
        result = exclude_sidebars_and_comments(soup)
        
        assert result.find('div', class_='comments') is None
        assert result.find('p') is not None
    
    def test_exclude_navigation(self):
        """Test removal of navigation elements"""
        html = '<nav>Menu</nav><p>Content</p>'
        soup = BeautifulSoup(html, 'html.parser')
        result = exclude_sidebars_and_comments(soup)
        
        assert result.find('nav') is None
        assert result.find('p') is not None


class TestIntegratePDFLibrary:
    """Tests for Story 4.1: Integrate PDF Library"""
    
    def test_integrate_pdf_library_returns_bytes(self):
        """Test that PDF generation returns bytes"""
        html = "<h1>India</h1><p>India is a country in South Asia.</p>"
        result = integrate_pdf_library(html)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        # PDF files start with %PDF
        assert result[:4] == b'%PDF'
    
    def test_integrate_pdf_library_classic_style(self):
        """Test PDF generation (classic style removed, using modern only)"""
        html = "<h1>India</h1>"
        result = integrate_pdf_library(html)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_integrate_pdf_library_minimal_style(self):
        """Test PDF generation (minimal style removed, using modern only)"""
        html = "<h1>India</h1>"
        result = integrate_pdf_library(html)
        
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestGenerateSecureDownloadLink:
    """Tests for Story 5.1: Generate Secure Download Link"""
    
    def test_generate_secure_download_link_returns_token(self):
        """Test that secure link generation returns a token"""
        result = generate_secure_download_link(TEST_URL)
        
        assert "token" in result
        assert "expiration" in result
        assert "expires_in" in result
    
    def test_generate_secure_download_link_unique_tokens(self):
        """Test that each call generates unique tokens"""
        result1 = generate_secure_download_link(TEST_URL)
        result2 = generate_secure_download_link("https://en.wikipedia.org/wiki/Python")
        
        assert result1["token"] != result2["token"]
    
    def test_generate_secure_download_link_has_expiration(self):
        """Test that token has future expiration time"""
        import time
        result = generate_secure_download_link(TEST_URL)
        
        assert result["expiration"] > int(time.time())
        assert result["expires_in"] == "1 hour"


class TestAPIEndpoints:
    """Tests for API endpoints"""
    
    def test_root_endpoint(self):
        """Test the root health check endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
        assert "version" in response.json()
    
    @patch('main.requests.head')
    def test_check_url_endpoint_success(self, mock_head):
        """Test URL check endpoint with Wikipedia India URL"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_head.return_value = mock_response
        
        response = client.post("/check-url", json={"url": TEST_URL})
        assert response.status_code == 200
        assert response.json()["accessible"] is True
    
    @patch('main.requests.head')
    def test_check_url_endpoint_failure(self, mock_head):
        """Test URL check endpoint with inaccessible URL"""
        mock_head.side_effect = requests.RequestException("Not found")
        
        response = client.post("/check-url", json={"url": "https://invalid.com"})
        assert response.status_code == 400
    
    @patch('main.fetch_html')
    @patch('main.integrate_pdf_library')
    def test_convert_endpoint_success(self, mock_pdf, mock_fetch):
        """Test successful PDF conversion with Wikipedia India"""
        mock_fetch.return_value = "<html><body><article><h1>India</h1></article></body></html>"
        mock_pdf.return_value = b'%PDF-1.4 mock pdf content'
        
        response = client.post("/convert", json={"url": TEST_URL})
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
