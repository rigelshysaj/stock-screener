/**
 * Stock Screener Frontend Application
 */

let dataTable = null;
let currentResults = [];

// Initialize DataTable when document is ready
$(document).ready(function() {
    initDataTable();
});

function initDataTable() {
    if (dataTable) {
        dataTable.destroy();
    }

    dataTable = $('#results-table').DataTable({
        pageLength: 25,
        order: [[5, 'desc']], // Sort by drop % descending
        language: {
            emptyTable: "Select a market and click 'Start Scan' to find opportunities"
        },
        columnDefs: [
            { targets: [3, 4], className: 'text-end' },
            { targets: [5, 6], className: 'text-center' }
        ]
    });
}

// Get selected markets (checkboxes)
function getSelectedMarkets() {
    const selected = [];
    $('input[name="market"]:checked').each(function() {
        selected.push($(this).val());
    });
    return selected;
}

// Select all markets
function selectAllMarkets() {
    $('input[name="market"]').prop('checked', true);
}

// Clear all markets
function clearAllMarkets() {
    $('input[name="market"]').prop('checked', false);
}

// Start scanning with batch support - collects all results before displaying
async function startScan() {
    const markets = getSelectedMarkets();

    if (markets.length === 0) {
        alert('Please select at least one market to scan.');
        return;
    }

    const minDrop = parseFloat($('#min-drop').val()) || 20;
    const maxDrop = parseFloat($('#max-drop').val()) || 30;
    const lookbackDays = parseInt($('#lookback-days').val()) || 2;

    // Validate range
    if (minDrop >= maxDrop) {
        alert('Min drop must be less than max drop.');
        return;
    }

    // Update UI - loading state
    $('#scan-btn').prop('disabled', true);
    $('#scan-text').text('Scanning...');
    $('#scan-spinner').removeClass('d-none');
    $('#status-bar').removeClass('d-none').addClass('alert-info').removeClass('alert-success alert-danger');
    $('#status-text').text(`Scanning ${markets.length} market(s)...`);

    // Clear previous results
    currentResults = [];
    dataTable.clear().draw();
    $('#results-count').text('Scanning...');

    const batchSize = 100;
    let batch = 0;
    let hasMore = true;
    let totalScanned = 0;
    let totalTickers = 0;

    try {
        // Phase 1: Fetch all stock data in batches
        while (hasMore) {
            const response = await fetch('/api/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    markets: markets,
                    min_drop: minDrop,
                    max_drop: maxDrop,
                    lookback_days: lookbackDays,
                    batch: batch,
                    batch_size: batchSize
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Update totals
            totalTickers = data.total_tickers;
            totalScanned += data.tickers_scanned;
            hasMore = data.has_more;

            // Add new stocks to results
            if (data.stocks && data.stocks.length > 0) {
                currentResults = currentResults.concat(data.stocks);
            }

            // Update progress - Phase 1: Stock scanning
            const scanProgress = Math.min(50, Math.round((totalScanned / totalTickers) * 50));
            $('#status-text').text(`Scanning stocks... ${scanProgress * 2}% (${totalScanned}/${totalTickers})`);

            batch++;
        }

        if (currentResults.length === 0) {
            $('#status-bar').removeClass('alert-info').addClass('alert-warning');
            $('#status-text').text(`No stocks found with ${minDrop}-${maxDrop}% drop in last ${lookbackDays} day(s). Scanned ${totalTickers} tickers.`);
            $('#results-count').text('0 stocks found');
            return;
        }

        // Phase 2: Load all news/safety data
        $('#status-text').text(`Loading safety analysis for ${currentResults.length} stocks...`);
        await loadAllNewsData(currentResults);

        // Phase 3: Display all results at once
        displayAllResults(currentResults);

        // Final update
        $('#status-bar').removeClass('alert-info').addClass('alert-success');
        $('#status-text').text(`Complete! Found ${currentResults.length} stocks with ${minDrop}-${maxDrop}% drop in last ${lookbackDays} day(s). Scanned ${totalTickers} tickers.`);
        $('#results-count').text(`${currentResults.length} stocks found`);

    } catch (error) {
        console.error('Scan error:', error);
        $('#status-bar').removeClass('alert-info').addClass('alert-danger');
        $('#status-text').text('Error during scan: ' + error.message);
    } finally {
        // Reset button
        $('#scan-btn').prop('disabled', false);
        $('#scan-text').text('Start Scan');
        $('#scan-spinner').addClass('d-none');
    }
}

// Load all news/safety data for stocks
async function loadAllNewsData(stocks) {
    let loaded = 0;
    const total = stocks.length;

    for (const stock of stocks) {
        try {
            const response = await fetch(`/api/stock/${stock.ticker}/news`);
            if (response.ok) {
                const analysis = await response.json();
                stock.safety_score = analysis.safety_score;
                stock.assessment = analysis.assessment || 'unknown';
                stock.safety_message = analysis.message || '';
                stock.critical_keywords = analysis.critical_keywords_found || [];
            } else {
                stock.safety_score = null;
                stock.assessment = 'unknown';
                stock.safety_message = 'Unable to load';
            }
        } catch (error) {
            console.warn(`Error loading news for ${stock.ticker}:`, error);
            stock.safety_score = null;
            stock.assessment = 'unknown';
            stock.safety_message = 'Error loading';
        }

        loaded++;
        const progress = Math.round((loaded / total) * 100);
        $('#status-text').text(`Loading safety analysis... ${progress}% (${loaded}/${total})`);
    }
}

// Display all results at once with safety data
function displayAllResults(stocks) {
    dataTable.clear();

    stocks.forEach(stock => {
        const safetyHtml = formatSafetyBadge(
            stock.safety_score,
            stock.assessment,
            stock.safety_message
        );

        dataTable.row.add([
            formatTicker(stock.ticker),
            truncateName(stock.name, 30),
            stock.sector || 'N/A',
            formatPrice(stock.current_price, stock.currency),
            formatPrice(stock.reference_price || stock.high_52w, stock.currency),
            formatDropPct(stock.drop_pct),
            safetyHtml
        ]);
    });

    dataTable.draw();
    setupRowClickHandlers();
}

// Update results table (full replace)
function updateResultsTable(stocks) {
    // Clear existing data
    dataTable.clear();

    // Add each stock as a row with loading indicator for safety
    stocks.forEach(stock => {
        dataTable.row.add([
            formatTicker(stock.ticker),
            truncateName(stock.name, 30),
            stock.sector || 'N/A',
            formatPrice(stock.current_price, stock.currency),
            formatPrice(stock.high_52w, stock.currency),
            formatDropPct(stock.drop_pct),
            `<span class="safety-loading" data-ticker="${stock.ticker}"><span class="spinner-border spinner-border-sm"></span></span>`
        ]);
    });

    dataTable.draw();

    // Load news analysis progressively in background
    loadNewsProgressively(stocks);

    setupRowClickHandlers();
}

// Append stocks to table (for batch loading)
function appendToResultsTable(stocks) {
    // Add each stock as a row with loading indicator for safety
    stocks.forEach(stock => {
        dataTable.row.add([
            formatTicker(stock.ticker),
            truncateName(stock.name, 30),
            stock.sector || 'N/A',
            formatPrice(stock.current_price, stock.currency),
            formatPrice(stock.high_52w, stock.currency),
            formatDropPct(stock.drop_pct),
            `<span class="safety-loading" data-ticker="${stock.ticker}"><span class="spinner-border spinner-border-sm"></span></span>`
        ]);
    });

    dataTable.draw();
    setupRowClickHandlers();
}

// Setup click handlers for table rows
function setupRowClickHandlers() {
    // Add click handlers for rows
    $('#results-table tbody').off('click').on('click', 'tr', function() {
        const data = dataTable.row(this).data();
        if (data && data[0]) {
            const ticker = extractTicker(data[0]);
            showStockDetails(ticker);
        }
    });

    // Make rows look clickable
    $('#results-table tbody tr').addClass('clickable-row');
}

// Format helpers
function formatTicker(ticker) {
    return `<strong>${ticker}</strong>`;
}

function truncateName(name, maxLength) {
    if (!name) return 'N/A';
    return name.length > maxLength ? name.substring(0, maxLength) + '...' : name;
}

function formatPrice(price, currency = 'USD') {
    if (!price) return '-';
    const symbols = { 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'HKD': 'HK$' };
    const symbol = symbols[currency] || currency + ' ';
    return symbol + price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDropPct(pct) {
    if (!pct) return '-';
    let className = 'drop-light';
    if (pct >= 25) className = 'drop-medium';
    if (pct >= 28) className = 'drop-heavy';
    return `<span class="drop-badge ${className}">-${pct.toFixed(1)}%</span>`;
}

function formatSafetyScore(score) {
    if (score === '-' || score === null || score === undefined) {
        return '<span class="safety-score" style="background:#6c757d">?</span>';
    }
    let className = 'score-low';
    if (score >= 60) className = 'score-high';
    else if (score >= 40) className = 'score-medium';
    return `<span class="safety-score ${className}">${score}</span>`;
}

function formatAssessment(assessment, message) {
    const icons = {
        'safe': '✓',
        'caution': '⚠',
        'avoid': '✗',
        'unknown': '?'
    };
    const labels = {
        'safe': 'Safe',
        'caution': 'Caution',
        'avoid': 'Avoid',
        'unknown': 'Unknown'
    };
    const icon = icons[assessment] || '?';
    const label = labels[assessment] || 'Unknown';
    const title = message || '';

    return `<span class="safety-badge safety-${assessment}" title="${title}">${icon} ${label}</span>`;
}

function extractTicker(tickerHtml) {
    // Extract ticker from HTML like "<strong>AAPL</strong>"
    const match = tickerHtml.match(/>([^<]+)</);
    return match ? match[1] : tickerHtml;
}

// Show stock details modal
async function showStockDetails(ticker) {
    const modal = new bootstrap.Modal(document.getElementById('stockModal'));
    $('#modal-title').text(`${ticker} - Loading...`);
    $('#modal-body').html(`
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-2">Loading stock details...</p>
        </div>
    `);
    modal.show();

    try {
        const response = await fetch(`/api/stock/${ticker}`);
        if (!response.ok) throw new Error('Failed to load stock details');

        const data = await response.json();
        $('#modal-title').text(`${ticker} - ${data.name}`);
        $('#modal-body').html(renderStockDetails(data));

    } catch (error) {
        $('#modal-body').html(`
            <div class="alert alert-danger">
                Error loading stock details: ${error.message}
            </div>
        `);
    }
}

// Render stock details HTML
function renderStockDetails(stock) {
    const newsAnalysis = stock.news_analysis || {};
    const news = newsAnalysis.news || [];

    // Safety section
    const safetyScore = newsAnalysis.safety_score ?? 'N/A';
    const assessment = newsAnalysis.assessment || 'unknown';
    const safetyClass = safetyScore >= 60 ? 'score-high' : (safetyScore >= 40 ? 'score-medium' : 'score-low');

    // Critical keywords
    let keywordsHtml = '';
    if (newsAnalysis.critical_keywords_found && newsAnalysis.critical_keywords_found.length > 0) {
        keywordsHtml = newsAnalysis.critical_keywords_found.map(kw =>
            `<span class="keyword-tag keyword-critical">${kw}</span>`
        ).join('');
    }

    // News items
    let newsHtml = '<p class="text-muted">No recent news available</p>';
    if (news.length > 0) {
        newsHtml = news.slice(0, 5).map(item => {
            const sentiment = item.sentiment?.interpretation || 'neutral';
            return `
                <div class="news-item ${sentiment}">
                    <div class="title">${item.title}</div>
                    <div class="meta">
                        <span>${item.source}</span> • <span>${item.date}</span>
                        <span class="badge bg-${sentiment === 'positive' ? 'success' : (sentiment === 'negative' ? 'danger' : 'warning')} ms-2">
                            ${sentiment}
                        </span>
                    </div>
                </div>
            `;
        }).join('');
    }

    return `
        <!-- Price Overview -->
        <div class="stock-detail-section">
            <h6>Price Overview</h6>
            <div class="row g-3">
                <div class="col-4">
                    <div class="metric-card">
                        <div class="value">${formatPrice(stock.current_price, stock.currency)}</div>
                        <div class="label">Current Price</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="metric-card">
                        <div class="value">${formatPrice(stock.high_52w, stock.currency)}</div>
                        <div class="label">52W High</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="metric-card">
                        <div class="value">${formatPrice(stock.low_52w, stock.currency)}</div>
                        <div class="label">52W Low</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Safety Analysis -->
        <div class="stock-detail-section">
            <h6>Safety Analysis</h6>
            <div class="row align-items-center">
                <div class="col-auto">
                    <div class="safety-score ${safetyClass}" style="width:60px;height:60px;font-size:1.2rem;">
                        ${safetyScore}
                    </div>
                </div>
                <div class="col">
                    <div class="assessment-text assessment-${assessment}">
                        ${assessment.toUpperCase()}
                    </div>
                    <div class="text-muted">${newsAnalysis.message || ''}</div>
                    ${keywordsHtml ? `<div class="mt-2">${keywordsHtml}</div>` : ''}
                </div>
            </div>
        </div>

        <!-- Key Metrics -->
        <div class="stock-detail-section">
            <h6>Key Metrics</h6>
            <div class="row g-2">
                <div class="col-md-3 col-6">
                    <div class="metric-card">
                        <div class="value">${stock.pe_ratio ? stock.pe_ratio.toFixed(1) : 'N/A'}</div>
                        <div class="label">P/E Ratio</div>
                    </div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="metric-card">
                        <div class="value">${stock.pb_ratio ? stock.pb_ratio.toFixed(2) : 'N/A'}</div>
                        <div class="label">P/B Ratio</div>
                    </div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="metric-card">
                        <div class="value">${stock.dividend_yield ? (stock.dividend_yield * 100).toFixed(2) + '%' : 'N/A'}</div>
                        <div class="label">Dividend Yield</div>
                    </div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="metric-card">
                        <div class="value">${stock.beta ? stock.beta.toFixed(2) : 'N/A'}</div>
                        <div class="label">Beta</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent News -->
        <div class="stock-detail-section">
            <h6>Recent News</h6>
            ${newsHtml}
        </div>

        <!-- Company Info -->
        <div class="stock-detail-section">
            <h6>About</h6>
            <p><strong>Sector:</strong> ${stock.sector || 'N/A'}</p>
            <p><strong>Industry:</strong> ${stock.industry || 'N/A'}</p>
            ${stock.description ? `<p class="text-muted small">${stock.description.substring(0, 300)}...</p>` : ''}
        </div>
    `;
}

// Load news analysis progressively for each stock
async function loadNewsProgressively(stocks) {
    for (const stock of stocks) {
        try {
            const response = await fetch(`/api/stock/${stock.ticker}/news`);
            if (response.ok) {
                const analysis = await response.json();
                updateSafetyCell(stock.ticker, analysis);
            } else {
                updateSafetyCell(stock.ticker, null);
            }
        } catch (error) {
            console.warn(`Error loading news for ${stock.ticker}:`, error);
            updateSafetyCell(stock.ticker, null);
        }
    }
}

// Update safety cell for a specific ticker
function updateSafetyCell(ticker, analysis) {
    const cell = $(`.safety-loading[data-ticker="${ticker}"]`);
    if (cell.length) {
        if (analysis && analysis.safety_score !== undefined) {
            const score = analysis.safety_score;
            const assessment = analysis.assessment || 'unknown';
            cell.replaceWith(formatSafetyBadge(score, assessment, analysis.message));
        } else {
            cell.replaceWith('<span class="badge bg-secondary">?</span>');
        }
    }
}

// Format safety badge with score and assessment
function formatSafetyBadge(score, assessment, message) {
    const icons = { 'safe': '✓', 'caution': '⚠', 'avoid': '✗', 'unknown': '?' };
    const colors = { 'safe': 'success', 'caution': 'warning', 'avoid': 'danger', 'unknown': 'secondary' };
    const icon = icons[assessment] || '?';
    const color = colors[assessment] || 'secondary';
    const title = message || '';
    return `<span class="badge bg-${color}" title="${title}" style="cursor:help">${icon} ${score}</span>`;
}
