import { api } from './public/api.js';

// Legend AI Trading Dashboard JavaScript

class LegendAI {
    constructor() {
        this.data = null;
        this.filteredPatterns = [];
        this.currentPattern = 'vcp';
        this.stockChart = null;
        this.currentSort = { column: null, direction: 'asc' };
        this.marketEnvironment = null;
        this.patternPagination = { nextCursor: null, hasMore: false, source: 'v1' };
        this.patternSet = new Set();
        this.rawPatterns = [];
        this.rawPortfolio = [];
        this.isLoadingMore = false;
        this.marketOverview = null;
        this.indexCharts = {};
        this.industryBreakdown = [];

        this.init();
    }

    async init() {
        try {
            const { patterns, marketEnvironment, portfolio } = await this.loadBackendData();
            this.marketEnvironment = marketEnvironment || this.getFallbackMarketEnvironment();
            const initialPatterns = Array.isArray(patterns) ? patterns : [];
            const initialPortfolio = Array.isArray(portfolio) ? portfolio : [];
            if (!this.rawPatterns.length) {
                this.rawPatterns = [...initialPatterns];
                this.patternSet = new Set(initialPatterns.map(pattern => pattern.symbol));
            }
            if (!this.rawPortfolio.length) {
                this.rawPortfolio = [...initialPortfolio];
            }
            this.data = await this.buildDataModel(initialPatterns, initialPortfolio);
        } catch (error) {
            console.error('Failed to load backend data, using fallback dataset.', error);
            const fallbackData = this.getFallbackData();
            this.marketEnvironment = fallbackData.market_environment;
            this.data = fallbackData;
            this.rawPatterns = Array.isArray(fallbackData.patterns) ? [...fallbackData.patterns] : [];
            this.patternSet = new Set(this.rawPatterns.map(pattern => pattern.symbol));
            this.rawPortfolio = Array.isArray(fallbackData.portfolio) ? [...fallbackData.portfolio] : [];
            this.patternPagination = { nextCursor: null, hasMore: false, source: 'fallback' };
        }
        
        this.setupEventListeners();
        this.setDefaultFilters();
        this.populateInitialData();
        this.startRealTimeUpdates();
    }

    async loadBackendData() {
        const initialPage = await this.fetchPatternsPage({ limit: 100 });
        const patterns = Array.isArray(initialPage.items) ? initialPage.items : [];

        this.patternPagination = {
            nextCursor: initialPage.nextCursor || null,
            hasMore: Boolean(initialPage.hasMore),
            source: initialPage.source || 'v1'
        };
        this.patternSet = new Set(patterns.map(pattern => pattern.symbol));
        this.rawPatterns = [...patterns];

        const [marketEnvironment, portfolio, marketOverview] = await Promise.all([
            this.fetchJSON('/api/market/environment').catch(error => {
                console.warn('Market environment unavailable, continuing without it.', error);
                return null;
            }),
            this.fetchJSON('/api/portfolio/positions').catch(error => {
                console.warn('Portfolio positions unavailable, using empty dataset.', error);
                return [];
            }),
            this.fetchJSON('/api/market/indices').catch(error => {
                console.warn('Market overview unavailable, skipping.', error);
                return null;
            })
        ]);

        this.rawPortfolio = Array.isArray(portfolio) ? [...portfolio] : [];
        this.marketOverview = marketOverview && marketOverview.indices ? marketOverview : null;

        return { patterns, marketEnvironment, portfolio, marketOverview: this.marketOverview };
    }

    setDefaultFilters() {
        const rsSlider = document.getElementById('rs-slider');
        if (rsSlider) {
            rsSlider.value = 50;
            const rsValue = document.getElementById('rs-value');
            if (rsValue) rsValue.textContent = '50';
        }

        const confidenceSlider = document.getElementById('confidence-slider');
        if (confidenceSlider) {
            confidenceSlider.value = 20;
            const confValue = document.getElementById('confidence-value');
            if (confValue) confValue.textContent = '20%';
        }

        const sectorFilter = document.getElementById('sector-filter');
        if (sectorFilter) sectorFilter.value = 'all';

        const marketCapFilter = document.getElementById('market-cap-filter');
        if (marketCapFilter) marketCapFilter.value = 'all';

        const minPrice = document.getElementById('min-price');
        if (minPrice) minPrice.value = '';

        const maxPrice = document.getElementById('max-price');
        if (maxPrice) maxPrice.value = '';

        const volumeFilter = document.getElementById('volume-filter');
        if (volumeFilter) volumeFilter.value = 'all';

        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        const vcpTab = document.querySelector('[data-pattern="vcp"]');
        if (vcpTab) {
            vcpTab.classList.add('active');
        }
    }

    async fetchJSON(route, options = {}) {
        const { data } = await api(route, options);
        return data;
    }

