// AI Supplier Evaluation System - Frontend Application
class SupplierAnalyzer {
  constructor() {
    this.initializeElements();
    this.initializeEventListeners();
    this.performanceChart = null;
    this.isAnalyzing = false;
  }

  initializeElements() {
    // Form elements
    this.form = document.getElementById('scrape-form');
    this.runBtn = document.getElementById('run-btn');
    this.btnText = document.getElementById('btn-text');
    this.loadingSpinner = document.getElementById('loading-spinner');
    this.statusText = document.getElementById('status-text');
    this.progressContainer = document.getElementById('progress-container');
    this.progressBar = document.getElementById('progress-bar');

    // Result sections
    this.statsSection = document.getElementById('stats-section');
    this.resultsSection = document.getElementById('results-section');
    this.rankingsSection = document.getElementById('rankings-section');
    this.rawSection = document.getElementById('raw-section');

    // Content elements
    this.insightsEl = document.getElementById('insights');
    this.productsTable = document.getElementById('products').querySelector('tbody');
    this.rawPre = document.getElementById('raw-pre');
  }

  initializeEventListeners() {
    this.form.addEventListener('submit', (e) => this.handleAnalysis(e));
    
    // Add input validation
    document.getElementById('query').addEventListener('input', this.validateForm.bind(this));
    document.getElementById('scrapfly_key').addEventListener('input', this.validateForm.bind(this));
  }

  validateForm() {
    const query = document.getElementById('query').value.trim();
    const apiKey = document.getElementById('scrapfly_key').value.trim();
    const isValid = query.length > 0 && apiKey.length > 0;
    
    this.runBtn.disabled = !isValid || this.isAnalyzing;
    return isValid;
  }

  setStatus(message, type = 'info') {
    this.statusText.textContent = message;
    
    // Update status indicator color
    const statusDot = document.querySelector('.status-dot');
    statusDot.style.background = type === 'error' ? 'var(--danger)' : 
                                 type === 'success' ? 'var(--success)' : 
                                 type === 'processing' ? 'var(--accent)' : 'var(--success)';
  }

  updateProgress(percent) {
    this.progressBar.style.width = `${percent}%`;
  }

