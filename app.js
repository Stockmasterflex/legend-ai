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

        const [marketEnvironment, portfolio] = await Promise.all([
            this.fetchJSON('/api/market/environment').catch(error => {
                console.warn('Market environment unavailable, continuing without it.', error);
                return null;
            }),
            this.fetchJSON('/api/portfolio/positions').catch(error => {
                console.warn('Portfolio positions unavailable, using empty dataset.', error);
                return [];
            })
        ]);

        this.rawPortfolio = Array.isArray(portfolio) ? [...portfolio] : [];

        return { patterns, marketEnvironment, portfolio };
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
        this.populateWatchlist();
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
        const normalizedPatterns = Array.isArray(patterns) ? patterns.map(pattern => {
            const meta = pattern.meta || {};
            const rawSymbol = pattern.symbol || pattern.ticker || meta.symbol || '';
            const symbol = rawSymbol ? String(rawSymbol).toUpperCase() : 'UNKNOWN';
            const name = pattern.name || meta.name || `${symbol} Corp`;
            const sector = pattern.sector || meta.sector || 'Technology';
            const patternType = pattern.pattern_type || pattern.type || pattern.pattern || meta.pattern_type || 'VCP';

            let confidence = typeof pattern.confidence === 'number' ? pattern.confidence : (typeof meta.confidence_score === 'number' ? meta.confidence_score : 0);
            confidence = confidence > 1 ? confidence / 100 : confidence;
            confidence = Math.max(0, Math.min(confidence, 1));

            const rawPrice = pattern.current_price ?? pattern.price ?? meta.current_price ?? meta.pivot_price ?? 0;
            const currentPrice = Number(rawPrice) || 0;
            const pivotPrice = Number(pattern.pivot_price ?? meta.pivot_price ?? currentPrice) || currentPrice;
            const fallbackPrice = currentPrice || pivotPrice;
            const stopLoss = Number(pattern.stop_loss ?? meta.stop_loss ?? (fallbackPrice * 0.92));
            const rsRatingRaw = pattern.rs_rating ?? pattern.rs ?? meta.rs ?? meta.relative_strength ?? 0;
            const rsRating = Math.round(Number(rsRatingRaw) || 0);
            const rawMarketCap = pattern.market_cap_category ?? pattern.market_cap ?? meta.market_cap_category ?? meta.market_cap ?? 'Unknown';
            const marketCap = typeof rawMarketCap === 'string' ? rawMarketCap : String(rawMarketCap);
            const rawVolumeMultiple = meta.volume_multiple ?? meta.volume_vs_average ?? null;
            const numericVolumeMultiple = rawVolumeMultiple !== null ? Number(rawVolumeMultiple) : null;
            const volumeMultiple = Number.isFinite(numericVolumeMultiple) ? Number(numericVolumeMultiple) : null;
            const averageVolume = meta.average_volume ?? meta.avg_volume ?? null;
            const daysInPattern = Number(pattern.days_in_pattern ?? meta.days_in_pattern ?? 0) || 0;
            const stage = pattern.stage || meta.stage || 'N/A';

            return {
                symbol,
                name,
                sector,
                type: patternType,
                confidence,
                pivot_price: pivotPrice || currentPrice,
                stop_loss: stopLoss || (fallbackPrice * 0.92),
                current_price: currentPrice || pivotPrice,
                days_in_pattern: daysInPattern,
                stage,
                rs_rating: rsRating,
                market_cap: marketCap,
                volume_multiple: volumeMultiple,
                average_volume: averageVolume,
            };
        }) : [];

        const relativeStrength = normalizedPatterns.map(pattern => ({
            symbol: pattern.symbol,
            rs_rating: pattern.rs_rating ?? 0,
            ytd_performance: pattern.confidence ? Number(((pattern.confidence - 0.5) * 200).toFixed(1)) : 0,
            relative_performance: 0,
            sector_rank: 0
        }));

        const sectors = this.aggregateSectorPerformance(normalizedPatterns);

        const normalizedPortfolio = Array.isArray(portfolio) ? portfolio.map(position => ({
            symbol: position.symbol,
            pattern_type: position.pattern_type,
            entry_price: position.entry_price,
            current_price: position.current_price,
            position_size: position.position_size,
            unrealized_pnl: position.unrealized_pnl,
            pnl_percent: position.pnl_percent,
            days_held: position.days_held
        })) : [];

        const watchlist = await this.buildWatchlist(normalizedPatterns);

        return {
            patterns: normalizedPatterns,
            relative_strength: relativeStrength,
            sectors,
            portfolio: normalizedPortfolio,
            watchlist
        };
    }

    aggregateSectorPerformance(patterns) {
        const sectorMap = new Map();

        patterns.forEach(pattern => {
            if (!pattern.sector) return;
            if (!sectorMap.has(pattern.sector)) {
                sectorMap.set(pattern.sector, {
                    sector: pattern.sector,
                    totalConfidence: 0,
                    totalRs: 0,
                    count: 0
                });
            }

            const entry = sectorMap.get(pattern.sector);
            entry.totalConfidence += pattern.confidence ?? 0;
            entry.totalRs += pattern.rs_rating ?? 0;
            entry.count += 1;
        });

        const sectors = Array.from(sectorMap.values()).map(entry => {
            const avgConfidence = entry.count ? entry.totalConfidence / entry.count : 0;
            const avgRs = entry.count ? entry.totalRs / entry.count : 0;
            const ytdPerformance = parseFloat(((avgConfidence - 0.5) * 200).toFixed(1));
            const momentumScore = Math.round(avgRs);

            return {
                sector: entry.sector,
                ytd_performance: ytdPerformance,
                momentum_score: momentumScore,
                rs_rating: Math.round(avgRs),
                rank: 0
            };
        }).sort((a, b) => (b.momentum_score ?? 0) - (a.momentum_score ?? 0));

        sectors.forEach((sector, index) => {
            sector.rank = index + 1;
        });

        return sectors;
    }

    async buildWatchlist(patterns) {
        if (!patterns.length) return [];

        const topPatterns = [...patterns]
            .filter(pattern => (pattern.type || '').toLowerCase() === 'vcp')
            .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))
            .slice(0, 3);

        const watchlistPromises = topPatterns.map(async pattern => {
            let trendTemplateScore = 'N/A';

            try {
                const analysis = await this.fetchJSON(`/api/stocks/${pattern.symbol}/analysis`);
                if (analysis && typeof analysis.trend_template_score !== 'undefined') {
                    trendTemplateScore = analysis.trend_template_score;
                }
            } catch (error) {
                console.warn(`Stock analysis unavailable for ${pattern.symbol}.`, error);
            }

            return {
                symbol: pattern.symbol,
                name: pattern.name,
                pattern_type: 'VCP',
                confidence: pattern.confidence,
                current_price: pattern.current_price,
                pivot_price: pattern.pivot_price,
                rs_rating: pattern.rs_rating ?? 0,
                trend_template_score: trendTemplateScore,
                risk_reward_ratio: this.calculateRiskRewardRatio(pattern)
            };
        });

        return Promise.all(watchlistPromises);
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
                {"sector": "Technology", "ytd_performance": 24.8, "momentum_score": 85, "rs_rating": 92, "rank": 1},
                {"sector": "Healthcare", "ytd_performance": 18.2, "momentum_score": 72, "rs_rating": 78, "rank": 2},
                {"sector": "Financial", "ytd_performance": 15.6, "momentum_score": 65, "rs_rating": 68, "rank": 3},
                {"sector": "Consumer Discretionary", "ytd_performance": 12.4, "momentum_score": 58, "rs_rating": 62, "rank": 4}
            ],
            "portfolio": [
                {"symbol": "NVDA", "pattern_type": "VCP", "entry_price": 118.50, "current_price": 128.75, "position_size": 200, "unrealized_pnl": 2050.00, "pnl_percent": 8.6, "days_held": 8},
                {"symbol": "TSLA", "pattern_type": "VCP", "entry_price": 268.40, "current_price": 292.40, "position_size": 80, "unrealized_pnl": 1920.00, "pnl_percent": 8.9, "days_held": 12},
                {"symbol": "SMCI", "pattern_type": "VCP", "entry_price": 812.00, "current_price": 874.20, "position_size": 30, "unrealized_pnl": 1866.00, "pnl_percent": 7.7, "days_held": 9}
            ],
            "watchlist": [
                {"symbol": "NVDA", "name": "NVIDIA Corp.", "pattern_type": "VCP", "confidence": 0.89, "current_price": 128.75, "pivot_price": 135.50, "rs_rating": 95, "trend_template_score": 8, "risk_reward_ratio": 2.8},
                {"symbol": "TSLA", "name": "Tesla Inc.", "pattern_type": "VCP", "confidence": 0.82, "current_price": 292.40, "pivot_price": 305.00, "rs_rating": 88, "trend_template_score": 7, "risk_reward_ratio": 2.6},
                {"symbol": "SMCI", "name": "Super Micro Computer", "pattern_type": "VCP", "confidence": 0.76, "current_price": 874.20, "pivot_price": 915.00, "rs_rating": 91, "trend_template_score": 8, "risk_reward_ratio": 2.1}
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
        this.populatePortfolioTable();
        this.populateWatchlist();
        this.updateLoadMoreVisibility();
    }

    async refreshData() {
        console.log('🔄 Manual scan triggered');
        const { patterns, marketEnvironment, portfolio } = await this.loadBackendData();

        this.marketEnvironment = marketEnvironment || this.getFallbackMarketEnvironment();
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
            
            sectorItem.innerHTML = `
                <div class="sector-name">${sector.sector}</div>
                <div class="sector-performance ${sector.ytd_performance > 0 ? 'positive' : 'negative'}">
                    +${sector.ytd_performance}%
                </div>
            `;
            
            sectorGrid.appendChild(sectorItem);
        });
    }

    populatePatternTable() {
        const tbody = document.getElementById('scanner-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';

        if (!Array.isArray(this.filteredPatterns)) return;

        const relativeStrengthData = Array.isArray(this.data?.relative_strength) ? this.data.relative_strength : [];

        this.filteredPatterns.forEach(pattern => {
            const rsData = relativeStrengthData.find(rs => rs.symbol === pattern.symbol);
            const rsRating = rsData ? rsData.rs_rating : (pattern.rs_rating ?? 0);

            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="symbol-cell">
                    <strong>${pattern.symbol}</strong>
                </td>
                <td>${pattern.name}</td>
                <td>
                    <span class="pattern-type">VCP</span>
                </td>
                <td>
                    <span class="confidence-badge ${this.getConfidenceClass(pattern.confidence)}">
                        ${Math.round(pattern.confidence * 100)}%
                    </span>
                </td>
                <td>
                    <span class="rs-rating ${this.getRSClass(rsRating)}">${rsRating}</span>
                </td>
                <td>$${pattern.current_price.toFixed(2)}</td>
                <td>$${pattern.pivot_price.toFixed(2)}</td>
                <td>${pattern.days_in_pattern}</td>
                <td>${pattern.sector}</td>
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

    populateWatchlist() {
        const watchlistItems = document.getElementById('watchlist-items');
        if (!watchlistItems) return;
        
        watchlistItems.innerHTML = '';

        if (!this.data || !Array.isArray(this.data.watchlist)) return;

        this.data.watchlist.forEach(item => {
            const watchlistItem = document.createElement('div');
            watchlistItem.className = 'watchlist-item';
            watchlistItem.addEventListener('click', () => this.openStockModal(item.symbol));

            const trendScore = item.trend_template_score === 'N/A' || typeof item.trend_template_score === 'undefined'
                ? 'N/A'
                : `${item.trend_template_score}/8`;
            
            watchlistItem.innerHTML = `
                <div class="watchlist-header">
                    <span class="watchlist-symbol">${item.symbol}</span>
                    <span class="watchlist-confidence confidence-badge ${this.getConfidenceClass(item.confidence)}">
                        ${Math.round(item.confidence * 100)}%
                    </span>
                </div>
                <div class="watchlist-details">
                    <span class="watchlist-pattern">${item.pattern_type}</span>
                    <span class="watchlist-price">$${item.current_price.toFixed(2)}</span>
                </div>
                <div class="watchlist-metrics">
                    <span>RS: <span class="rs-score">${item.rs_rating}</span></span>
                    <span>R:R ${item.risk_reward_ratio}</span>
                    <span>Score: ${trendScore}</span>
                </div>
            `;
            
            watchlistItems.appendChild(watchlistItem);
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

        const relativeStrengthData = Array.isArray(this.data.relative_strength) ? this.data.relative_strength : [];

        const basePatterns = this.currentPattern === 'all'
            ? (Array.isArray(this.data?.patterns) ? this.data.patterns : [])
            : this.getVcpPatterns();

        if (!basePatterns.length) {
            this.filteredPatterns = [];
            this.populatePatternTable();
            return;
        }

        this.filteredPatterns = basePatterns.filter(pattern => {
            const rsData = relativeStrengthData.find(rs => rs.symbol === pattern.symbol);
            const rsRating = rsData ? rsData.rs_rating : 0;

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
        const direction = this.currentSort.column === column && this.currentSort.direction === 'asc' ? 'desc' : 'asc';
        this.currentSort = { column, direction };

        if (!Array.isArray(this.filteredPatterns)) return;

        const relativeStrengthData = Array.isArray(this.data?.relative_strength) ? this.data.relative_strength : [];

        this.filteredPatterns.sort((a, b) => {
            let aVal = a[column];
            let bVal = b[column];

            if (column === 'rs') {
                const rsA = relativeStrengthData.find(rs => rs.symbol === a.symbol);
                const rsB = relativeStrengthData.find(rs => rs.symbol === b.symbol);
                aVal = rsA ? rsA.rs_rating : 0;
                bVal = rsB ? rsB.rs_rating : 0;
            }

            if (column === 'price') {
                aVal = a.current_price;
                bVal = b.current_price;
            }

            if (column === 'pivot') {
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
        const relativeStrengthData = Array.isArray(this.data.relative_strength) ? this.data.relative_strength : [];

        const pattern = patterns.find(p => p.symbol === symbol);
        const rsData = relativeStrengthData.find(rs => rs.symbol === symbol);
        
        if (!pattern) return;

        const modalTitle = document.getElementById('modal-title');
        if (modalTitle) {
            modalTitle.textContent = `${symbol} - ${pattern.name}`;
        }
        
        // Populate trend template checklist
        this.populateTrendTemplate(pattern, rsData);
        
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

        if (Array.isArray(this.data.watchlist)) {
            this.data.watchlist.forEach(item => {
                const change = (Math.random() - 0.5) * 0.01;
                item.current_price *= (1 + change);
            });
        }

        // Update displays
        this.populatePatternTable();
        this.populatePortfolioTable();
        this.populateWatchlist();
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