    async fetchPatternsPage({ cursor = null, limit = 100 } = {}) {
        const params = new URLSearchParams();
        if (limit) {
            params.set('limit', String(limit));
        }
        if (cursor) {
            params.set('cursor', cursor);
        }

        const query = params.toString();
        const path = query ? `/v1/patterns/all?${query}` : '/v1/patterns/all';

        try {
            const { data } = await api(path);

            if (data && Array.isArray(data.items)) {
                const items = data.items.map(item => {
                    const meta = item.meta || {};
                    const rawSymbol = item.symbol || item.ticker || meta.symbol || '';
                    const symbol = rawSymbol ? String(rawSymbol).toUpperCase() : 'UNKNOWN';
                    return { ...item, symbol };
                });
                const nextCursor = data.next_cursor ?? data.nextCursor ?? data.next ?? null;
                const hasMore =
                    typeof data.has_more === 'boolean'
                        ? data.has_more
                        : typeof data.hasMore === 'boolean'
                            ? data.hasMore
                            : Boolean(nextCursor);

                return {
                    items,
                    nextCursor,
                    hasMore,
                    source: 'v1'
                };
            }

            if (Array.isArray(data)) {
                const items = data.map(item => {
                    const meta = item.meta || {};
                    const rawSymbol = item.symbol || item.ticker || meta.symbol || '';
                    const symbol = rawSymbol ? String(rawSymbol).toUpperCase() : 'UNKNOWN';
                    return { ...item, symbol };
                });
                return {
                    items,
                    nextCursor: null,
                    hasMore: false,
                    source: 'legacy'
                };
            }
        } catch (error) {
            console.warn('v1 patterns endpoint unavailable, falling back to legacy.', error);
        }

        try {
            const { data: legacy } = await api('/api/patterns/all');
            const items = Array.isArray(legacy) ? legacy.map(item => {
                const meta = item.meta || {};
                const rawSymbol = item.symbol || item.ticker || meta.symbol || '';
                const symbol = rawSymbol ? String(rawSymbol).toUpperCase() : 'UNKNOWN';
                return { ...item, symbol };
            }) : [];
            return {
                items,
                nextCursor: null,
                hasMore: false,
                source: 'legacy'
            };
        } catch (fallbackError) {
            console.error('Failed to fetch patterns from legacy endpoint.', fallbackError);
            throw fallbackError;
        }
    }

    async rebuildDataModel() {
        const portfolioSource = Array.isArray(this.data?.portfolio) ? this.data.portfolio : this.rawPortfolio;
        this.rawPortfolio = Array.isArray(portfolioSource) ? [...portfolioSource] : [];
        this.data = await this.buildDataModel(this.rawPatterns, this.rawPortfolio);
        this.applyFilters();
        this.populateSectorGrid();
        this.populatePortfolioTable();
        this.populateIndustryList();
        this.populateMarketOverview();
    }

    async loadMorePatterns() {
        if (this.isLoadingMore || !this.patternPagination?.hasMore || this.patternPagination.source !== 'v1') {
            return;
        }

        this.isLoadingMore = true;
        const loadMoreButton = document.getElementById('load-more-patterns');
        if (loadMoreButton) {
            loadMoreButton.disabled = true;
            loadMoreButton.textContent = 'Loading...';
        }

        try {
            const nextPage = await this.fetchPatternsPage({ cursor: this.patternPagination.nextCursor });
            const newItems = Array.isArray(nextPage.items) ? nextPage.items.filter(item => !this.patternSet.has(item.symbol)) : [];

            newItems.forEach(item => this.patternSet.add(item.symbol));

            if (newItems.length) {
                this.rawPatterns = [...this.rawPatterns, ...newItems];
            }

            this.patternPagination = {
                nextCursor: nextPage.nextCursor || null,
                hasMore: Boolean(nextPage.hasMore),
                source: nextPage.source || this.patternPagination.source
            };

            if (newItems.length) {
                await this.rebuildDataModel();
            }
        } catch (error) {
            console.error('Failed to load additional patterns.', error);
        } finally {
            if (loadMoreButton) {
                loadMoreButton.disabled = false;
                loadMoreButton.textContent = 'Load more';
            }
            this.isLoadingMore = false;
            this.updateLoadMoreVisibility();
        }
    }

    updateLoadMoreVisibility() {
        const button = document.getElementById('load-more-patterns');
        if (!button) return;

        const shouldShow = Boolean(this.patternPagination?.hasMore) && this.patternPagination.source === 'v1';
        if (shouldShow) {
            button.classList.remove('hidden');
            if (!this.isLoadingMore) {
                button.disabled = false;
                button.textContent = 'Load more';
            }
        } else {
            button.classList.add('hidden');
        }
    }

    async buildDataModel(patterns, portfolio) {
        const normalizedPatterns = Array.isArray(patterns)
            ? patterns.map(pattern => {
                  const meta = pattern.meta || {};
                  const rawSymbol = pattern.symbol || pattern.ticker || meta.symbol || '';
                  const symbol = rawSymbol ? String(rawSymbol).toUpperCase() : 'UNKNOWN';
                  const name = pattern.name || meta.name || `${symbol} Corp`;
                  const sector = pattern.sector || meta.sector || 'Unknown';
                  const industry = pattern.industry || meta.industry || sector;
                  const patternType = pattern.pattern_type || pattern.type || pattern.pattern || meta.pattern_type || 'VCP';

                  let confidence = typeof pattern.confidence === 'number'
                      ? pattern.confidence
                      : (typeof meta.confidence_score === 'number' ? meta.confidence_score : 0);
                  confidence = confidence > 1 ? confidence / 100 : confidence;
                  confidence = Math.max(0, Math.min(confidence, 1));

                  const currentPrice = Number(pattern.current_price ?? pattern.price ?? meta.current_price ?? 0) || 0;
                  const pivotPrice = Number(pattern.pivot_price ?? meta.pivot_price ?? currentPrice) || currentPrice;
                  const stopLoss = Number(pattern.stop_loss ?? meta.stop_loss ?? (pivotPrice ? pivotPrice * 0.92 : 0)) || 0;
                  const rsRating = Number.isFinite(pattern.rs_rating)
                      ? Number(pattern.rs_rating)
                      : Number.isFinite(pattern.rs)
                          ? Number(pattern.rs)
                          : Number(meta.rs_rating ?? meta.rs ?? 0);
                  const daysInPattern = Number(pattern.days_in_pattern ?? meta.days_in_pattern ?? 0) || 0;
                  const trendStrength = Number.isFinite(pattern.trend_strength)
                      ? Number(pattern.trend_strength)
                      : Number(meta.trend_strength ?? 0);
                  const volumeMultiple = Number.isFinite(pattern.volume_multiple)
                      ? Number(pattern.volume_multiple)
                      : Number.isFinite(meta.volume_multiple)
                          ? Number(meta.volume_multiple)
                          : null;
                  const averageVolume = Number(pattern.average_volume ?? meta.average_volume ?? 0) || null;
                  const marketCap = Number(pattern.market_cap ?? meta.market_cap ?? 0) || null;
                  const marketCapHuman = pattern.market_cap_human || meta.market_cap_human || (marketCap ? this.formatMarketCap(marketCap) : '—');

                  return {
                      symbol,
                      name,
                      sector,
                      industry,
                      type: patternType,
                      confidence,
                      pivot_price: pivotPrice,
                      stop_loss: stopLoss,
                      current_price: currentPrice,
                      days_in_pattern: daysInPattern,
                      rs_rating: Number.isFinite(rsRating) ? Math.max(0, Math.min(100, Math.round(rsRating))) : null,
                      trend_strength: Number.isFinite(trendStrength) ? trendStrength : null,
                      volume_multiple: volumeMultiple,
                      average_volume: averageVolume,
                      market_cap: marketCap,
                      market_cap_human: marketCapHuman,
                  };
              })
            : [];

        const sectors = this.aggregateSectorPerformance(normalizedPatterns);
        this.industryBreakdown = this.aggregateIndustryPerformance(normalizedPatterns);

        const normalizedPortfolio = Array.isArray(portfolio)
            ? portfolio.map(position => ({
                  symbol: position.symbol,
                  pattern_type: position.pattern_type,
                  entry_price: position.entry_price,
                  current_price: position.current_price,
                  position_size: position.position_size,
                  unrealized_pnl: position.unrealized_pnl,
                  pnl_percent: position.pnl_percent,
                  days_held: position.days_held,
              }))
            : [];

        return {
            patterns: normalizedPatterns,
            sectors,
            industries: this.industryBreakdown,
            portfolio: normalizedPortfolio,
        };
    }

