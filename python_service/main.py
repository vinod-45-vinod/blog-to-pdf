from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from xhtml2pdf import pisa
import re
import hashlib
import time
from typing import Optional
from urllib.parse import urljoin, urlparse
import io
import base64

app = FastAPI(title="Blog-to-PDF Converter API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: str

class URLCheckRequest(BaseModel):
    url: str

# Story 2.1: Fetch HTML
def fetch_html(url: str) -> str:
    """
    Fetches the HTML content from a given URL.
    
    Args:
        url: The URL to fetch HTML from
        
    Returns:
        str: The HTML content as a string
        
    Raises:
        HTTPException: If the URL cannot be fetched
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

# Story 2.2: Parse Article Text and Headings
def parse_article_text_and_headings(html: str) -> BeautifulSoup:
    """
    Extracts readable content including text and headings from HTML.
    
    Args:
        html: The HTML content as a string
        
    Returns:
        BeautifulSoup: Parsed HTML with article content
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try to find the main article content
    article = (
        soup.find('article') or 
        soup.find('main') or 
        soup.find('div', class_=re.compile(r'(post|article|content|entry)', re.I)) or
        soup.find('div', id=re.compile(r'(post|article|content|entry)', re.I))
    )
    
    if article:
        return BeautifulSoup(str(article), 'html.parser')
    
    return soup

# Story 2.3: Preserve Inline Images
def preserve_inline_images(soup: BeautifulSoup, base_url: str) -> BeautifulSoup:
    """
    Ensures images appear in the PDF by converting them to base64 data URIs.
    
    Args:
        soup: BeautifulSoup object containing the HTML
        base_url: The base URL for resolving relative image paths
        
    Returns:
        BeautifulSoup: Modified soup with base64-encoded images
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for img in soup.find_all('img'):
        try:
            # Get the image source URL
            src = img.get('src') or img.get('data-src')
            if not src:
                img.decompose()  # Remove image if no source
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(base_url, src)
            
            # Fetch the image
            try:
                img_response = requests.get(absolute_url, headers=headers, timeout=5)
                img_response.raise_for_status()
                
                # Determine image type from content-type or URL
                content_type = img_response.headers.get('content-type', 'image/jpeg')
                if 'image' not in content_type:
                    # Guess from URL extension
                    if absolute_url.endswith('.png'):
                        content_type = 'image/png'
                    elif absolute_url.endswith('.gif'):
                        content_type = 'image/gif'
                    elif absolute_url.endswith('.webp'):
                        content_type = 'image/webp'
                    else:
                        content_type = 'image/jpeg'
                
                # Convert to base64
                img_base64 = base64.b64encode(img_response.content).decode('utf-8')
                img['src'] = f"data:{content_type};base64,{img_base64}"
                
                # Remove lazy loading attributes
                if img.get('loading'):
                    del img['loading']
                if img.get('data-src'):
                    del img['data-src']
                if img.get('srcset'):
                    del img['srcset']
                    
            except Exception as e:
                # If image fetch fails, remove the image
                print(f"Failed to fetch image {absolute_url}: {str(e)}")
                img.decompose()
                
        except Exception as e:
            # If any error, remove the image
            print(f"Error processing image: {str(e)}")
            img.decompose()
    
    return soup

# Story 3.1: Remove Ads and Banners
def remove_ads_and_banners(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Removes advertisement-related elements from the HTML.
    
    Args:
        soup: BeautifulSoup object containing the HTML
        
    Returns:
        BeautifulSoup: Cleaned soup without ads
    """
    # Common ad-related class/id patterns
    ad_patterns = [
        'ad', 'ads', 'advert', 'advertisement', 'banner', 'sponsor',
        'promo', 'promotion', 'marketing', 'adsense', 'google-ad'
    ]
    
    for pattern in ad_patterns:
        # Remove by class
        for element in soup.find_all(class_=re.compile(pattern, re.I)):
            element.decompose()
        # Remove by id
        for element in soup.find_all(id=re.compile(pattern, re.I)):
            element.decompose()
    
    # Remove script and style tags
    for script in soup.find_all(['script', 'style']):
        script.decompose()
    
    return soup

# Story 3.2: Exclude Sidebars and Comments
def exclude_sidebars_and_comments(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Removes sidebars, navigation, and comment sections from HTML.
    
    Args:
        soup: BeautifulSoup object containing the HTML
        
    Returns:
        BeautifulSoup: Cleaned soup without sidebars and comments
    """
    # Common sidebar/comment patterns
    unwanted_patterns = [
        'sidebar', 'side-bar', 'navigation', 'nav', 'menu',
        'comment', 'comments', 'discussion', 'social', 'share',
        'footer', 'header', 'breadcrumb', 'widget', 'related'
    ]
    
    for pattern in unwanted_patterns:
        # Remove by class
        for element in soup.find_all(class_=re.compile(pattern, re.I)):
            element.decompose()
        # Remove by id
        for element in soup.find_all(id=re.compile(pattern, re.I)):
            element.decompose()
        # Remove by tag name
        for element in soup.find_all(pattern):
            element.decompose()
    
    return soup

# Story 4.1: Integrate PDF Library
def integrate_pdf_library(clean_html: str) -> bytes:
    """
    Converts cleaned HTML to PDF using xhtml2pdf.
    
    Args:
        clean_html: The cleaned HTML content as a string
        
    Returns:
        bytes: The PDF content as bytes
    """
    # Parse the HTML to extract headings and create TOC
    soup = BeautifulSoup(clean_html, 'html.parser')
    
    # Extract the main title (first h1 or h2)
    main_title = None
    first_h1 = soup.find('h1')
    if first_h1:
        main_title = first_h1.get_text().strip()
    else:
        first_h2 = soup.find('h2')
        if first_h2:
            main_title = first_h2.get_text().strip()
    
    print(f"Article title: {main_title}")
    
    # Remove reference sections (commonly found at the end of articles)
    reference_patterns = ['reference', 'citation', 'bibliography', 'notes', 'external-link', 'see-also', 'footer']
    for pattern in reference_patterns:
        for element in soup.find_all(['div', 'section', 'ol', 'ul'], class_=re.compile(pattern, re.I)):
            element.decompose()
        for element in soup.find_all(['div', 'section'], id=re.compile(pattern, re.I)):
            element.decompose()
    
    # Also remove any heading that matches reference patterns and everything after it
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        heading_text = heading.get_text().strip().lower()
        if any(pattern in heading_text for pattern in ['reference', 'citation', 'see also', 'external link', 'note', 'bibliography', 'further reading']):
            # Remove this heading and all following siblings
            next_sibling = heading.find_next_sibling()
            heading.decompose()
            while next_sibling:
                temp = next_sibling.find_next_sibling()
                next_sibling.decompose()
                next_sibling = temp
    
    # Add title at the top if found
    title_html = ""
    if main_title:
        title_html = f'<h2 class="article-title">{main_title}</h2><hr class="title-separator"/>'
    
    # Modern style theme
    modern_style = """
        @page { size: A4; margin: 2cm; }
        body { font-family: Arial, sans-serif; font-size: 14px; line-height: 1.8; color: #2c3e50; }
        h1, h2, h3 { color: #34495e; margin-top: 1.2em; margin-bottom: 0.6em; font-weight: 600; }
        h1 { font-size: 2.2em; border-bottom: 3px solid #3498db; padding-bottom: 0.3em; }
        h2 { font-size: 1.7em; border-bottom: 1px solid #bdc3c7; padding-bottom: 0.2em; }
        h3 { font-size: 1.3em; }
        p { margin-bottom: 1em; text-align: justify; }
        img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
        a { color: #3498db; text-decoration: none; font-weight: 500; }
        code { background: #ecf0f1; padding: 3px 6px; border-radius: 4px; font-family: 'Courier New', monospace; }
        
        .article-title {
            font-size: 32px;
            color: #2c3e50;
            margin-bottom: 10px;
            margin-top: 0;
            border: none;
            font-weight: bold;
            text-align: center;
        }
        .title-separator {
            border: none;
            border-top: 3px solid #3498db;
            margin: 20px 0 30px 0;
        }
        
        table { 
            border-collapse: collapse; 
            width: 100%; 
            margin: 1em 0; 
        }
        th, td { 
            border: 1px solid #bdc3c7; 
            padding: 8px; 
            text-align: left; 
        }
        th { 
            background: #ecf0f1; 
            font-weight: 600; 
        }
    """
    
    # Create full HTML document
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>{modern_style}</style>
    </head>
    <body>
        {title_html}
        {str(soup)}
    </body>
    </html>
    """
    
    # Generate PDF using xhtml2pdf
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        src=full_html,
        dest=pdf_buffer,
        encoding='utf-8'
    )
    
    if pisa_status.err:
        raise Exception(f"Error creating PDF: {pisa_status.err}")
    
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    
    return pdf_bytes

# Story 5.1: Generate Secure Download Link
def generate_secure_download_link(pdf_path: str) -> dict:
    """
    Creates a secure, expiring URL/token for PDF downloads.
    
    Args:
        pdf_path: Path or identifier for the PDF
        
    Returns:
        dict: Contains token and expiration time
    """
    # Generate a unique token
    timestamp = str(time.time())
    token = hashlib.sha256(f"{pdf_path}{timestamp}".encode()).hexdigest()
    
    # Set expiration (e.g., 1 hour from now)
    expiration = int(time.time()) + 3600
    
    return {
        "token": token,
        "expiration": expiration,
        "expires_in": "1 hour"
    }

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Blog-to-PDF Converter API is running", "version": "1.0.0"}

@app.post("/check-url")
async def check_url(request: URLCheckRequest):
    """
    Check if a URL is accessible before conversion.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.head(request.url, headers=headers, timeout=5, allow_redirects=True)
        
        if response.status_code == 405:  # HEAD not allowed, try GET
            response = requests.get(request.url, headers=headers, timeout=5, stream=True)
        
        response.raise_for_status()
        return {"accessible": True, "status_code": response.status_code}
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"URL is not accessible: {str(e)}")

@app.post("/convert")
async def convert_to_pdf(request: URLRequest):
    """
    Main endpoint to convert a blog URL to PDF.
    
    Pipeline:
    1. Fetch HTML
    2. Parse article content
    3. Remove ads and banners
    4. Exclude sidebars and comments
    5. Preserve images
    6. Generate PDF
    7. Return PDF file
    """
    try:
        # Step 1: Fetch HTML (Story 2.1)
        html_content = fetch_html(request.url)
        
        # Step 2: Parse article content (Story 2.2)
        soup = parse_article_text_and_headings(html_content)
        
        # Step 3: Remove ads and banners (Story 3.1)
        soup = remove_ads_and_banners(soup)
        
        # Step 4: Exclude sidebars and comments (Story 3.2)
        soup = exclude_sidebars_and_comments(soup)
        
        # Step 5: Preserve inline images (Story 2.3)
        soup = preserve_inline_images(soup, request.url)
        
        # Get cleaned HTML
        clean_html = str(soup)
        
        # Step 6: Generate PDF (Story 4.1)
        try:
            pdf_bytes = integrate_pdf_library(clean_html)
        except Exception as pdf_error:
            print(f"PDF Generation Error: {pdf_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(pdf_error)}")
        
        # Step 7: Generate secure download info (Story 5.1)
        download_info = generate_secure_download_link(request.url)
        
        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=blog-article.pdf",
                "X-Download-Token": download_info["token"],
                "X-Expires-In": download_info["expires_in"]
            }
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"General Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error converting to PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
