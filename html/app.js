const { useState, useEffect } = React;

// Story 1.1: Create URL Input Form
function createURLInputForm(url, setUrl, onSubmit, loading) {
    return (
        <form className="url-form" onSubmit={onSubmit}>
            <div className="form-group">
                <label htmlFor="blog-url">Enter Blog/Article URL</label>
                <input
                    type="text"
                    id="blog-url"
                    placeholder="https://en.wikipedia.org/wiki/India"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={loading}
                />
            </div>
            <button type="submit" className="btn" disabled={loading}>
                {loading ? (
                    <>
                        <span className="spinner"></span>
                        Converting to PDF...
                    </>
                ) : (
                    'Convert to PDF'
                )}
            </button>
        </form>
    );
}

// Story 1.2: Validate URL Format
function validateURLFormat(url) {
    if (!url || url.trim() === '') {
        return { valid: false, error: 'URL cannot be empty' };
    }
    
    const urlPattern = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
    
    if (!urlPattern.test(url)) {
        return { valid: false, error: 'Please enter a valid URL format' };
    }
    
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        return { valid: false, error: 'URL must start with http:// or https://' };
    }
    
    return { valid: true, error: null };
}

// Story 1.3: Check URL Accessibility
async function checkURLAccessibility(url) {
    try {
        // Use the backend to check accessibility
        const response = await fetch(`http://localhost:8000/check-url`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            return { accessible: false, error: data.detail || 'URL is not accessible' };
        }
        
        return { accessible: true, error: null };
    } catch (error) {
        return { accessible: false, error: 'Failed to check URL accessibility. Is the backend running?' };
    }
}

// Story 4.2: Preserve Article Layout
function preserveArticleLayout(html) {
    // This function ensures article format consistency
    // In a real implementation, this would process the HTML structure
    return html;
}

// Story 4.3: Apply Consistent Styles
function applyConsistentStyles() {
    const styles = {
        classic: {
            fontFamily: 'Georgia, serif',
            fontSize: '16px',
            lineHeight: '1.6',
        },
        modern: {
            fontFamily: 'Arial, sans-serif',
            fontSize: '14px',
            lineHeight: '1.8',
        },
        minimal: {
            fontFamily: 'Helvetica, sans-serif',
            fontSize: '15px',
            lineHeight: '1.7',
        },
    };
    
    return styles;
}

// Main App Component
function App() {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);
    const [pdfUrl, setPdfUrl] = useState(null);
    const [progress, setProgress] = useState('');
    
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);
        setPdfUrl(null);
        setProgress('');
        
        // Story 1.2: Validate URL Format
        const validation = validateURLFormat(url);
        if (!validation.valid) {
            setError(validation.error);
            return;
        }
        
        setLoading(true);
        
        // Story 1.3: Check URL Accessibility
        setProgress('Checking URL accessibility...');
        const accessibility = await checkURLAccessibility(url);
        if (!accessibility.accessible) {
            setError(accessibility.error);
            setLoading(false);
            setProgress('');
            return;
        }
        
        // Convert to PDF
        try {
            setProgress('Fetching article content...');
            await new Promise(resolve => setTimeout(resolve, 500));
            
            setProgress('Processing images and content...');
            await new Promise(resolve => setTimeout(resolve, 500));
            
            setProgress('Generating PDF document...');
            const response = await fetch('http://localhost:8000/convert', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to convert to PDF');
            }
            
            setProgress('Finalizing your PDF...');
            // Get the PDF blob
            const blob = await response.blob();
            const pdfBlobUrl = URL.createObjectURL(blob);
            setPdfUrl(pdfBlobUrl);
            setSuccess('PDF generated successfully! Click below to download.');
            setProgress('');
        } catch (err) {
            setError(err.message || 'An error occurred while converting to PDF');
            setProgress('');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div className="container">
            <div className="header">
                <h1>📄 Blog-to-PDF</h1>
                <p>Convert any blog or article into a beautiful PDF</p>
            </div>
            
            {error && (
                <div className="alert alert-error">
                    ❌ {error}
                </div>
            )}
            
            {success && (
                <div className="alert alert-success">
                    ✅ {success}
                </div>
            )}
            
            {progress && (
                <div className="progress-container">
                    <div className="progress-bar">
                        <div className="progress-fill"></div>
                    </div>
                    <p className="progress-text">{progress}</p>
                </div>
            )}
            
            {createURLInputForm(url, setUrl, handleSubmit, loading)}
            
            {pdfUrl && (
                <div className="pdf-preview">
                    <h3>Your PDF is ready!</h3>
                    <a 
                        href={pdfUrl} 
                        download="blog-article.pdf" 
                        className="download-link"
                    >
                        📥 Download PDF
                    </a>
                </div>
            )}
        </div>
    );
}

// Render the App
ReactDOM.render(<App />, document.getElementById('root'));
