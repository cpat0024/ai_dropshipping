// 🚀 Advanced Features for AI Dropshipping Platform
class AdvancedFeatures {
  constructor(app) {
    this.app = app;
    console.log('🚀 Initializing AdvancedFeatures...');
    this.init();
  }

  init() {
    try {
      this.addProfitCalculatorModal();
      this.addExportFeatures();
      console.log('✅ Advanced features initialized successfully');
    } catch (error) {
      console.error('❌ Error initializing features:', error);
    }
  }

  addProfitCalculatorModal() {
    const modal = document.createElement('div');
    modal.id = 'profit-calculator-modal';
    modal.className = 'modal hidden';
    modal.innerHTML = `
      <div class="modal-overlay" onclick="features.closeProfitCalculator()"></div>
      <div class="modal-content" style="max-width: 900px;">
        <div class="modal-header">
          <h3><i class="fas fa-calculator"></i> Profit Calculator</h3>
          <button class="modal-close" onclick="features.closeProfitCalculator()">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="profit-calculator">
            <div class="calc-grid">
              <div class="calc-section">
                <h4><i class="fas fa-shopping-cart"></i> Product Costs</h4>
                <div class="calc-input-group">
                  <label>Product Cost ($)</label>
                  <input type="number" id="product-cost" placeholder="12.50" step="0.01">
                </div>
                <div class="calc-input-group">
                  <label>Shipping Cost ($)</label>
                  <input type="number" id="shipping-cost" placeholder="3.50" step="0.01">
                </div>
                <div class="calc-input-group">
                  <label>Payment Processing (%)</label>
                  <input type="number" id="processing-fee" placeholder="2.9" step="0.1">
                </div>
              </div>
              
              <div class="calc-section">
                <h4><i class="fas fa-tag"></i> Selling Price</h4>
                <div class="calc-input-group">
                  <label>Selling Price ($)</label>
                  <input type="number" id="selling-price" placeholder="29.99" step="0.01">
                </div>
                <div class="calc-input-group">
                  <label>Marketing Cost ($)</label>
                  <input type="number" id="marketing-cost" placeholder="5.00" step="0.01">
                </div>
                <div class="calc-input-group">
                  <label>Platform Fee (%)</label>
                  <input type="number" id="platform-fee" placeholder="2.5" step="0.1">
                </div>
              </div>
              
              <div class="calc-results">
                <h4><i class="fas fa-chart-line"></i> Profit Analysis</h4>
                <div id="profit-breakdown"></div>
                <div id="profit-chart"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  showProfitCalculator(product) {
    console.log('📊 Opening profit calculator for:', product);
    const modal = document.getElementById('profit-calculator-modal');
    
    if (!modal) {
      console.error('❌ Profit calculator modal not found');
      return;
    }
    
    // Pre-fill with product data
    if (product) {
      setTimeout(() => {
        const priceStr = product.price || product.price_original || '0';
        const price = parseFloat(priceStr.toString().replace(/[^0-9.]/g, '') || '0');
        
        const productCostInput = document.getElementById('product-cost');
        const sellingPriceInput = document.getElementById('selling-price');
        
        if (productCostInput) productCostInput.value = price.toFixed(2);
        if (sellingPriceInput) sellingPriceInput.value = (price * 2.5).toFixed(2);
        
        this.calculateProfit();
      }, 100);
    }
    
    this.setupProfitCalculatorListeners();
    modal.classList.remove('hidden');
    modal.classList.add('show');
  }

  closeProfitCalculator() {
    const modal = document.getElementById('profit-calculator-modal');
    modal.classList.remove('show');
    setTimeout(() => modal.classList.add('hidden'), 300);
  }

  setupProfitCalculatorListeners() {
    const inputs = ['product-cost', 'shipping-cost', 'processing-fee', 'selling-price', 'marketing-cost', 'platform-fee'];
    inputs.forEach(id => {
      const input = document.getElementById(id);
      if (input) {
        input.addEventListener('input', () => this.calculateProfit());
      }
    });
  }

  calculateProfit() {
    const productCost = parseFloat(document.getElementById('product-cost')?.value || '0');
    const shippingCost = parseFloat(document.getElementById('shipping-cost')?.value || '0');
    const processingFee = parseFloat(document.getElementById('processing-fee')?.value || '2.9');
    const sellingPrice = parseFloat(document.getElementById('selling-price')?.value || '0');
    const marketingCost = parseFloat(document.getElementById('marketing-cost')?.value || '0');
    const platformFee = parseFloat(document.getElementById('platform-fee')?.value || '0');

    const processingAmount = (sellingPrice * processingFee) / 100;
    const platformAmount = (sellingPrice * platformFee) / 100;
    const totalCosts = productCost + shippingCost + processingAmount + marketingCost + platformAmount;
    const profit = sellingPrice - totalCosts;
    const margin = sellingPrice > 0 ? ((profit / sellingPrice) * 100) : 0;

    const breakdownEl = document.getElementById('profit-breakdown');
    if (breakdownEl) {
      breakdownEl.innerHTML = `
        <div class="profit-summary">
          <div class="profit-item ${profit > 0 ? 'positive' : 'negative'}">
            <span class="profit-label">Net Profit:</span>
            <span class="profit-value">$${profit.toFixed(2)}</span>
          </div>
          <div class="profit-item">
            <span class="profit-label">Profit Margin:</span>
            <span class="profit-value">${margin.toFixed(1)}%</span>
          </div>
          <div class="profit-item">
            <span class="profit-label">Total Costs:</span>
            <span class="profit-value">$${totalCosts.toFixed(2)}</span>
          </div>
        </div>
        <div class="cost-breakdown">
          <div class="cost-item">Product: $${productCost.toFixed(2)}</div>
          <div class="cost-item">Shipping: $${shippingCost.toFixed(2)}</div>
          <div class="cost-item">Processing: $${processingAmount.toFixed(2)}</div>
          <div class="cost-item">Marketing: $${marketingCost.toFixed(2)}</div>
          <div class="cost-item">Platform: $${platformAmount.toFixed(2)}</div>
        </div>
      `;
    }
  }

  addTrendAnalysisChart() {
    // Simplified trend analysis - removed for performance
    console.log('📈 Trend analysis available in future update');
  }

  addCompetitionMonitor() {
    // Simplified - just add the button styles
    if (!document.getElementById('competition-style')) {
      const style = document.createElement('style');
      style.id = 'competition-style';
      style.textContent = `
        .competition-btn {
          background: linear-gradient(45deg, #f59e0b, #d97706);
          color: white;
          border: none;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
          cursor: pointer;
          margin-left: 0.5rem;
        }
        .competition-btn:hover {
          opacity: 0.8;
        }
      `;
      document.head.appendChild(style);
    }
  }

  addExportFeatures() {
    // Simplified - features accessible via FAB menu
    console.log('📁 Export features initialized');
  }

  exportToPDF() {
    // Implement PDF export
    this.showNotification('PDF export feature coming soon!', 'info');
  }

  exportToCSV() {
    console.log('📁 Exporting CSV...');
    
    if (!this.app || !this.app.currentProducts || this.app.currentProducts.length === 0) {
      alert('No data to export. Please run an analysis first.');
      return;
    }

    try {
      const csvContent = this.generateCSV(this.app.currentProducts);
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `supplier-analysis-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      alert('✅ CSV exported successfully!');
    } catch (error) {
      console.error('❌ Export error:', error);
      alert('❌ Export failed: ' + error.message);
    }
  }

