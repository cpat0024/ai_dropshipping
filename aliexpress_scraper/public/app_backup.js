// AI Supplier Evaluation System - Frontend Application
class SupplierAnalyzer {
  constructor() {
    this.initializeElements();
    this.initializeEventListeners();
    this.performanceChart = null;
    this.isAnalyzing = false;
    this.currentProducts = [];
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
  }

  validateForm() {
    const query = document.getElementById('query').value.trim();
    const isValid = query.length > 0;
    
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
      if (error.name === 'AbortError') {
        this.setStatus('Request timed out. Please try again.', 'error');
      } else {
        console.error('Analysis error:', error);
        this.setStatus(`Error: ${error.message}`, 'error');
      }
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
    this.currentProducts = products;
    
    this.productsTable.innerHTML = products.map((product, index) => {
      const aiScore = product.ai_score || this.calculateAIScore(product);
      const rating = product.rating || 0;
      const productUrl = product.product_url || '#';
      const hasValidUrl = product.product_url && product.product_url.startsWith('http');
      
      return `
        <tr>
          <td>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="font-weight: 600; color: var(--accent);">#${index + 1}</span>
              ${index < 3 ? `<i class="fas fa-crown" style="color: var(--accent);"></i>` : ''}
            </div>
          </td>
          <td>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <div>
                ${hasValidUrl ? 
                  `<a href="${productUrl}" target="_blank" rel="noopener">
                    ${this.truncateText(product.product_title || 'Unknown Product', 50)}
                  </a>` :
                  `<span>${this.truncateText(product.product_title || 'Unknown Product', 50)}</span>`
                }
              </div>
              <button class="details-btn" onclick="window.app?.showProductDetails('${productUrl}')" title="View detailed product information">
                <i class="fas fa-info-circle"></i> Details
              </button>
            </div>
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
    this.resultsSection.classList.remove('hidden');
    this.rankingsSection.classList.remove('hidden');
    this.rawSection.classList.remove('hidden');
  }

  exportToCSV() {
    if (!this.currentProducts || this.currentProducts.length === 0) {
      alert('No data to export');
      return;
    }

    const headers = ['Rank', 'Product Title', 'Seller', 'Price', 'Rating', 'Orders', 'AI Score', 'URL'];
    const rows = this.currentProducts.map((product, index) => [
      index + 1,
      `"${(product.product_title || 'Unknown Product').replace(/"/g, '""')}"`,
      `"${(product.seller_name || 'Unknown').replace(/"/g, '""')}"`,
      product.price || 'N/A',
      product.rating || 0,
      product.num_orders || 0,
      Math.round(product.ai_score || this.calculateAIScore(product)),
      product.product_url || ''
    ]);

    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `supplier-analysis-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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

  async showProductDetails(productUrl) {
    console.log('🔍 showProductDetails called with URL:', productUrl);
    
    if (!productUrl || productUrl === '#') {
      alert('Product URL not available');
      return;
    }

    // Show loading
    const loadingMsg = document.createElement('div');
    loadingMsg.id = 'details-loading';
    loadingMsg.innerHTML = `
      <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 9999; display: flex; align-items: center; justify-content: center;">
        <div style="background: var(--bg-secondary); padding: 2rem; border-radius: 12px; text-align: center;">
        <i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i>
          <div>Loading detailed product information...</div>
        </div>
      </div>
    `;
    document.body.appendChild(loadingMsg);

    try {
      console.log('📡 Fetching product details from API...');
      
      const response = await fetch('/api/product-details', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          product_url: productUrl,
          scrapfly_key: 'scp-live-8afea162f0f44a54a71193fb1e19cae6'
        })
      });

      const data = await response.json();
      
      if (!data.ok) {
        throw new Error(data.error || 'Failed to fetch product details');
      }

      this.displayProductDetailsModal(data.details, productUrl);

    } catch (error) {
      console.error('Error fetching product details:', error);
      alert('Failed to load product details: ' + error.message);
    } finally {
      // Remove loading
      const loading = document.getElementById('details-loading');
      if (loading) loading.remove();
    }
  }

  displayProductDetailsModal(details, productUrl) {
    // Create modal
    const modal = document.createElement('div');
    modal.id = 'product-details-modal';
    modal.innerHTML = `
      <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 1rem;">
        <div style="background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 16px; max-width: 900px; max-height: 90vh; width: 100%; overflow-y: auto;">
          <div style="padding: 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
            <h2 style="margin: 0; color: var(--primary);">
              <i class="fas fa-info-circle"></i> Product Details
            </h2>
            <button onclick="this.closest('#product-details-modal').remove()" style="background: none; border: none; color: var(--text-secondary); font-size: 1.5rem; cursor: pointer;">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div style="padding: 1.5rem;">
            ${this.formatProductDetails(details, productUrl)}
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    // Close on background click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }

  formatProductDetails(details, productUrl) {
    if (details.error) {
      return `<div style="color: var(--danger); padding: 2rem; text-align: center;">
        <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
        <div>Error: ${details.error}</div>
      </div>`;
    }

    const basic = details.basic_info || {};
    const ratings = details.ratings || {};
    const seller = details.seller || {};
    const shipping = details.shipping || {};
    const reviews = details.reviews || [];
    const specs = details.specifications || {};
    const images = details.images || [];

    return `
      <div style="display: grid; gap: 1.5rem;">
        <!-- Product Header -->
        <div style="display: flex; gap: 1rem; align-items: flex-start;">
          ${images[0] ? `<img src="${images[0]}" style="width: 150px; height: 150px; object-fit: cover; border-radius: 8px;" onerror="this.style.display='none'">` : ''}
          <div style="flex: 1;">
            <h3 style="margin: 0 0 0.5rem 0; color: var(--text-primary);">${basic.title || 'Unknown Product'}</h3>
            <div style="display: flex; gap: 1rem; margin-bottom: 0.5rem;">
              ${basic.price ? `<span style="font-size: 1.2rem; font-weight: 600; color: var(--success);">${basic.price}</span>` : ''}
              ${basic.original_price ? `<span style="text-decoration: line-through; color: var(--text-muted);">${basic.original_price}</span>` : ''}
            </div>
            <div style="margin-bottom: 0.5rem;">
              ${ratings.rating ? `
                <div style="display: flex; align-items: center; gap: 0.5rem;">
  <div>${this.renderStars(ratings.rating)}</div>
                  <span>${ratings.rating}/5</span>
                  ${ratings.num_ratings ? `<span style="color: var(--text-muted);">(${this.formatNumber(ratings.num_ratings)} reviews)</span>` : ''}
                </div>
              ` : ''}
              ${ratings.num_orders ? `<div style="color: var(--text-muted); margin-top: 0.25rem;"><i class="fas fa-shopping-cart"></i> ${this.formatNumber(ratings.num_orders)} orders</div>` : ''}
            </div>
            <a href="${productUrl}" target="_blank" rel="noopener" style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem 1rem; background: var(--primary); color: white; text-decoration: none; border-radius: 6px; font-size: 0.875rem;">
              <i class="fas fa-external-link-alt"></i> View on AliExpress
            </a>
          </div>
        </div>

        <!-- Seller Information -->
        ${seller.name ? `
          <div style="background: var(--glass); padding: 1rem; border-radius: 8px;">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--secondary);"><i class="fas fa-store"></i> Seller Information</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.5rem;">
              <div><strong>Store:</strong> ${seller.name}</div>
              ${seller.rating ? `<div><strong>Rating:</strong> ${seller.rating}/5</div>` : ''}
            </div>
          </div>
        ` : ''}

        <!-- Description -->
        ${basic.description ? `
          <div style="background: var(--glass); padding: 1rem; border-radius: 8px;">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--accent);"><i class="fas fa-file-text"></i> Description</h4>
            <p style="margin: 0; line-height: 1.5;">${basic.description}</p>
          </div>
        ` : ''}

        <!-- Product Images -->
        ${images.length > 1 ? `
          <div style="background: var(--glass); padding: 1rem; border-radius: 8px;">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);"><i class="fas fa-images"></i> Product Images</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 0.5rem;">
              ${images.slice(1, 9).map(img => `<img src="${img}" style="width: 100%; height: 100px; object-fit: cover; border-radius: 4px; cursor: pointer;" onclick="window.open('${img}', '_blank')" onerror="this.style.display='none'">`).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Specifications -->
        ${Object.keys(specs).length > 0 ? `
          <div style="background: var(--glass); padding: 1rem; border-radius: 8px;">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--warning);"><i class="fas fa-cog"></i> Specifications</h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 0.5rem;">
              ${Object.entries(specs).map(([key, value]) => `
                <div style="padding: 0.5rem; background: var(--bg-primary); border-radius: 4px;">
                  <strong>${key}:</strong> ${value}
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Reviews -->
        ${reviews.length > 0 ? `
          <div style="background: var(--glass); padding: 1rem; border-radius: 8px;">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--success);"><i class="fas fa-comments"></i> Customer Reviews</h4>
            <div style="display: grid; gap: 0.75rem;">
              ${reviews.map(review => `
                <div style="padding: 0.75rem; background: var(--bg-primary); border-radius: 6px; border-left: 3px solid var(--primary);">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <strong style="color: var(--text-primary);">${review.author}</strong>
                    <div>${this.renderStars(review.rating)}</div>
                  </div>
                  <p style="margin: 0; line-height: 1.4; color: var(--text-secondary);">${review.comment}</p>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Shipping Info -->
        ${shipping.info ? `
          <div style="background: var(--glass); padding: 1rem; border-radius: 8px;">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--secondary);"><i class="fas fa-shipping-fast"></i> Shipping Information</h4>
            <p style="margin: 0;">${shipping.info}</p>
          </div>
        ` : ''}
      </div>
    `;
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
  window.app = new SupplierAnalyzer();
  window.supplierAnalyzer = window.app; // Backward compatibility alias
  
  console.log('✅ SupplierAnalyzer initialized as window.app and window.supplierAnalyzer');
  
  // Initialize advanced features after a short delay
  setTimeout(() => {
    if (typeof AdvancedFeatures !== 'undefined') {
      window.features = new AdvancedFeatures(window.app);
      console.log('✅ Advanced features initialized');
    } else {
      console.warn('⚠️ AdvancedFeatures class not found');
    }
  }, 100);
  
  // Add some nice touches
  console.log(`
    🧠 AI Supplier Evaluation System
    🚀 Built with modern web technologies
    🔬 Powered by Gemini AI & Scrapfly
    
    System Status: Ready for Analysis
  `);
});
