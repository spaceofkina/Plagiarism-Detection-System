import React, { useState, useEffect } from 'react';
import './App.css';

// Use your Render backend URL
const API_BASE_URL = 'https://plagiarism-detection-system-3.onrender.com';

function App() {
  const [activeTab, setActiveTab] = useState('compare');
  const [text1, setText1] = useState('');
  const [text2, setText2] = useState('');
  const [similarityResult, setSimilarityResult] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [checkResults, setCheckResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  
  // New states for summarization
  const [summaryText, setSummaryText] = useState('');
  const [summaryResult, setSummaryResult] = useState(null);
  const [maxLength, setMaxLength] = useState(150);
  const [minLength, setMinLength] = useState(30); // Changed from 50 to 30
  
  // New states for FAQs
  const [faqs, setFaqs] = useState([]);
  const [faqCategories, setFaqCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState('All');
  const [newFAQ, setNewFAQ] = useState({
    question: '',
    answer: '',
    category: 'General'
  });

  // Compare two texts
  const compareTexts = async () => {
    if (!text1.trim() || !text2.trim()) {
      alert('Please enter both texts to compare');
      return;
    }

    setLoading(true);
    try {
      console.log('Sending request to:', `${API_BASE_URL}/api/similarity/compare`);
      
      const response = await fetch(`${API_BASE_URL}/api/similarity/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text1, text2 })
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Response data:', result);
      setSimilarityResult(result);
      
    } catch (error) {
      console.error('Error details:', error);
      alert(`Error comparing texts: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Text summarization function
  const summarizeText = async () => {
    if (!summaryText.trim()) {
      alert('Please enter text to summarize');
      return;
    }

    if (summaryText.length < 20) {
      alert('Text is too short for summarization (minimum 20 characters)');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/summarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          text: summaryText,
          max_length: maxLength,
          min_length: minLength
        })
      });
      
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.detail || `HTTP error! status: ${response.status}`);
      }
      
      setSummaryResult(result);
      
    } catch (error) {
      console.error('Error summarizing text:', error);
      alert(`Error summarizing text: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Load FAQs
  const loadFAQs = async (category = null) => {
    try {
      const url = category && category !== 'All' 
        ? `${API_BASE_URL}/api/faqs?category=${category}`
        : `${API_BASE_URL}/api/faqs`;
      
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setFaqs(data.faqs || []);
        setFaqCategories(data.categories || []);
      }
    } catch (error) {
      console.error('Error loading FAQs:', error);
    }
  };

  // Add new FAQ
  const addFAQ = async () => {
    if (!newFAQ.question.trim() || !newFAQ.answer.trim()) {
      alert('Please enter both question and answer');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/faqs/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newFAQ)
      });
      
      if (response.ok) {
        const result = await response.json();
        alert('FAQ added successfully!');
        setNewFAQ({ question: '', answer: '', category: 'General' });
        loadFAQs(activeCategory);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to add FAQ');
      }
    } catch (error) {
      console.error('Error adding FAQ:', error);
      alert(`Error adding FAQ: ${error.message}`);
    }
  };

  // Upload document
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Only text files for this version
    if (!file.type.includes('text') && !file.name.endsWith('.txt')) {
      alert('Please upload a text file (.txt)');
      return;
    }

    setLoading(true);
    try {
      console.log('Uploading file:', file.name);
      
      // Use FormData instead of JSON
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: 'POST',
        body: formData
      });
      
      console.log('Upload response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.log('Error response:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Upload success:', result);
      
      setUploadMessage(`Document "${result.filename}" uploaded successfully!`);
      loadDocuments();
      event.target.value = ''; // Reset file input
      
    } catch (error) {
      console.error('Upload error details:', error);
      setUploadMessage(`Error uploading document: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Load all documents
  const loadDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/documents`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  // Check document for plagiarism
  const checkDocument = async (documentId) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      setCheckResults(result);
    } catch (error) {
      console.error('Error checking document:', error);
      alert(`Error checking document for plagiarism: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Delete document
  const deleteDocument = async (documentId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setUploadMessage('Document deleted successfully!');
        loadDocuments();
        setCheckResults(null);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      alert(`Error deleting document: ${error.message}`);
    }
  };

  // Load data when tab changes
  useEffect(() => {
    if (activeTab === 'documents') {
      loadDocuments();
    }
    if (activeTab === 'faqs') {
      loadFAQs(activeCategory !== 'All' ? activeCategory : null);
    }
  }, [activeTab, activeCategory]);

  // Sample text for summarization
  const loadSampleText = () => {
    const sampleText = `Sentence-BERT (SBERT) is a modification of the pretrained BERT network that uses siamese and triplet network structures to derive semantically meaningful sentence embeddings that can be compared using cosine-similarity. This reduces the effort for finding the most similar pair from 65 hours with BERT / RoBERTa to about 5 seconds with SBERT, while maintaining the accuracy from BERT.

    We evaluated SBERT and SRoBERTa on common STS tasks and transfer learning tasks, where it outperforms other state-of-the-art sentence embeddings methods. The models are available on HuggingFace for easy use.`;
    
    setSummaryText(sampleText);
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>Enhanced Plagiarism Detection System</h1>
        <p>A Comparative Analysis of Text Similarity Methods for Duplicate Document Detection</p>
        <p className="subtitle">Now with Text Summarization & Research FAQs</p>
      </header>

      <nav className="tab-navigation">
        <button 
          className={activeTab === 'compare' ? 'active' : ''} 
          onClick={() => setActiveTab('compare')}
        >
          Compare Texts
        </button>
        <button 
          className={activeTab === 'documents' ? 'active' : ''} 
          onClick={() => setActiveTab('documents')}
        >
          Document Management
        </button>
        <button 
          className={activeTab === 'summarize' ? 'active' : ''} 
          onClick={() => setActiveTab('summarize')}
        >
          Text Summarization
        </button>
        <button 
          className={activeTab === 'faqs' ? 'active' : ''} 
          onClick={() => setActiveTab('faqs')}
        >
          Research FAQs
        </button>
      </nav>

      <main className="main-content">
        {activeTab === 'compare' && (
          <div className="compare-section">
            <h2>Compare Two Texts</h2>
            <div className="text-inputs">
              <div className="text-area-container">
                <h3>Text 1</h3>
                <textarea
                  value={text1}
                  onChange={(e) => setText1(e.target.value)}
                  placeholder="Enter first text here..."
                  rows="10"
                />
              </div>
              <div className="text-area-container">
                <h3>Text 2</h3>
                <textarea
                  value={text2}
                  onChange={(e) => setText2(e.target.value)}
                  placeholder="Enter second text here..."
                  rows="10"
                />
              </div>
            </div>
            
            <button 
              onClick={compareTexts} 
              disabled={loading}
              className="compare-button"
            >
              {loading ? 'Analyzing...' : 'Compare Texts'}
            </button>

            {similarityResult && (
              <div className={`result-card ${similarityResult.is_plagiarized ? 'plagiarized' : 'original'}`}>
                <h3>Similarity Analysis Result</h3>
                <div className="score-display">
                  <span className="score-label">Similarity Score:</span>
                  <span className="score-value">{(similarityResult.similarity_score * 100).toFixed(2)}%</span>
                </div>
                <div className="verdict">
                  <strong>Verdict:</strong> {similarityResult.message}
                </div>
                <div className="threshold-info">
                  Threshold for plagiarism: {(similarityResult.threshold * 100).toFixed(0)}%
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="documents-section">
            <h2>Document Management</h2>
            
            {uploadMessage && (
              <div className={`message-banner ${uploadMessage.includes('Error') ? 'error' : 'success'}`}>
                {uploadMessage}
              </div>
            )}
            
            <div className="upload-section">
              <h3>Upload Document</h3>
              <input
                type="file"
                onChange={handleFileUpload}
                accept=".txt"
                disabled={loading}
              />
              <p>Supported format: TXT files only</p>
            </div>

            <div className="documents-list">
              <h3>Uploaded Documents ({documents.length})</h3>
              {documents.length === 0 ? (
                <p>No documents uploaded yet.</p>
              ) : (
                <div className="document-cards">
                  {documents.map(doc => (
                    <div key={doc.document_id} className="document-card">
                      <div className="doc-info">
                        <strong>{doc.filename}</strong>
                        <span>Size: {doc.size} characters</span>
                      </div>
                      <div className="doc-actions">
                        <button 
                          onClick={() => checkDocument(doc.document_id)}
                          disabled={loading}
                          className="check-button"
                        >
                          Check Plagiarism
                        </button>
                        <button 
                          onClick={() => deleteDocument(doc.document_id)}
                          className="delete-button"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {checkResults && (
              <div className="check-results">
                <h3>Plagiarism Check Results</h3>
                <div className="summary">
                  <p>Average Similarity: {(checkResults.average_similarity * 100).toFixed(2)}%</p>
                  <p>Potential Plagiarism Cases: {checkResults.plagiarism_count}</p>
                </div>
                
                <div className="similarity-list">
                  {checkResults.results.map(result => (
                    <div 
                      key={result.document_id} 
                      className={`similarity-item ${result.is_plagiarized ? 'high-similarity' : ''}`}
                    >
                      <div className="similarity-doc">
                        <strong>{result.filename}</strong>
                        <span>{(result.similarity_score * 100).toFixed(2)}% similar</span>
                      </div>
                      {result.is_plagiarized && (
                        <span className="plagiarism-warning">⚠️ Potential Plagiarism</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'summarize' && (
          <div className="summarize-section">
            <h2>Text Summarization</h2>
            <p className="feature-description">
              Automatically generate concise summaries of long texts using extractive summarization.
              Perfect for research papers, articles, and lengthy documents.
            </p>
            
            <div className="summarize-controls">
              <div className="length-controls">
                <div className="length-control">
                  <label>Min Length: {minLength}</label>
                  <input
                    type="range"
                    min="20"
                    max="100"
                    value={minLength}
                    onChange={(e) => setMinLength(parseInt(e.target.value))}
                  />
                </div>
                <div className="length-control">
                  <label>Max Length: {maxLength}</label>
                  <input
                    type="range"
                    min="50"
                    max="300"
                    value={maxLength}
                    onChange={(e) => setMaxLength(parseInt(e.target.value))}
                  />
                </div>
              </div>
              
              <button 
                className="sample-button"
                onClick={loadSampleText}
              >
                Load Sample Text
              </button>
            </div>
            
            <div className="text-input-container">
              <h3>Enter Text to Summarize</h3>
              <textarea
                value={summaryText}
                onChange={(e) => setSummaryText(e.target.value)}
                placeholder="Paste your text here (minimum 20 characters)..."
                rows="12"
              />
              <div className="text-stats">
                <span>Characters: {summaryText.length}</span>
                <span>Words: {summaryText.trim().split(/\s+/).filter(w => w.length > 0).length}</span>
              </div>
            </div>
            
            <button 
              onClick={summarizeText} 
              disabled={loading || summaryText.length < 20}
              className="summarize-button"
            >
              {loading ? 'Summarizing...' : 'Generate Summary'}
            </button>

            {summaryResult && (
              <div className="summary-result">
                <h3>Summary Result</h3>
                <div className="summary-stats">
                  <div className="stat">
                    <span className="stat-label">Original Length:</span>
                    <span className="stat-value">{summaryResult.original_length} chars</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Summary Length:</span>
                    <span className="stat-value">{summaryResult.summary_length} chars</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Compression Ratio:</span>
                    <span className="stat-value">{(summaryResult.compression_ratio * 100).toFixed(1)}%</span>
                  </div>
                </div>
                
                <div className="summary-content">
                  <h4>Generated Summary:</h4>
                  <div className="summary-text">
                    {summaryResult.summary}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'faqs' && (
          <div className="faqs-section">
            <h2>Research & System FAQs</h2>
            <p className="feature-description">
              Frequently asked questions about the research methodology, findings, and system features.
            </p>
            
            <div className="faq-filters">
              <button 
                className={`category-filter ${activeCategory === 'All' ? 'active' : ''}`}
                onClick={() => setActiveCategory('All')}
              >
                All FAQs
              </button>
              {faqCategories.map(category => (
                <button
                  key={category}
                  className={`category-filter ${activeCategory === category ? 'active' : ''}`}
                  onClick={() => setActiveCategory(category)}
                >
                  {category}
                </button>
              ))}
            </div>
            
            <div className="faq-list">
              {faqs.length === 0 ? (
                <p>Loading FAQs...</p>
              ) : (
                faqs.map((faq, index) => (
                  <div key={index} className="faq-card">
                    <div className="faq-header">
                      <span className="faq-category">{faq.category}</span>
                      <span className="faq-number">Q{index + 1}</span>
                    </div>
                    <div className="faq-content">
                      <h3 className="faq-question">Q: {faq.question}</h3>
                      <p className="faq-answer"><strong>A:</strong> {faq.answer}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
            
            <div className="add-faq-section">
              <h3>Add New FAQ (Demo)</h3>
              <div className="faq-form">
                <input
                  type="text"
                  placeholder="Enter question..."
                  value={newFAQ.question}
                  onChange={(e) => setNewFAQ({...newFAQ, question: e.target.value})}
                  className="faq-input"
                />
                <textarea
                  placeholder="Enter answer..."
                  value={newFAQ.answer}
                  onChange={(e) => setNewFAQ({...newFAQ, answer: e.target.value})}
                  rows="3"
                  className="faq-textarea"
                />
                <select
                  value={newFAQ.category}
                  onChange={(e) => setNewFAQ({...newFAQ, category: e.target.value})}
                  className="faq-select"
                >
                  <option value="General">General</option>
                  <option value="Research">Research</option>
                  <option value="Data">Data</option>
                  <option value="Results">Results</option>
                  <option value="Technology">Technology</option>
                  <option value="System">System</option>
                  <option value="Features">Features</option>
                </select>
                <button 
                  onClick={addFAQ}
                  className="add-faq-button"
                >
                  Add FAQ
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>Powered by Sentence-BERT & Extractive Summarization | Research: Text Similarity Methods</p>
        <p className="footer-note">Version 2.0 - Lightweight & Reliable</p>
      </footer>
    </div>
  );
}

export default App;