  generateCSV(products) {
    const headers = ['Title', 'Price', 'Rating', 'Orders', 'Seller', 'AI Score', 'URL'];
    const rows = products.map(product => [
      product.product_title || '',
      product.price || '',
      product.rating || '',
      product.num_orders || '',
      product.seller_name || '',
      product.ai_score || this.app.calculateAIScore(product),
      product.product_url || ''
    ]);
    
    return [headers, ...rows].map(row => 
      row.map(field => `"${String(field).replace(/"/g, '""')}"`).join(',')
    ).join('\n');
  }

  exportToShopify() {
    this.showNotification('Shopify integration coming soon!', 'info');
  }

  scheduleMonitoring() {
    this.showNotification('Price monitoring feature coming soon!', 'info');
  }

  showNotification(message, type = 'info') {
    // Simplified notification system
    const icon = type === 'success' ? '✅' : type === 'warning' ? '⚠️' : 'ℹ️';
    alert(`${icon} ${message}`);
  }
}

// Profit Calculator Helper Class
class ProfitCalculator {
  calculateROI(investment, returns) {
    return ((returns - investment) / investment) * 100;
  }

  calculateBreakeven(fixedCosts, pricePerUnit, variableCostPerUnit) {
    return fixedCosts / (pricePerUnit - variableCostPerUnit);
  }
}

// Trend Analyzer Helper Class
class TrendAnalyzer {
  analyzeTrends(products) {
    // Simulate trend analysis
    return {
      growth: Math.random() * 20 - 5, // -5% to +15%
      demand: Math.random() * 3 + 7,  // 7-10 score
      competition: ['Low', 'Medium', 'High'][Math.floor(Math.random() * 3)]
    };
  }
}

// Competition Tracker Helper Class
class CompetitionTracker {
  trackCompetitors(productId) {
    // Simulate competition tracking
    return {
      competitors: Math.floor(Math.random() * 20) + 5,
      averagePrice: Math.random() * 50 + 10,
      marketShare: Math.random() * 100
    };
  }
}