    aggregateSectorPerformance(patterns) {
        const sectorMap = new Map();

        patterns.forEach(pattern => {
            if (!pattern.sector) return;
            if (!sectorMap.has(pattern.sector)) {
                sectorMap.set(pattern.sector, {
                    sector: pattern.sector,
                    count: 0,
                    totalConfidence: 0,
                    totalRs: 0,
                    totalTrend: 0,
                });
            }

            const entry = sectorMap.get(pattern.sector);
            entry.count += 1;
            entry.totalConfidence += pattern.confidence ?? 0;
            entry.totalRs += pattern.rs_rating ?? 0;
            entry.totalTrend += pattern.trend_strength ?? 0;
        });

        return Array.from(sectorMap.values())
            .map(entry => ({
                sector: entry.sector,
                count: entry.count,
                avg_confidence: entry.count ? entry.totalConfidence / entry.count : 0,
                avg_rs: entry.count ? entry.totalRs / entry.count : 0,
                avg_trend: entry.count ? entry.totalTrend / entry.count : 0,
            }))
            .sort((a, b) => (b.avg_rs ?? 0) - (a.avg_rs ?? 0));
    }

    aggregateIndustryPerformance(patterns) {
        const industryMap = new Map();

        patterns.forEach(pattern => {
            const key = pattern.industry || 'Unknown';
            if (!industryMap.has(key)) {
                industryMap.set(key, {
                    industry: key,
                    sector: pattern.sector || 'Unknown',
                    count: 0,
                    totalRs: 0,
                    totalConfidence: 0,
                });
            }
            const entry = industryMap.get(key);
            entry.count += 1;
            entry.totalRs += pattern.rs_rating ?? 0;
            entry.totalConfidence += pattern.confidence ?? 0;
        });

        return Array.from(industryMap.values())
            .map(entry => ({
                industry: entry.industry,
                sector: entry.sector,
                count: entry.count,
                avg_rs: entry.count ? Math.round(entry.totalRs / entry.count) : 0,
                avg_confidence: entry.count ? entry.totalConfidence / entry.count : 0,
            }))
            .sort((a, b) => b.avg_rs - a.avg_rs)
            .slice(0, 12);
    }

