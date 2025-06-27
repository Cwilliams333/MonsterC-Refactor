# MonsterC CSV Analysis Tool 🚀

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Gradio](https://img.shields.io/badge/Gradio-4.0%2B-orange.svg)](https://gradio.app)
[![Tabulator](https://img.shields.io/badge/Tabulator.js-6.3.0-green.svg)](https://tabulator.info)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/user/repo/graphs/commit-activity)

**A professional-grade CSV analysis platform designed for automation testing data analysis, featuring dual-method failure counting, interactive pivot tables, and advanced business intelligence dashboards.**

## ✨ Latest Features (2025)

### 🎯 **Dual-Method Failure Analysis**
- **Pure Failures Mode**: Count only `Overall status = 'FAILURE'` (1000 total)
- **Comprehensive Mode**: Include `ERROR + result_FAIL` records (1023 total)
- **Toggle Control**: Real-time switching between counting methodologies
- **Excel Validation**: Matches Excel pivot table calculations perfectly

### 📊 **Professional Dashboard Interface**
- **Horizontal Summary Cards**: Top Station, Test Case, and Model metrics with gradient styling
- **Color-Coded Analytics**: 🔴 HIGH, 🟡 MEDIUM, 🟢 LOW status indicators
- **Quick Access Totals**: Redundant Grand Total columns for instant insights
- **750px Embedded View**: Larger snapshot with full horizontal scrolling

### 🎨 **Enhanced User Experience**
- **Collapsible UI Panels**: Clean interface with ⚙️ Failure Method and 🔍 Filter Options
- **Blue-Themed Headers**: Professional Grand Total column styling
- **Smart Layout**: Horizontal space optimization for better data visibility
- **Responsive Design**: Works seamlessly across desktop and tablet devices

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd MonsterC

# Install dependencies
pip install -r requirements.txt

# Launch the application
python main.py
```

### Usage
1. **📁 Upload CSV Data** - Drag & drop your automation testing data
2. **⚙️ Configure Analysis** - Choose failure counting method (Pure vs Comprehensive)
3. **🤖 Run Analysis** - Click "Automation High Failures" for interactive pivot table
4. **📊 Explore Results** - Use embedded view or open in new tab for full controls

## 🏗️ Architecture Overview

```
MonsterC/
├── 🎨 UI Layer
│   ├── src/ui/gradio_app.py         # Main Gradio interface with dual-method toggle
│   ├── src/tabulator_app.py         # Enhanced Tabulator.js with horizontal scrolling
│   └── src/dash_pivot_app.py        # Legacy AG Grid interface (optional)
├── ⚙️ Service Layer
│   ├── services/pivot_service.py    # Excel-compatible pivot generation
│   ├── services/analysis_service.py # Core KPI analysis and dashboards
│   ├── services/filtering_service.py# Advanced data filtering and preprocessing
│   └── services/wifi_error_service.py # Specialized wireless error analysis
├── 🔧 Common Layer
│   ├── common/io.py                 # File I/O with encoding detection
│   ├── common/logging_config.py     # Centralized logging with decorators
│   └── common/mappings.py           # Device models and station mappings
└── 🧪 Tests & Assets
    ├── tests/                       # Comprehensive test suite
    ├── test_data/                   # Sample automation data
    └── assets/                      # Static resources
```

## 📈 Core Analysis Workflows

### 🤖 **Automation High Failures**
**Purpose**: Identify automation line failure patterns with business-critical accuracy

**Key Features**:
- **Operator Filtering**: STN251_RED, STN252_RED, STN351_GRN, STN352_GRN (24 stations total)
- **Dual Counting Logic**: Toggle between Pure FAILURE (1000) vs Comprehensive FAILURE+ERROR (1023)
- **Test Case Preservation**: Maintains concatenated values like "Camera Pictures,Camera Flash"
- **Heat Map Intelligence**: 🔴 RED (overall max), 🟠 ORANGE (test case max), 🟡 YELLOW (top 3 models)

**Business Value**:
- Matches Excel pivot calculations exactly (validates against 1023 expected total)
- Identifies phantom ERROR records with valuable test data (23 additional insights)
- Provides station-level failure prioritization for resource allocation

### 🔍 **High Error Rates Analysis**
**Purpose**: Deep-dive 3-level hierarchical error analysis

**Structure**: `Model → Error Code → Error Message`
- **Comprehensive Error Mapping**: Links error codes to human-readable descriptions
- **Statistical Analysis**: Failure rate calculations and trend identification
- **Root Cause Analysis**: Groups related errors for systematic troubleshooting

### 📊 **Advanced Visualizations**

#### **Professional Summary Cards**
```
🏭 Top Station     🔬 Top Test Case     📱 Top Model
   59 failures        608 failures        120 failures
   radi183            Camera Pictures      iPhone14ProMax
```

#### **Enhanced Tabulator Interface**
- **Native Tree Grouping**: No enterprise license required (saves $1000+)
- **True Horizontal Scrolling**: All 24 station columns accessible
- **Quick Access Totals**: Grand Total column positioned after hierarchy
- **Professional Styling**: Dark theme with blue headers and white text

## ⚙️ Configuration & Customization

### **Environment Variables**
```bash
export LOG_LEVEL=INFO                    # Set logging verbosity
export GRADIO_SERVER_PORT=7860          # Main interface port
export TABULATOR_PORT=5001              # Tabulator interface port
```

### **CSV Data Requirements**
Your automation testing data should include:

| Column | Description | Example |
|--------|-------------|---------|
| `Operator` | Test operator ID | `STN251_RED(id:10089)` |
| `Overall status` | Test result | `FAILURE`, `ERROR`, `SUCCESS` |
| `result_FAIL` | Failure details | `Camera Pictures,Face ID` |
| `Station ID` | Station identifier | `radi183`, `radi115` |
| `Model` | Device model | `iPhone14ProMax` |
| `error_code` | Error ID | `6A-Display Fail` |
| `error_message` | Error description | `Display Grading Failed` |

## 🎨 Advanced Features

### **Heat Mapping System**
Multi-level conditional formatting for instant pattern recognition:

1. **🔴 RED (Critical)**: Overall highest failure count across entire dataset
2. **🟠 ORANGE (High)**: Highest failure per test case category
3. **🟡 YELLOW (Medium)**: Highest failure for top 3 models in each category

### **Smart Data Processing**
- **Concatenated Test Preservation**: Keeps "Camera Pictures,Camera Flash" as analytical units
- **Station Intelligence**: Auto-sorts columns by failure count (highest impact first)
- **Device Mapping**: Translates internal codes to business-friendly names
- **Zero Suppression**: Clean interface hiding empty cells for better readability

### **Performance Optimizations**
- **Lazy Loading**: Handles 3.5k-6k row datasets → ~500 pivot rows efficiently
- **Client-Side Processing**: Real-time filtering without server requests
- **Smart Caching**: Temporary data storage for improved response times
- **Responsive Rendering**: Optimized for both embedded and full-screen views

## 🧪 Testing & Quality Assurance

### **Run Tests**
```bash
# Full test suite
pytest tests/ -v --cov=src --cov-report=term-missing

# Specific modules
pytest tests/test_pivot_service.py -v
pytest tests/test_tabulator.py -v

# Code quality checks
pre-commit run --all-files
```

### **Development Workflow**
```bash
# Install development tools
pip install pytest pytest-cov pre-commit

# Setup pre-commit hooks
pre-commit install

# Code formatting
black --check src/ tests/
isort --check-only src/ tests/
flake8 src/ tests/
```

## 🌟 Business Intelligence Features

### **KPI Dashboard Cards**
Real-time calculation of critical business metrics:
- **Station Utilization**: `24/24 (100.0%)` stations with failures
- **Failure Distribution**: Visual breakdown across test categories
- **Model Performance**: Top failing devices with actionable counts

### **Excel Compatibility Mode**
- **Validation Ready**: Matches Excel pivot calculations exactly
- **Business Logic**: Configurable FAILURE vs FAILURE+ERROR counting
- **Audit Trail**: Comprehensive logging for compliance and troubleshooting

### **Enterprise-Grade UI**
- **Professional Theming**: Dark headers, gradient cards, consistent branding
- **Accessibility**: High contrast ratios, keyboard navigation support
- **Mobile Responsive**: Touch-friendly controls for tablet-based quality stations

## 🛠️ Integration & Deployment

### **Production Deployment**
```bash
# Production mode
python main.py --production

# With custom configuration
GRADIO_SERVER_PORT=8080 python main.py

# Launch specific interface
python launch_tabulator.py  # Enhanced Tabulator view only
```

### **Browser Compatibility**
- ✅ Chrome 80+ (Recommended)
- ✅ Firefox 75+
- ✅ Safari 13+
- ✅ Edge 80+

## 📞 Support & Contributing

### **Getting Help**
- 📝 **Issues**: [GitHub Issues](https://github.com/user/repo/issues)
- 📖 **Documentation**: Comprehensive inline help and tooltips
- 🔧 **Configuration**: CLAUDE.md contains development commands and architecture notes

### **Contributing**
```bash
# Development setup
git checkout -b feature/amazing-enhancement
pip install -r requirements.txt
pre-commit install

# Make changes and test
pytest tests/
black src/ tests/
isort src/ tests/

# Submit changes
git commit -m "✨ Add amazing enhancement"
git push origin feature/amazing-enhancement
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**MonsterC** - *Professional CSV Analysis for Automation Testing Excellence* 🚀

*Built with ❤️ for quality engineers and automation teams worldwide*
