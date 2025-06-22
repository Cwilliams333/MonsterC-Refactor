# MonsterC CSV Analysis Tool

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Gradio](https://img.shields.io/badge/Gradio-4.0%2B-orange.svg)](https://gradio.app)
[![Dash](https://img.shields.io/badge/Dash-2.0%2B-lightblue.svg)](https://dash.plotly.com)
[![Tabulator](https://img.shields.io/badge/Tabulator.js-6.3.0-green.svg)](https://tabulator.info)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/user/repo/graphs/commit-activity)

A comprehensive CSV analysis tool designed for automation testing data analysis, featuring interactive pivot tables, advanced filtering, and multiple visualization interfaces.

## Features

### Core Analysis Capabilities
- **Automation High Failures Analysis** - Specialized analysis for automation testing data with FAILURE + ERROR logic
- **Error Code Deep-Dive** - 3-level hierarchical analysis (Model → Error Code → Error Message)
- **Repeated Failures Detection** - Identify patterns in recurring test failures
- **WiFi Error Analysis** - Specialized analysis for wireless connectivity issues
- **IMEI Data Processing** - Extract and process device identifier information

### Interactive Visualization Options
- **Classic AG Grid Interface** - Traditional Excel-style pivot tables with expandable groups
- **Enhanced Tabulator Interface** - Native collapsible groups with advanced heat mapping
- **Custom Heat Maps** - Multi-level highlighting system for failure pattern identification
- **Grand Total Columns** - Horizontal summation across all stations for better prioritization

### Advanced Features
- **Concatenated Test Case Preservation** - Maintains complex test case relationships (e.g., "Camera Pictures,Camera Flash")
- **Smart Column Sorting** - Automatic ordering by failure count (highest impact first)
- **Zen Zero Display** - Clean interface that hides zero values for better readability
- **Responsive Design** - Works across different screen sizes and devices

## Project Structure

```
MonsterC/
├── src/
│   ├── common/                    # Shared utilities and configurations
│   │   ├── io.py                 # File I/O operations
│   │   ├── logging_config.py     # Centralized logging setup
│   │   └── mappings.py           # Data mapping configurations
│   ├── services/                 # Business logic layer
│   │   ├── analysis_service.py   # Core analysis operations
│   │   ├── filtering_service.py  # Data filtering and sorting
│   │   ├── pivot_service.py      # Pivot table generation
│   │   ├── repeated_failures_service.py  # Failure pattern analysis
│   │   ├── wifi_error_service.py # WiFi-specific analysis
│   │   └── imei_extractor_service.py     # IMEI processing
│   ├── ui/                       # User interface layer
│   │   └── gradio_app.py         # Main Gradio application
│   ├── dash_pivot_app.py         # Dash AG Grid interface
│   └── tabulator_app.py          # Enhanced Tabulator.js interface
├── tests/                        # Test suite
├── test_data/                    # Sample data for testing
├── assets/                       # Static assets
├── launch_tabulator.py           # Tabulator interface launcher
└── main.py                       # Application entry point
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup
1. Clone the repository:
```bash
git clone <repository-url>
cd MonsterC
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Usage

### Basic Workflow
1. **Launch Application** - Run `python main.py` and navigate to the provided URL
2. **Upload CSV Data** - Use the file upload interface to load your automation testing data
3. **Select Analysis Type** - Choose from multiple analysis workflows based on your needs
4. **Choose Visualization** - Select between AG Grid (classic) or Tabulator (enhanced) interfaces
5. **Interact with Results** - Expand/collapse groups, sort columns, and explore patterns

### Interface Options

#### Classic AG Grid View
- Traditional Excel-style pivot table
- Expandable test case groups
- Standard column sorting and filtering
- Heat map highlighting for maximum values

#### Enhanced Tabulator Interface
- Native collapsible groups with smooth animations
- Multi-level heat mapping system:
  - **Red**: Overall highest failure count
  - **Orange**: Highest per test case
  - **Yellow**: Highest for top 3 models
- One-click test case expansion (click anywhere on test case name)
- Auto-collapsed default view for clean first impression
- Grand Total column with horizontal summation

### Analysis Types

#### Automation High Failures
Analyzes automation testing failures with sophisticated business logic:
- Filters for specific automation operators (STN251_RED, STN252_RED, STN351_GRN, STN352_GRN)
- Applies FAILURE + ERROR with result_FAIL logic
- Preserves concatenated test case relationships
- Provides 2-level hierarchy: Test Case → Model

#### High Error Rates Analysis
Deep-dive error analysis with 3-level hierarchy:
- Model → Error Code → Error Message structure
- Comprehensive error pattern identification
- Detailed error message breakdown

## Key Features Deep Dive

### Heat Mapping System
The application features a sophisticated 3-level heat mapping system:

1. **Global Level (Red)**: Highlights the absolute highest failure count across all data
2. **Test Case Level (Orange)**: Highlights the highest station failure for each test case
3. **Model Level (Yellow)**: Highlights the highest station failure for the top 3 models in each category

### Concatenated Test Case Handling
Unlike traditional pivot tables that split comma-separated values, MonsterC preserves the integrity of concatenated test cases like "Camera Pictures,Camera Flash" as single analytical units, providing more accurate failure pattern analysis.

### Smart Column Ordering
Columns are automatically sorted by total failure count in descending order, ensuring the most critical stations appear on the left for immediate visibility and prioritization.

## Configuration

### Environment Variables
- `LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR)
- `PORT` - Override default port for web interface

### Data Format Requirements
CSV files should contain the following key columns:
- `Operator` - Test operator identifier
- `Overall status` - Test result status (SUCCESS, FAILURE, ERROR)
- `result_FAIL` - Failure reason(s), may contain comma-separated values
- `Station ID` - Testing station identifier
- `Model` - Device model being tested
- `error_code` - Numeric error identifier (for error analysis)
- `error_message` - Human-readable error description

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

Run specific test modules:
```bash
python tests/test_tabulator.py
python tests/test_pivot_service.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Architecture

The application follows a modular architecture pattern:

- **Presentation Layer** (`ui/`) - Gradio interface with multiple visualization options
- **Service Layer** (`services/`) - Business logic and data processing
- **Common Layer** (`common/`) - Shared utilities, logging, and configurations
- **Specialized Interfaces** - Dedicated Dash and Tabulator applications for advanced interactions

This structure enables:
- Easy maintenance and testing
- Clear separation of concerns
- Flexible interface options
- Scalable feature additions

## Performance Considerations

- **Lazy Loading** - Large datasets are processed efficiently with pagination
- **Client-Side Filtering** - Interactive filtering without server round-trips
- **Optimized Rendering** - Smart rendering for large pivot tables
- **Caching** - Temporary data caching for improved response times

## Browser Compatibility

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or feature requests, please open an issue on GitHub or contact the development team.