  async handleAnalysis(e) {
    e.preventDefault();
    
    if (!this.validateForm()) return;

    this.isAnalyzing = true;
    this.startLoadingAnimation();
    this.hideResultSections();

    const requestData = this.gatherFormData();

    try {
      // Simulate progress steps
      this.simulateProgress();
      
      const response = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Analysis failed: ${errorText}`);
      }

      const data = await response.json();
      
      if (!data.ok) {
        throw new Error(data.message || 'Analysis request failed');
      }

      await this.renderResults(data);
      this.setStatus('Analysis Complete', 'success');
      
    } catch (error) {
      console.error('Analysis error:', error);
      this.setStatus(`Error: ${error.message}`, 'error');
      this.showErrorMessage(error.message);
    } finally {
      this.stopLoadingAnimation();
      this.isAnalyzing = false;
    }
  }

  gatherFormData() {
    return {
      query: document.getElementById('query').value.trim(),
      max_suppliers: Number(document.getElementById('max_suppliers').value || 5),
      max_products_per_seller: Number(document.getElementById('max_products_per_seller').value || 3),
      limit: Number(document.getElementById('limit').value || 20),
      country: document.getElementById('country').value.trim() || 'AU',
      scrapfly_key: document.getElementById('scrapfly_key').value.trim(),
    };
  }

  startLoadingAnimation() {
    this.runBtn.disabled = true;
    this.btnText.textContent = 'Analyzing...';
    this.loadingSpinner.classList.remove('hidden');
    this.progressContainer.classList.remove('hidden');
    this.setStatus('Initializing AI Analysis...', 'processing');
  }

  stopLoadingAnimation() {
    this.runBtn.disabled = false;
    this.btnText.textContent = 'Analyze Suppliers';
    this.loadingSpinner.classList.add('hidden');
    this.progressContainer.classList.add('hidden');
    this.updateProgress(0);
  }

  simulateProgress() {
    const steps = [
      { percent: 20, message: 'Scraping supplier data...' },
      { percent: 40, message: 'Processing with AI...' },
      { percent: 60, message: 'Analyzing ratings and reviews...' },
      { percent: 80, message: 'Generating insights...' },
      { percent: 100, message: 'Finalizing results...' }
    ];

    let currentStep = 0;
    const progressInterval = setInterval(() => {
      if (currentStep < steps.length) {
        const step = steps[currentStep];
        this.updateProgress(step.percent);
        this.setStatus(step.message, 'processing');
        currentStep++;
      } else {
        clearInterval(progressInterval);
      }
    }, 800);
  }

  hideResultSections() {
    [this.statsSection, this.resultsSection, this.rankingsSection, this.rawSection]
      .forEach(section => section?.classList.add('hidden'));
  }

  async renderResults(data) {
    const { cleaned, raw } = data;
    
    // Add delay for smooth transition
    await new Promise(resolve => setTimeout(resolve, 300));
    
    this.renderStatistics(cleaned, raw);
    this.renderInsights(cleaned.insights || []);
    this.renderProductRankings(cleaned.top_products || []);
    this.renderPerformanceChart(cleaned.top_products || []);
    this.renderRawData(raw);
    
    // Show sections with animation
    this.showResultSections();
  }

  renderStatistics(cleaned, raw) {
    const stats = this.calculateStatistics(cleaned, raw);
    
    this.statsSection.innerHTML = stats.map(stat => `
      <div class="stat-card fade-in">
        <div class="stat-value">${stat.value}</div>
        <div class="stat-label">${stat.label}</div>
      </div>
    `).join('');
    
    this.statsSection.classList.remove('hidden');
  }

  calculateStatistics(cleaned, raw) {
    const suppliers = raw.suppliers || [];
    const products = cleaned.top_products || [];
    const marketAnalysis = cleaned.market_analysis || {};
    
    const avgRating = marketAnalysis.avg_rating || 
      (products.length > 0 ? (products.reduce((sum, p) => sum + (p.rating || 0), 0) / products.length).toFixed(1) : '0');
    
    const totalOrders = products.reduce((sum, p) => sum + (p.num_orders || 0), 0);
    const avgAiScore = products.length > 0 ? 
      Math.round(products.reduce((sum, p) => sum + (p.ai_score || this.calculateAIScore(p)), 0) / products.length) : 0;
    
    return [
      { value: suppliers.length, label: 'Suppliers Found' },
      { value: products.length, label: 'Products Analyzed' },
      { value: avgRating, label: 'Average Rating' },
      { value: this.formatNumber(totalOrders), label: 'Total Orders' },
      { value: `${avgAiScore}%`, label: 'Avg AI Score' },
      { value: `${marketAnalysis.high_quality_ratio || 0}%`, label: 'High Quality %' }
    ];
  }

  renderInsights(insights) {
    // Handle both simple insights array and enhanced AI response structure
    const mainInsights = Array.isArray(insights) ? insights : insights.insights || [];
    const recommendations = insights.recommendations || [];
    const riskFactors = insights.risk_factors || [];
    
    let insightsHTML = '';
    
    // Main insights
    if (mainInsights.length > 0) {
      insightsHTML += mainInsights.map((insight, index) => `
        <li style="animation-delay: ${index * 0.1}s" class="fade-in">
          <div class="insight-icon">
            <i class="fas fa-lightbulb"></i>
          </div>
          <div>${insight}</div>
        </li>
      `).join('');
    }
    
    // Recommendations
    if (recommendations.length > 0) {
      insightsHTML += `
        <li style="animation-delay: ${mainInsights.length * 0.1}s" class="fade-in">
          <div class="insight-icon" style="background: linear-gradient(45deg, var(--success), #059669);">
            <i class="fas fa-thumbs-up"></i>
          </div>
          <div>
            <strong>AI Recommendations:</strong>
            <ul style="margin-top: 0.5rem; padding-left: 1rem;">
              ${recommendations.slice(0, 3).map(rec => `<li>${rec}</li>`).join('')}
            </ul>
          </div>
        </li>
      `;
    }
    
    // Risk factors (show only 2 most important)
    if (riskFactors.length > 0) {
      insightsHTML += `
        <li style="animation-delay: ${(mainInsights.length + 1) * 0.1}s" class="fade-in">
          <div class="insight-icon" style="background: linear-gradient(45deg, var(--warning), #d97706);">
            <i class="fas fa-exclamation-triangle"></i>
          </div>
          <div>
            <strong>Risk Considerations:</strong>
            <ul style="margin-top: 0.5rem; padding-left: 1rem;">
              ${riskFactors.slice(0, 2).map(risk => `<li>${risk}</li>`).join('')}
            </ul>
          </div>
        </li>
      `;
    }
    
    this.insightsEl.innerHTML = insightsHTML;
  }

  renderProductRankings(products) {
    // Debug: Check if URLs are present in the data
    console.log('Product data received:', products.slice(0, 2));
    
    this.productsTable.innerHTML = products.map((product, index) => {
      // Use AI score from backend if available, otherwise calculate locally
      const aiScore = product.ai_score || this.calculateAIScore(product);
      const rating = product.rating || 0;
      
      // Ensure we have a valid URL, fallback to a placeholder or disable link
      const productUrl = product.product_url || '#';
      const hasValidUrl = product.product_url && product.product_url.startsWith('http');
      
      // Debug: Log URL issues
      if (!hasValidUrl && index < 3) {
        console.warn(`Product ${index + 1} missing valid URL:`, product.product_url);
      }
      
      return `
        <tr class="fade-in" style="animation-delay: ${index * 0.05}s">
          <td>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="font-weight: 600; color: var(--accent);">#${index + 1}</span>
              ${index < 3 ? `<i class="fas fa-crown" style="color: var(--accent);"></i>` : ''}
            </div>
          </td>
          <td>
            ${hasValidUrl ? 
              `<a href="${productUrl}" target="_blank" rel="noopener">
                ${this.truncateText(product.product_title || 'Unknown Product', 50)}
              </a>` :
              `<span title="URL not available">
                ${this.truncateText(product.product_title || 'Unknown Product', 50)}
              </span>`
            }
          </td>
          <td>
            <div style="font-weight: 500;">${product.seller_name || 'Unknown'}</div>
          </td>
          <td>
            <div style="font-weight: 600; color: var(--success);">
              ${product.price || 'N/A'}
            </div>
          </td>
          <td>
            <div class="rating">
              ${this.renderStars(rating)}
              <span class="rating-text">(${rating})</span>
            </div>
          </td>
          <td>
            <div style="font-weight: 500;">
              ${this.formatNumber(product.num_orders || 0)}
            </div>
          </td>
          <td>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <div style="background: linear-gradient(90deg, var(--danger), var(--accent), var(--success)); height: 4px; width: 40px; border-radius: 2px; position: relative;">
                <div style="position: absolute; left: 0; width: ${aiScore}%; height: 100%; background: white; border-radius: 2px;"></div>
              </div>
              <span style="font-weight: 600; color: var(--primary);">${aiScore}%</span>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  calculateAIScore(product) {
    // Simple AI scoring algorithm based on rating, orders, and price
    const rating = product.rating || 0;
    const orders = product.num_orders || 0;
    const hasPrice = product.price && product.price !== 'N/A';
    
    let score = 0;
    score += (rating / 5) * 40; // Rating contributes 40%
    score += Math.min((orders / 1000), 1) * 30; // Orders contribute 30%
    score += hasPrice ? 20 : 0; // Price availability contributes 20%
    score += Math.random() * 10; // Random factor for AI "insight" 10%
    
    return Math.round(Math.min(score, 100));
  }

  renderStars(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    return [
      ...Array(fullStars).fill('<i class="fas fa-star star"></i>'),
      ...(hasHalfStar ? ['<i class="fas fa-star-half-alt star"></i>'] : []),
      ...Array(emptyStars).fill('<i class="far fa-star star"></i>')
    ].join('');
  }

  renderPerformanceChart(products) {
    const ctx = document.getElementById('performance-chart');
    if (!ctx) return;

    // Destroy existing chart
    if (this.performanceChart) {
      this.performanceChart.destroy();
    }

    const data = products.slice(0, 8).map(p => ({
      label: this.truncateText(p.product_title || 'Unknown', 20),
      rating: p.rating || 0,
      orders: Math.log10((p.num_orders || 0) + 1), // Log scale for orders
      aiScore: (p.ai_score || this.calculateAIScore(p)) / 20 // Scale to 0-5 for chart
    }));

    this.performanceChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: data.map(d => d.label),
        datasets: [
          {
            label: 'Rating',
            data: data.map(d => d.rating),
            borderColor: 'rgb(99, 102, 241)',
            backgroundColor: 'rgba(99, 102, 241, 0.2)',
            borderWidth: 2
          },
          {
            label: 'Order Volume (log)',
            data: data.map(d => d.orders),
            borderColor: 'rgb(20, 184, 166)',
            backgroundColor: 'rgba(20, 184, 166, 0.2)',
            borderWidth: 2
          },
          {
            label: 'AI Score',
            data: data.map(d => d.aiScore / 20), // Scale to 0-5 for chart
            borderColor: 'rgb(245, 158, 11)',
            backgroundColor: 'rgba(245, 158, 11, 0.2)',
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: 'rgb(248, 250, 252)'
            }
          }
        },
        scales: {
          r: {
            angleLines: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            pointLabels: {
              color: 'rgb(203, 213, 225)',
              font: {
                size: 10
              }
            },
            ticks: {
              color: 'rgb(148, 163, 184)',
              backdropColor: 'transparent'
            }
          }
        }
      }
    });
  }

  renderRawData(raw) {
    this.rawPre.textContent = JSON.stringify(raw, null, 2);
  }

  showResultSections() {
    setTimeout(() => this.resultsSection.classList.remove('hidden'), 100);
    setTimeout(() => this.rankingsSection.classList.remove('hidden'), 200);
    setTimeout(() => this.rawSection.classList.remove('hidden'), 300);
  }

  showErrorMessage(message) {
    // Create error notification
    const errorDiv = document.createElement('div');
    errorDiv.className = 'glass-card fade-in';
    errorDiv.style.cssText = `
      background: rgba(239, 68, 68, 0.1);
      border-color: var(--danger);
      margin-top: 2rem;
    `;
    errorDiv.innerHTML = `
      <div class="card-header">
        <div class="card-icon" style="background: var(--danger);">
          <i class="fas fa-exclamation-triangle"></i>
        </div>
        <div>
          <h3 class="card-title">Analysis Failed</h3>
          <p class="card-subtitle">${message}</p>
        </div>
      </div>
    `;
    
    // Insert after the form
    this.form.parentNode.insertBefore(errorDiv, this.form.nextSibling);
    
    // Remove after 10 seconds
    setTimeout(() => errorDiv.remove(), 10000);
  }

  truncateText(text, maxLength) {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  }

  formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  }
}

// Toggle raw data visibility
function toggleRawData() {
  const content = document.getElementById('raw-content');
  const icon = document.getElementById('raw-toggle-icon');
  
  if (content.classList.contains('hidden')) {
    content.classList.remove('hidden');
    content.classList.add('fade-in');
    icon.classList.remove('fa-chevron-down');
    icon.classList.add('fa-chevron-up');
  } else {
    content.classList.add('hidden');
    icon.classList.remove('fa-chevron-up');
    icon.classList.add('fa-chevron-down');
  }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
  new SupplierAnalyzer();
  
  // Add some nice touches
  console.log(`
    🧠 AI Supplier Evaluation System
    🚀 Built with modern web technologies
    🔬 Powered by Gemini AI & Scrapfly
    
    System Status: Ready for Analysis
  `);
});
