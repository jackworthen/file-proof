# 🔍 FileProof - Data File Validator

**Your guardian against messy data files! 🛡️**

Validate, clean, and fix delimited files (CSV, TSV, pipe-delimited, and more) with an intuitive GUI that makes data validation actually enjoyable.

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Screenshots](#-screenshots)

</div>

---

## ✨ Features

### 🎯 Smart Validation
- **🔎 Auto-Detection**: Automatically detects file delimiters (comma, pipe, tab, semicolon, colon, asterisk)
- **📊 Column Consistency**: Ensures every row has the correct number of columns
- **🔢 Row Counting**: Tracks total, valid, and invalid rows with precision
- **⚠️ Detailed Error Reporting**: Get comprehensive reports with error types, locations, and descriptions

### 🧹 Data Cleaning
- **🚫 Duplicate Detection**: Identifies duplicate rows (enabled by default!)
- **✅ Export Clean Files**: Remove error records, duplicates, or both in one click
- **🔧 Fix & Save**: Smart save options to export cleaned data
- **📝 Error Extraction**: Export only the problematic records for review

### 🎨 User Interface
- **🖥️ Clean GUI**: Built with Tkinter for a smooth, native experience
- **📈 Real-time Progress**: Visual progress bar with color-coded results (green = pass, red = fail)
- **🔍 Interactive Error Navigator**: Browse, filter, and explore errors with ease
- **📋 Copy & Export**: One-click copy of error row numbers or export to CSV

### 📊 Reporting
- **📄 Comprehensive Reports**: Detailed validation summaries with statistics
- **💾 Multiple Export Formats**: Save reports as TXT or errors as CSV
- **🎯 Error Grouping**: Errors grouped by type for easier analysis
- **⏱️ Performance Metrics**: See validation time and file size statistics

---

## 🚀 Installation

### Prerequisites
- Python 3.7 or higher
- Tkinter (usually comes pre-installed with Python)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yjackworthen/fileproof.git
cd fileproof
```

2. **Run the application**
```bash
python fileproof.py
```

That's it! No external dependencies required. 🎉

---

## 📖 Usage

### Basic Workflow

1. **🎯 Select Your File**
   - Click "Browse" to choose your delimited file
   - Supports CSV, TSV, pipe-delimited, and custom delimiters

2. **🔍 Validate**
   - Click "🔍 Validate File" to start the validation process
   - Watch the progress bar as your file is analyzed
   - The "Check for duplicate rows" option is enabled by default

3. **📊 Review Results**
   - See validation results instantly with color-coded status
   - Browse errors in the interactive error navigator
   - Filter errors by type (Column Count, Quotes, Empty Rows, etc.)
   - Double-click any error to see full details

4. **🔧 Fix & Save**
   - Click "Fix & Save" to open the save options dialog
   - Choose from three powerful options:
     - ✅ **Export file without error records** - Get a clean file with errors removed
     - 🔄 **Remove duplicate records** - Eliminate duplicates (keeps one instance)
     - ⚠️ **Export error records** - Save only the problematic rows for analysis
   - Options 1 & 2 combine into a single clean file if both are selected!

5. **💾 Export Reports**
   - Click "Save Report" to export the full validation report
   - Use "📋 Copy Row Numbers" to copy error row numbers to clipboard
   - View detailed error information with "🔍 Show All Details"

### Supported File Types

| Format | Delimiter | Auto-Detected |
|--------|-----------|---------------|
| CSV | `,` | ✅ |
| TSV | `\t` | ✅ |
| Pipe | `\|` | ✅ |
| Semicolon | `;` | ✅ |
| Colon | `:` | ✅ |
| Asterisk | `*` | ✅ |

---

## 🛠️ Advanced Features

### Error Detection Types

| Error Type | Description |
|------------|-------------|
| `COLUMN_COUNT_MISMATCH` | Row has incorrect number of columns |
| `UNCLOSED_QUOTES` | Quoted field not properly closed |
| `EMPTY_ROW` | Row contains no data |
| `DELIMITER_IN_UNQUOTED_FIELD` | Unquoted field contains delimiter |
| `DUPLICATE_ROW` | Exact duplicate of another row |

### Performance
- ✅ Handles large files efficiently
- ✅ Chunked reading for memory efficiency
- ✅ Configurable error limits to prevent memory overflow
- ✅ Multi-threaded validation for responsive UI

---

## 🎓 Tips & Tricks

💡 **Pro Tips:**
- The duplicate checker is on by default - uncheck it if you want faster validation on large files
- Use the error type filter to focus on specific issues
- Double-click errors in the table to see the full row content
- Combine "Export file without errors" and "Remove duplicates" to get a fully cleaned file in one step
- Export error records separately to analyze patterns in your data issues

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- 🐛 Report bugs
- 💡 Suggest new features
- 🔧 Submit pull requests
- 📚 Improve documentation

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<div align="center">

 **⭐ If this project helped you, please consider giving it a star! ⭐**

*Developed by [Jack Worthen](https://github.com/jackworthen)*

</div>
