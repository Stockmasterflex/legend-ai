#!/bin/bash
# Legend AI - One-Command Development Setup
# Installs everything needed to run Legend AI locally

set -e

echo "🚀 Legend AI Development Setup"
echo "==============================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check prerequisites
log "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    error "Python 3 is required but not installed"
fi

if ! command -v node &> /dev/null; then
    warning "Node.js not found - frontend won't work"
fi

if ! command -v git &> /dev/null; then
    error "Git is required but not installed"
fi

success "Prerequisites check passed"

# Setup Python virtual environment
log "Setting up Python virtual environment..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    success "Created virtual environment"
else
    success "Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate

# Install Python dependencies
log "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
success "Python dependencies installed"

# Run database migrations
log "Setting up database..."
python -m alembic upgrade head || warning "Database migration failed - continuing anyway"
success "Database setup complete"

# Seed sample data
log "Seeding sample data..."
python seed_sample_data.py || warning "Sample data seeding failed - continuing anyway"
success "Sample data seeded"

# Setup frontend (if Node.js is available)
if command -v node &> /dev/null; then
    log "Setting up frontend..."
    cd kyle-portfolio
    
    if [ ! -d "node_modules" ]; then
        npm install
        success "Frontend dependencies installed"
    else
        success "Frontend dependencies already installed"
    fi
    
    cd ..
else
    warning "Skipping frontend setup - Node.js not available"
fi

# Test installation
log "Testing installation..."

# Test Python imports
python -c "
import service_api
from vcp.vcp_detector import VCPDetector  
from backtest.run_backtest import scan_once
print('✅ All Python imports successful')
" || error "Python import test failed"

# Test syntax
find . -name "*.py" -not -path "./.venv/*" -exec python -m py_compile {} \; || error "Syntax check failed"

success "Installation test passed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    log "Creating .env file..."
    cat > .env << EOF
# Legend AI Environment Variables
LEGEND_MOCK_MODE=0
NEWSAPI_KEY=
SHOTS_BASE_URL=http://127.0.0.1:3010
EOF
    success ".env file created"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Quick Start Commands:"
echo "  make up              # Start everything (API + frontend)"
echo "  make api             # Start API only"
echo "  make scan            # Run VCP scan for today"
echo "  make test            # Run test suite"
echo "  python test_production.py  # Full production test"
echo ""
echo "URLs:"
echo "  API: http://127.0.0.1:8000/docs"
echo "  Frontend: http://localhost:3000/demo"
echo "  Health: http://127.0.0.1:8000/healthz"
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
success "Legend AI is ready for development!"