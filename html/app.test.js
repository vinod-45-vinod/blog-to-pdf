/**
 * @jest-environment jsdom
 */

// Mock functions from app.js for testing
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

// Story 1.3: Check URL Accessibility (Mock for testing)
async function checkURLAccessibility(url) {
    try {
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

// Tests

describe('Frontend Functions Tests', () => {
    
    // Story 1.2: Validate URL Format Tests
    describe('validateURLFormat', () => {
        test('should return valid for Wikipedia India URL', () => {
            const result = validateURLFormat('https://en.wikipedia.org/wiki/India');
            expect(result.valid).toBe(true);
            expect(result.error).toBeNull();
        });
        
        test('should return valid for correct HTTPS URL', () => {
            const result = validateURLFormat('https://example.com/blog-post');
            expect(result.valid).toBe(true);
            expect(result.error).toBeNull();
        });
        
        test('should return valid for correct HTTP URL', () => {
            const result = validateURLFormat('http://example.com/article');
            expect(result.valid).toBe(true);
            expect(result.error).toBeNull();
        });
        
        test('should return invalid for empty URL', () => {
            const result = validateURLFormat('');
            expect(result.valid).toBe(false);
            expect(result.error).toBe('URL cannot be empty');
        });
        
        test('should return invalid for URL without protocol', () => {
            const result = validateURLFormat('example.com/blog');
            expect(result.valid).toBe(false);
            expect(result.error).toBe('URL must start with http:// or https://');
        });
        
        test('should return invalid for malformed URL', () => {
            const result = validateURLFormat('not-a-url');
            expect(result.valid).toBe(false);
            expect(result.error).toBe('Please enter a valid URL format');
        });
    });
    
    // Story 1.3: Check URL Accessibility Tests
    describe('checkURLAccessibility', () => {
        beforeEach(() => {
            global.fetch = jest.fn();
        });
        
        afterEach(() => {
            jest.resetAllMocks();
        });
        
        test('should return accessible for Wikipedia India URL', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ accessible: true }),
            });
            
            const result = await checkURLAccessibility('https://en.wikipedia.org/wiki/India');
            expect(result.accessible).toBe(true);
            expect(result.error).toBeNull();
        });
        
        test('should return accessible for valid URL', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ accessible: true }),
            });
            
            const result = await checkURLAccessibility('https://example.com');
            expect(result.accessible).toBe(true);
            expect(result.error).toBeNull();
        });
        
        test('should return not accessible for invalid URL', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: false,
                json: async () => ({ detail: 'URL not found' }),
            });
            
            const result = await checkURLAccessibility('https://invalid-url.com');
            expect(result.accessible).toBe(false);
            expect(result.error).toBe('URL not found');
        });
        
        test('should handle fetch errors', async () => {
            global.fetch.mockRejectedValueOnce(new Error('Network error'));
            
            const result = await checkURLAccessibility('https://example.com');
            expect(result.accessible).toBe(false);
            expect(result.error).toContain('Failed to check URL accessibility');
        });
    });
    
    // Story 4.2: Preserve Article Layout Tests
    describe('preserveArticleLayout', () => {
        test('should preserve HTML content', () => {
            const html = '<div><h1>Title</h1><p>Content</p></div>';
            const result = preserveArticleLayout(html);
            expect(result).toBe(html);
        });
        
        test('should handle empty HTML', () => {
            const result = preserveArticleLayout('');
            expect(result).toBe('');
        });
    });
    
    // Story 4.3: Apply Consistent Styles Tests
    describe('applyConsistentStyles', () => {
        test('should return all style themes', () => {
            const styles = applyConsistentStyles();
            expect(styles).toHaveProperty('classic');
            expect(styles).toHaveProperty('modern');
            expect(styles).toHaveProperty('minimal');
        });
        
        test('should have correct classic style properties', () => {
            const styles = applyConsistentStyles();
            expect(styles.classic.fontFamily).toBe('Georgia, serif');
            expect(styles.classic.fontSize).toBe('16px');
            expect(styles.classic.lineHeight).toBe('1.6');
        });
        
        test('should have correct modern style properties', () => {
            const styles = applyConsistentStyles();
            expect(styles.modern.fontFamily).toBe('Arial, sans-serif');
            expect(styles.modern.fontSize).toBe('14px');
            expect(styles.modern.lineHeight).toBe('1.8');
        });
        
        test('should have correct minimal style properties', () => {
            const styles = applyConsistentStyles();
            expect(styles.minimal.fontFamily).toBe('Helvetica, sans-serif');
            expect(styles.minimal.fontSize).toBe('15px');
            expect(styles.minimal.lineHeight).toBe('1.7');
        });
    });
});
