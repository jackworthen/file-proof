
<h1 align="center">
  🔍 File Proof
</h1>

<p align="center">
  <b>A powerful, user-friendly data file validator with a modern GUI</b>
</p>

<p align="center">
  <i>Validate CSV, TSV, JSON, and delimited files in seconds — catch errors before they catch you!</i>
</p>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 Smart Validation
- **Auto-detect delimiters** — CSV, TSV, pipe, semicolon, and more
- **JSON structure analysis** — validates schema consistency
- **Quote handling** — properly parses escaped and nested quotes
- **Column count verification** — catches misaligned rows instantly

</td>
<td width="50%">

### 🧭 Interactive Error Navigator
- **Sortable error table** — click headers to sort
- **Filter by error type** — focus on what matters
- **Search by row number** — jump to specific issues
- **Double-click for details** — see full row content

</td>
</tr>
<tr>
<td width="50%">

### 📊 Detailed Reports
- **Comprehensive summaries** — rows processed, valid, invalid
- **Grouped error analysis** — errors organized by type
- **Export to CSV** — import errors into Excel or other tools
- **Save text reports** — document validation results

</td>
<td width="50%">

### ⚡ Performance
- **Multi-threaded processing** — UI stays responsive
- **Large file support** — handles files of any size
- **Progress tracking** — visual progress bar with row count
- **Chunked reading** — memory-efficient file processing

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/fileproof.git
cd fileproof

# Run the application (no dependencies required!)
python fileproof_py.py
```

> 💡 **Note:** File Proof uses only Python standard library modules — no pip install needed!

### Usage

1. **Launch** the application
2. **Browse** to select your data file
3. **Click** the `🔍 Validate File` button
4. **Review** errors in the interactive navigator
5. **Export** results or save the report

---

## 🎨 Screenshots

```
┌─────────────────────────────────────────────────────────────────────┐
│  📁 File Proof                                              [─][□][×]│
├─────────────────────────────────────────────────────────────────────┤
│  ┌─ Select File ──────────────────────────────────────────────────┐ │
│  │ File: [data.csv                          ] [Browse] [🔍Validate]│ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ✓ PASSED - 10,000 rows validated in 0.45 seconds                  │
│  ████████████████████████████████████████████████████ 100%          │
│                                                                     │
│  ┌─ Error Navigator ──────────────────────────────────────────────┐ │
│  │ Filter: [All Errors ▼]  │  Showing 0 of 0 errors  │ Search: [ ]│ │
│  │─────────────────────────────────────────────────────────────────│ │
│  │  Row #  │  Error Type  │  Description  │  Preview              │ │
│  │─────────────────────────────────────────────────────────────────│ │
│  │                    ✨ No errors found!                          │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                      [Save Report] [Clear]          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Supported File Types

| Format | Extensions | Auto-Detect |
|--------|------------|-------------|
| 🗃️ **CSV** | `.csv` | ✅ Delimiter auto-detected |
| 📊 **TSV** | `.tsv`, `.txt` | ✅ Tab delimiter |
| 📑 **Pipe-delimited** | `.txt`, `.dat` | ✅ Pipe `\|` delimiter |
| 🔣 **Custom delimited** | `.*` | ✅ `;` `:` `*` and more |
| 📦 **JSON** | `.json` | ✅ Structure validation |

---

## 🔎 Error Types Detected

| Error Type | Description |
|------------|-------------|
| `COLUMN_COUNT_MISMATCH` | Row has different number of columns than header |
| `UNCLOSED_QUOTES` | Quotation marks not properly closed |
| `JSON_PARSE_ERROR` | Invalid JSON syntax |
| `TYPE_MISMATCH` | Inconsistent data types in JSON arrays |
| `KEY_MISMATCH` | Missing or extra keys in JSON objects |
| `EMPTY_FILE` | File contains no data |
| `FILE_READ_ERROR` | Unable to read file |

---

## 🛠️ Technical Details

### Architecture

```
fileproof_py.py
├── ValidationReport      # Stores results & generates reports
├── DelimitedFileValidator  # CSV/TSV/delimited file validation
├── JSONValidator         # JSON file validation
└── DataValidatorApp      # Tkinter GUI application
```

### Key Algorithms

- **Delimiter Detection**: Analyzes first 20 lines, counts delimiters outside quotes, selects most consistent delimiter
- **Quote-Aware Parsing**: Handles single/double quotes, escaped quotes, and nested delimiters
- **Streaming Validation**: Processes files line-by-line for memory efficiency

---

## 📄 Sample Validation Report

```
================================================================================
DATA FILE VALIDATION REPORT
================================================================================

File: sales_data.csv
File Size: 15.23 MB
File Type: Delimited (delimiter: ,)
Validation Time: 2.34 seconds
Timestamp: 2025-01-15 14:30:22

--------------------------------------------------------------------------------
VALIDATION RESULT: ✗ FAILED
--------------------------------------------------------------------------------

Total Rows Processed: 150,000
Valid Rows: 149,847
Invalid Rows: 153
Delimiter: ',' (detected)
Expected Columns: 12

================================================================================
ERRORS (153 found)
================================================================================

COLUMN_COUNT_MISMATCH (150 occurrences):
--------------------------------------------------------------------------------
  Row 1042: Expected 12 columns, found 11
  Row 2891: Expected 12 columns, found 13
  ...

UNCLOSED_QUOTES (3 occurrences):
--------------------------------------------------------------------------------
  Row 50123: Unclosed double quotes detected
  ...

================================================================================
END OF REPORT
================================================================================
```

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

- 🐛 Report bugs
- 💡 Suggest features  
- 🔧 Submit pull requests

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

**⭐ If this project helped you, please consider giving it a star! ⭐**

*Developed by [Jack Worthen](https://github.com/jackworthen)*