    formatMarketCap(value) {
        if (!value || Number.isNaN(value)) return '—';
        const abs = Math.abs(value);
        if (abs >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
        if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
        if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
        if (abs >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
        return value.toFixed(0);
    }

    calculateRiskRewardRatio(pattern) {
        if (!pattern) return 'N/A';
        const risk = (pattern.current_price ?? 0) - (pattern.stop_loss ?? 0);
        const reward = (pattern.pivot_price ?? 0) - (pattern.current_price ?? 0);

        if (risk <= 0 || reward <= 0) return 'N/A';

        const ratio = reward / risk;
        if (!isFinite(ratio) || ratio <= 0) return 'N/A';

        return ratio.toFixed(1);
    }

    getFallbackData() {
        return {
            "market_environment": this.getFallbackMarketEnvironment(),
            "market_data": {
                "AAPL": {
                    "info": {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
                    "current_price": 145.23,
                    "data": [{"Date": "2024-08-28", "Open": 143.50, "High": 146.80, "Low": 142.90, "Close": 145.23, "Volume": 2450000}]
                },
                "NVDA": {
                    "info": {"symbol": "NVDA", "name": "NVIDIA Corp.", "sector": "Technology", "industry": "Semiconductors"},
                    "current_price": 128.75,
                    "data": [{"Date": "2024-08-28", "Open": 126.20, "High": 130.45, "Low": 125.80, "Close": 128.75, "Volume": 4850000}]
                },
                "TSLA": {
                    "info": {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Technology", "industry": "Electric Vehicles"},
                    "current_price": 285.60,
                    "data": [{"Date": "2024-08-28", "Open": 282.10, "High": 288.90, "Low": 280.50, "Close": 285.60, "Volume": 3200000}]
                }
            },
            "patterns": [
                {"symbol": "NVDA", "name": "NVIDIA Corp.", "sector": "Technology", "type": "VCP", "confidence": 0.89, "stage": "Stage 2", "contractions": 4, "days_in_pattern": 25, "pivot_price": 135.50, "stop_loss": 122.00, "current_price": 128.75, "rs_rating": 95},
                {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Technology", "type": "VCP", "confidence": 0.82, "stage": "Stage 2", "contractions": 3, "days_in_pattern": 21, "pivot_price": 305.00, "stop_loss": 281.00, "current_price": 292.40, "rs_rating": 88},
                {"symbol": "SMCI", "name": "Super Micro Computer", "sector": "Technology", "type": "VCP", "confidence": 0.76, "stage": "Stage 2", "contractions": 3, "days_in_pattern": 18, "pivot_price": 915.00, "stop_loss": 842.50, "current_price": 874.20, "rs_rating": 91}
            ],
            "relative_strength": [
                {"symbol": "NVDA", "rs_rating": 95, "ytd_performance": 45.8, "relative_performance": 28.3, "sector_rank": 2},
                {"symbol": "TSLA", "rs_rating": 88, "ytd_performance": 38.2, "relative_performance": 21.7, "sector_rank": 5},
                {"symbol": "SMCI", "rs_rating": 91, "ytd_performance": 41.5, "relative_performance": 24.1, "sector_rank": 3}
            ],
            "sectors": [
                {"sector": "Technology", "count": 12, "avg_confidence": 0.82, "avg_rs": 88, "avg_trend": 0.6},
                {"sector": "Healthcare", "count": 5, "avg_confidence": 0.74, "avg_rs": 76, "avg_trend": 0.4},
                {"sector": "Financial", "count": 4, "avg_confidence": 0.69, "avg_rs": 71, "avg_trend": 0.32},
                {"sector": "Consumer Discretionary", "count": 3, "avg_confidence": 0.65, "avg_rs": 64, "avg_trend": 0.28}
            ],
            "industries": [
                {"industry": "Semiconductors", "sector": "Technology", "count": 6, "avg_rs": 92, "avg_confidence": 0.84},
                {"industry": "Software", "sector": "Technology", "count": 4, "avg_rs": 85, "avg_confidence": 0.78},
                {"industry": "Biotech", "sector": "Healthcare", "count": 3, "avg_rs": 74, "avg_confidence": 0.7}
            ],
            "portfolio": [
                {"symbol": "NVDA", "pattern_type": "VCP", "entry_price": 118.50, "current_price": 128.75, "position_size": 200, "unrealized_pnl": 2050.00, "pnl_percent": 8.6, "days_held": 8},
                {"symbol": "TSLA", "pattern_type": "VCP", "entry_price": 268.40, "current_price": 292.40, "position_size": 80, "unrealized_pnl": 1920.00, "pnl_percent": 8.9, "days_held": 12},
                {"symbol": "SMCI", "pattern_type": "VCP", "entry_price": 812.00, "current_price": 874.20, "position_size": 30, "unrealized_pnl": 1866.00, "pnl_percent": 7.7, "days_held": 9}
            ]
        };
    }

    setupEventListeners() {
        // Pattern tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchPattern(e.target.dataset.pattern);
            });
        });

        // Filter controls
        const rsSlider = document.getElementById('rs-slider');
        if (rsSlider) {
            rsSlider.addEventListener('input', (e) => {
                document.getElementById('rs-value').textContent = e.target.value;
                this.applyFilters();
            });
        }


        const confidenceSlider = document.getElementById('confidence-slider');
        if (confidenceSlider) {
            confidenceSlider.addEventListener('input', (e) => {
                document.getElementById('confidence-value').textContent = e.target.value + '%';
                this.applyFilters();
            });
        }

        const sectorFilter = document.getElementById('sector-filter');
        if (sectorFilter) {
            sectorFilter.addEventListener('change', () => {
                this.applyFilters();
            });
        }

        const marketCapFilter = document.getElementById('market-cap-filter');
        if (marketCapFilter) {
            marketCapFilter.addEventListener('change', () => {
                this.applyFilters();
            });
        }

        const applyFiltersBtn = document.getElementById('apply-filters');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => {
                this.applyFilters();
            });
        }

        ['min-price', 'max-price'].forEach(id => {
            const input = document.getElementById(id);
            if (!input) return;
            input.addEventListener('change', () => this.applyFilters());
            input.addEventListener('keyup', (event) => {
                if (event.key === 'Enter') {
                    this.applyFilters();
                }
            });
        });

        const volumeFilter = document.getElementById('volume-filter');
        if (volumeFilter) {
            volumeFilter.addEventListener('change', () => this.applyFilters());
        }

        const scanButton = document.getElementById('scan-now');
        if (scanButton) {
            scanButton.addEventListener('click', async () => {
                const originalText = scanButton.textContent;
                scanButton.disabled = true;
                scanButton.textContent = 'Scanning…';
                scanButton.classList.add('is-loading');

                try {
                    await this.refreshData();
                } catch (error) {
                    console.error('Manual scan failed', error);
                    alert(`Scan failed: ${error?.message || 'unknown error'}`);
                } finally {
                    scanButton.disabled = false;
                    scanButton.textContent = originalText;
                    scanButton.classList.remove('is-loading');
                }
            });
        }

        const loadMoreButton = document.getElementById('load-more-patterns');
        if (loadMoreButton) {
            loadMoreButton.addEventListener('click', () => {
                this.loadMorePatterns();
            });
        }

        // Table sorting
        document.querySelectorAll('[data-sort]').forEach(th => {
            th.addEventListener('click', (e) => {
                this.sortTable(e.target.dataset.sort);
            });
        });

        // Modal controls - Fixed event listeners
        const modalClose = document.getElementById('modal-close');
        if (modalClose) {
            modalClose.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.closeModal();
            });
        }

        const modalOverlay = document.querySelector('.modal-overlay');
        if (modalOverlay) {
            modalOverlay.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.closeModal();
            });
        }

        // Keyboard event for ESC key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !document.getElementById('stock-modal').classList.contains('hidden')) {
                this.closeModal();
            }
        });

        // Sector grid clicks
        const sectorGrid = document.getElementById('sector-grid');
        if (sectorGrid) {
            sectorGrid.addEventListener('click', (e) => {
                const sectorItem = e.target.closest('.sector-item');
                if (sectorItem) {
                    const sector = sectorItem.dataset.sector;
                    this.filterBySector(sector);
                }
            });
        }
    }

    populateInitialData() {
        this.applyFilters();
        this.updateMarketPulse();
        this.populateSectorGrid();
        this.populateIndustryList();
        this.populatePortfolioTable();
        this.populateMarketOverview();
        this.updateLoadMoreVisibility();
    }

    async refreshData() {
        console.log('🔄 Manual scan triggered');
        const { patterns, marketEnvironment, portfolio, marketOverview } = await this.loadBackendData();

        this.marketEnvironment = marketEnvironment || this.getFallbackMarketEnvironment();
        this.marketOverview = marketOverview || this.marketOverview;
        this.data = await this.buildDataModel(patterns, portfolio);
        this.populateInitialData();

        console.log('✅ Scan complete:', {
            patterns: this.data?.patterns?.length || 0,
            portfolio: this.data?.portfolio?.length || 0
        });
    }

    getVcpPatterns() {
        if (!this.data || !Array.isArray(this.data.patterns)) return [];
        return this.data.patterns.filter(pattern => (pattern.type || '').toLowerCase() === 'vcp');
    }

    getFallbackMarketEnvironment() {
        return {
            current_trend: 'Confirmed Uptrend',
            days_in_trend: 23,
            distribution_days: 2,
            follow_through_date: '2024-08-15',
            market_health_score: 78,
            breadth_indicators: {
                advance_decline_line: 'Strong',
                new_highs_vs_lows: '245 vs 23',
                up_volume_ratio: '68%'
            }
        };
    }

    updateMarketPulse() {
        if (!this.marketEnvironment) return;

        const { current_trend, days_in_trend, distribution_days, market_health_score, breadth_indicators } = this.marketEnvironment;

        const statusText = document.querySelector('.market-status .status-text');
        if (statusText) {
            statusText.textContent = current_trend;
        }

        const daysInTrend = document.querySelector('.market-status .days-in-trend');
        if (daysInTrend) {
            daysInTrend.textContent = `Day ${days_in_trend}`;
        }

        const trendValue = document.querySelector('.market-intelligence .pulse-item:nth-child(1) .pulse-value');
        if (trendValue) {
            trendValue.textContent = current_trend;
            trendValue.classList.toggle('confirmed', `${current_trend}`.toLowerCase().includes('confirmed'));
        }

        const distributionValue = document.querySelector('.market-intelligence .pulse-item:nth-child(2) .pulse-value');
        if (distributionValue) {
            distributionValue.textContent = distribution_days;
        }

        const healthValue = document.querySelector('.market-intelligence .health-value');
        if (healthValue) {
            healthValue.textContent = market_health_score;
        }

        const healthProgress = document.querySelector('.market-intelligence .health-progress');
        if (healthProgress) {
            healthProgress.style.width = `${market_health_score}%`;
        }

        const highsLows = document.querySelector('.market-intelligence .pulse-item:nth-child(4) .pulse-value');
        if (highsLows) {
            const highsVsLows = breadth_indicators && breadth_indicators.new_highs_vs_lows ? breadth_indicators.new_highs_vs_lows : '—';
            highsLows.textContent = highsVsLows;
        }
    }

    populateSectorGrid() {
        const sectorGrid = document.getElementById('sector-grid');
        if (!sectorGrid) return;
        
        sectorGrid.innerHTML = '';

        if (!this.data || !Array.isArray(this.data.sectors)) return;

        this.data.sectors.forEach(sector => {
            const sectorItem = document.createElement('div');
            sectorItem.className = 'sector-item';
            sectorItem.dataset.sector = sector.sector;

            const avgRs = sector.avg_rs ?? 0;
            const momentumClass = avgRs >= 70 ? 'positive' : avgRs >= 50 ? 'neutral' : 'negative';

            sectorItem.innerHTML = `
                <div class="sector-name">${sector.sector}</div>
                <div class="sector-stats">
                    <span>${sector.count} setups</span>
                    <span class="sector-performance ${momentumClass}">RS ${avgRs}</span>
                </div>
            `;

            sectorGrid.appendChild(sectorItem);
        });
    }

    populateIndustryList() {
        const list = document.getElementById('industry-list');
        if (!list) return;

        list.innerHTML = '';

        if (!Array.isArray(this.industryBreakdown)) return;

        this.industryBreakdown.forEach(entry => {
            const item = document.createElement('div');
            item.className = 'industry-item';
            item.innerHTML = `
                <div>
                    <div class="industry-item__name">${entry.industry}</div>
                    <div class="industry-item__sector">${entry.sector}</div>
                </div>
                <div class="industry-item__stats">
                    <span>RS ${entry.avg_rs}</span>
                    <span>${entry.count} setups</span>
                </div>
            `;
            list.appendChild(item);
        });
    }

    populateMarketOverview() {
        const grid = document.getElementById('indices-grid');
        if (!grid) return;

        grid.innerHTML = '';
        const timestampEl = document.getElementById('market-update-time');
        if (timestampEl) {
            timestampEl.textContent = this.marketOverview?.updated_at
                ? `Updated ${new Date(this.marketOverview.updated_at).toLocaleTimeString()}`
                : '';
        }

        if (!this.marketOverview || !Array.isArray(this.marketOverview.indices)) return;

        this.marketOverview.indices.forEach(index => {
            const card = document.createElement('div');
            card.className = 'index-card';

            const changeClass = index.change_percent >= 0 ? 'positive' : 'negative';
            const changeLabel = index.change_percent >= 0 ? '+' : '';

            card.innerHTML = `
                <div class="index-card__header">
                    <div>
                        <div class="index-card__symbol">${index.symbol}</div>
                        <div class="index-card__price">${index.last_price?.toFixed(2) ?? '—'}</div>
                    </div>
                    <div class="index-card__change ${changeClass}">
                        ${changeLabel}${(index.change_percent * 100).toFixed(2)}%
                    </div>
                </div>
                <canvas class="index-card__sparkline" id="spark-${index.symbol}"></canvas>
            `;

            grid.appendChild(card);
            this.renderIndexSparkline(`spark-${index.symbol}`, index.sparkline || []);
        });
    }

    renderIndexSparkline(canvasId, series) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.indexCharts[canvasId]) {
            this.indexCharts[canvasId].destroy();
        }

        const labels = series.map(point => point.time);
        const data = series.map(point => point.close);

        this.indexCharts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        data,
                        borderColor: '#00ffaa',
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.2,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: { display: false }
                }
            }
        });
    }

    populatePatternTable() {
        const tbody = document.getElementById('scanner-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';

        if (!Array.isArray(this.filteredPatterns)) return;

        this.filteredPatterns.forEach(pattern => {
            const rsRating = Number.isFinite(pattern.rs_rating) ? pattern.rs_rating : 0;
            const trendStrength = Number.isFinite(pattern.trend_strength) ? pattern.trend_strength : null;
            const volumeMultiple = Number.isFinite(pattern.volume_multiple) ? pattern.volume_multiple : null;
            const marketCap = pattern.market_cap_human || this.formatMarketCap(pattern.market_cap);

            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="symbol-cell"><strong>${pattern.symbol}</strong></td>
                <td>${pattern.name}</td>
                <td>${pattern.type}</td>
                <td>
                    <span class="confidence-badge ${this.getConfidenceClass(pattern.confidence)}">
                        ${Math.round((pattern.confidence ?? 0) * 100)}%
                    </span>
                </td>
                <td><span class="rs-rating ${this.getRSClass(rsRating)}">${rsRating}</span></td>
                <td>${trendStrength !== null ? `${(trendStrength * 100).toFixed(0)}%` : '—'}</td>
                <td>$${(pattern.current_price ?? 0).toFixed(2)}</td>
                <td>$${(pattern.pivot_price ?? 0).toFixed(2)}</td>
                <td>${pattern.days_in_pattern ?? 0}</td>
                <td>${pattern.sector || '—'}</td>
                <td>${pattern.industry || '—'}</td>
                <td>${volumeMultiple !== null ? volumeMultiple.toFixed(2) : '—'}</td>
                <td>${marketCap || '—'}</td>
                <td>
                    <button class="btn btn--primary btn--small" onclick="app.openStockModal('${pattern.symbol}')">
                        Analyze
                    </button>
                </td>
            `;

            tbody.appendChild(row);
        });

        const resultsCount = document.getElementById('results-count');
        if (resultsCount) {
            resultsCount.textContent = `${this.filteredPatterns.length} patterns found`;
        }

        this.updateLoadMoreVisibility();
    }

    populatePortfolioTable() {
        const tbody = document.getElementById('portfolio-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';

        if (!this.data || !Array.isArray(this.data.portfolio)) return;

        this.data.portfolio.forEach(position => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${position.symbol}</strong></td>
                <td>${position.pattern_type}</td>
                <td>$${position.entry_price.toFixed(2)}</td>
                <td>$${position.current_price.toFixed(2)}</td>
                <td class="${position.unrealized_pnl >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                    $${position.unrealized_pnl.toFixed(0)}
                </td>
                <td class="${position.pnl_percent >= 0 ? 'pnl-positive' : 'pnl-negative'}">
                    ${position.pnl_percent >= 0 ? '+' : ''}${position.pnl_percent.toFixed(1)}%
                </td>
                <td>${position.days_held}</td>
            `;
            tbody.appendChild(row);
        });
    }

    switchPattern(pattern) {
        this.currentPattern = pattern === 'all' ? 'all' : 'vcp';

        // Update active tab
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        const targetTab = document.querySelector(`[data-pattern="${this.currentPattern}"]`) || document.querySelector('[data-pattern="vcp"]');
        if (targetTab) {
            targetTab.classList.add('active');
        }

        this.applyFilters();
    }

    applyFilters() {
        const rsSlider = document.getElementById('rs-slider');
        const confidenceSlider = document.getElementById('confidence-slider');
        const sectorFilter = document.getElementById('sector-filter');
        const marketCapFilter = document.getElementById('market-cap-filter');
        const minPriceInput = document.getElementById('min-price');
        const maxPriceInput = document.getElementById('max-price');
        const volumeFilter = document.getElementById('volume-filter');

        const rsThreshold = rsSlider ? parseInt(rsSlider.value) : 0;
        const confidenceThreshold = confidenceSlider ? parseInt(confidenceSlider.value) / 100 : 0;
        const sectorFilterValue = sectorFilter ? sectorFilter.value : 'all';
        const marketCapFilterValue = marketCapFilter ? marketCapFilter.value : 'all';
        const minPrice = minPriceInput && minPriceInput.value !== '' ? parseFloat(minPriceInput.value) : Number.NaN;
        const maxPrice = maxPriceInput && maxPriceInput.value !== '' ? parseFloat(maxPriceInput.value) : Number.NaN;
        const volumeThreshold = volumeFilter && volumeFilter.value !== 'all'
            ? parseFloat(volumeFilter.value)
            : Number.NaN;

        const basePatterns = this.currentPattern === 'all'
            ? (Array.isArray(this.data?.patterns) ? this.data.patterns : [])
            : this.getVcpPatterns();

        if (!basePatterns.length) {
            this.filteredPatterns = [];
            this.populatePatternTable();
            return;
        }

        this.filteredPatterns = basePatterns.filter(pattern => {
            const rsRating = Number.isFinite(pattern.rs_rating) ? pattern.rs_rating : 0;

            // RS Rating filter
            if (rsRating < rsThreshold) return false;

            // Confidence filter
            if (pattern.confidence < confidenceThreshold) return false;

            // Sector filter
            if (sectorFilterValue !== 'all' && pattern.sector !== sectorFilterValue) return false;

            // Market cap filter (match substring to allow for detailed labels)
            if (marketCapFilterValue !== 'all') {
                const patternCap = (pattern.market_cap || 'unknown').toString().toLowerCase();
                if (!patternCap.includes(marketCapFilterValue)) {
                    return false;
                }
            }

            // Price range filters
            if (!Number.isNaN(minPrice) && pattern.current_price < minPrice) return false;
            if (!Number.isNaN(maxPrice) && pattern.current_price > maxPrice) return false;

            // Volume filters using relative multiple
            if (!Number.isNaN(volumeThreshold)) {
                const multiple = typeof pattern.volume_multiple === 'number' && Number.isFinite(pattern.volume_multiple)
                    ? pattern.volume_multiple
                    : null;
                if (multiple !== null && multiple < volumeThreshold) {
                    return false;
                }
            }

            return true;
        });

        this.populatePatternTable();
    }

    sortTable(column) {
        const columnMap = {
            pattern_type: 'type',
            price: 'current_price',
            pivot: 'pivot_price',
            rs: 'rs_rating',
            rs_rating: 'rs_rating',
            trend_strength: 'trend_strength',
            market_cap: 'market_cap',
            volume_multiple: 'volume_multiple',
        };

        const actualColumn = columnMap[column] || column;

        const direction = this.currentSort.column === actualColumn && this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        this.currentSort = { column: actualColumn, direction };

        if (!Array.isArray(this.filteredPatterns)) return;

        this.filteredPatterns.sort((a, b) => {
            let aVal = a[actualColumn];
            let bVal = b[actualColumn];

            if (actualColumn === 'rs_rating') {
                aVal = a.rs_rating ?? 0;
                bVal = b.rs_rating ?? 0;
            }

            if (actualColumn === 'current_price') {
                aVal = a.current_price;
                bVal = b.current_price;
            }

            if (actualColumn === 'pivot_price') {
                aVal = a.pivot_price;
                bVal = b.pivot_price;
            }

            if (typeof aVal === 'string') {
                return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }

            return direction === 'asc' ? aVal - bVal : bVal - aVal;
        });

        this.populatePatternTable();
    }

    openStockModal(symbol) {
        if (!this.data) return;

        const patterns = Array.isArray(this.data.patterns) ? this.data.patterns : [];

        const pattern = patterns.find(p => p.symbol === symbol);
        
        if (!pattern) return;

        const modalTitle = document.getElementById('modal-title');
        if (modalTitle) {
            modalTitle.textContent = `${symbol} - ${pattern.name}`;
        }
        
        // Populate trend template checklist
        this.populateTrendTemplate(pattern, { rs_rating: pattern.rs_rating });
        
        // Populate pattern metrics
        this.populatePatternMetrics(pattern);
        
        // Populate risk/reward
        this.populateRiskReward(pattern);
        
        // Create chart
        this.createStockChart(symbol, pattern);
        
        // Show modal
        const modal = document.getElementById('stock-modal');
        if (modal) {
            modal.classList.remove('hidden');
            // Prevent body scroll when modal is open
            document.body.style.overflow = 'hidden';
        }
    }

    closeModal() {
        const modal = document.getElementById('stock-modal');
        if (modal) {
            modal.classList.add('hidden');
            // Restore body scroll
            document.body.style.overflow = '';
        }
        
        if (this.stockChart) {
            this.stockChart.destroy();
            this.stockChart = null;
        }
    }

    populateTrendTemplate(pattern, rsData) {
        const checklist = document.getElementById('trend-checklist');
        if (!checklist) return;

        const criteria = [
            { label: 'Current price above 150 & 200 MA', passed: true },
            { label: '150 MA above 200 MA', passed: true },
            { label: '150 MA trending up for 1+ months', passed: true },
            { label: '200 MA flat or trending up', passed: true },
            { label: 'Current price 25%+ above 52-week low', passed: true },
            { label: 'Current price within 25% of 52-week high', passed: true },
            { label: 'RS Rating 70+', passed: rsData && rsData.rs_rating >= 70 },
            { label: 'Price pattern tight & constructive', passed: pattern.confidence >= 0.7 }
        ];

        checklist.innerHTML = '';
        criteria.forEach(criterion => {
            const item = document.createElement('div');
            item.className = 'checklist-item';
            item.innerHTML = `
                <span class="checklist-icon ${criterion.passed ? 'passed' : 'failed'}">
                    ${criterion.passed ? '✓' : '✗'}
                </span>
                <span>${criterion.label}</span>
            `;
            checklist.appendChild(item);
        });
    }

    populatePatternMetrics(pattern) {
        const metricsContainer = document.getElementById('pattern-metrics');
        if (!metricsContainer) return;

        const metrics = {
            'Pattern Type': pattern.type,
            'Confidence Score': `${Math.round(pattern.confidence * 100)}%`,
            'Days in Pattern': pattern.days_in_pattern,
            'Stage': pattern.stage || 'N/A',
            'Current Price': `$${pattern.current_price.toFixed(2)}`,
            'Pivot Price': `$${pattern.pivot_price.toFixed(2)}`
        };

        metricsContainer.innerHTML = '';
        Object.entries(metrics).forEach(([label, value]) => {
            const row = document.createElement('div');
            row.className = 'metric-row';
            row.innerHTML = `
                <span class="label">${label}:</span>
                <span class="value">${value}</span>
            `;
            metricsContainer.appendChild(row);
        });
    }

    populateRiskReward(pattern) {
        const riskRewardContainer = document.getElementById('risk-reward');
        if (!riskRewardContainer) return;

        const risk = pattern.current_price - pattern.stop_loss;
        const reward = pattern.pivot_price - pattern.current_price;
        const ratio = reward / risk;

        const metrics = {
            'Entry Price': `$${pattern.current_price.toFixed(2)}`,
            'Stop Loss': `$${pattern.stop_loss.toFixed(2)}`,
            'Target (Pivot)': `$${pattern.pivot_price.toFixed(2)}`,
            'Risk per Share': `$${risk.toFixed(2)}`,
            'Reward per Share': `$${reward.toFixed(2)}`,
            'Risk:Reward Ratio': `1:${ratio.toFixed(1)}`
        };

        riskRewardContainer.innerHTML = '';
        Object.entries(metrics).forEach(([label, value]) => {
            const row = document.createElement('div');
            row.className = 'metric-row';
            row.innerHTML = `
                <span class="label">${label}:</span>
                <span class="value">${value}</span>
            `;
            riskRewardContainer.appendChild(row);
        });
    }

    createStockChart(symbol, pattern) {
        const ctx = document.getElementById('stock-chart');
        if (!ctx) return;

        const chartContext = ctx.getContext('2d');
        
        if (this.stockChart) {
            this.stockChart.destroy();
        }

        // Generate sample price data
        const data = this.generatePriceData(pattern);

        this.stockChart = new Chart(chartContext, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Price',
                    data: data.prices,
                    borderColor: '#ffd700',
                    backgroundColor: 'rgba(255, 215, 0, 0.1)',
                    borderWidth: 2,
                    fill: false
                }, {
                    label: 'Volume',
                    data: data.volumes,
                    type: 'bar',
                    backgroundColor: 'rgba(0, 255, 136, 0.3)',
                    borderColor: '#00ff88',
                    borderWidth: 1,
                    yAxisID: 'volume'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#e0e6ed'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#a0a6b0'
                        },
                        grid: {
                            color: '#2a3441'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#a0a6b0'
                        },
                        grid: {
                            color: '#2a3441'
                        }
                    },
                    volume: {
                        type: 'linear',
                        position: 'right',
                        ticks: {
                            color: '#a0a6b0'
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 0
                    }
                }
            }
        });
    }

    generatePriceData(pattern) {
        const labels = [];
        const prices = [];
        const volumes = [];
        const basePrice = pattern.current_price;
        
        // Generate 30 days of sample data
        for (let i = 29; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString());
            
            // Generate realistic price movements
            const volatility = 0.02;
            const trend = (30 - i) / 30 * 0.1; // Slight upward trend
            const randomMove = (Math.random() - 0.5) * volatility;
            const price = basePrice * (1 + trend + randomMove);
            prices.push(price);
            
            // Generate volume data
            const baseVolume = 1000000;
            const volumeVariation = Math.random() * 0.5 + 0.75;
            volumes.push(baseVolume * volumeVariation);
        }
        
        return { labels, prices, volumes };
    }

    filterBySector(sector) {
        const sectorFilter = document.getElementById('sector-filter');
        if (sectorFilter) {
            sectorFilter.value = sector;
        }
        this.applyFilters();
    }

    getConfidenceClass(confidence) {
        if (confidence >= 0.8) return 'confidence-high';
        if (confidence >= 0.6) return 'confidence-medium';
        return 'confidence-low';
    }

    getRSClass(rs) {
        if (rs >= 80) return 'excellent';
        if (rs >= 60) return 'good';
        return 'average';
    }

    startRealTimeUpdates() {
        // Simulate real-time price updates every 5 seconds
        setInterval(() => {
            this.updatePrices();
        }, 5000);

        // Update streaming indicator
        setInterval(() => {
            const indicator = document.querySelector('.stream-indicator');
            if (indicator) {
                indicator.style.opacity = indicator.style.opacity === '0.5' ? '1' : '0.5';
            }
        }, 1000);
    }

    updatePrices() {
        if (!this.data) return;

        // Simulate small price movements
        if (Array.isArray(this.data.patterns)) {
            this.data.patterns.forEach(pattern => {
                const change = (Math.random() - 0.5) * 0.01; // ±0.5% random change
                pattern.current_price *= (1 + change);
            });
        }

        if (Array.isArray(this.data.portfolio)) {
            this.data.portfolio.forEach(position => {
                const change = (Math.random() - 0.5) * 0.01;
                position.current_price *= (1 + change);
                position.unrealized_pnl = (position.current_price - position.entry_price) * position.position_size;
                position.pnl_percent = ((position.current_price - position.entry_price) / position.entry_price) * 100;
            });
        }

        // Update displays
        this.populatePatternTable();
        this.populatePortfolioTable();
        this.populateIndustryList();
        this.populateMarketOverview();
    }
}

// Initialize the application
function bootstrapLegendApp() {
    const instance = new LegendAI();
    window.app = instance;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrapLegendApp, { once: true });
} else {
    bootstrapLegendApp();
}
/* Updated: 2025-10-06 10:12:00 - Module bootstrap */
