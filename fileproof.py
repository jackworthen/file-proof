import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import csv
import os
import threading
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import re
import hashlib
import webbrowser

class ValidationReport:
    """Stores validation results and generates detailed reports."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.file_size = 0
        self.start_time = None
        self.end_time = None
        self.total_rows = 0
        self.valid_rows = 0
        self.invalid_rows = 0
        self.file_type = ""
        self.delimiter = ""
        self.expected_columns = 0
        self.errors = []
        self.warnings = []
        self.duplicates = []
        self.passed = False
        self.cancelled = False
        
    def add_error(self, row_num: int, error_type: str, description: str, row_content: str = ""):
        """Add an error to the report."""
        self.errors.append({
            'row': row_num,
            'type': error_type,
            'description': description,
            'content': row_content[:500] if row_content else ""  # Store first 500 chars
        })
        
    def add_warning(self, row_num: int, warning_type: str, description: str):
        """Add a warning to the report."""
        self.warnings.append({
            'row': row_num,
            'type': warning_type,
            'description': description
        })
    
    def add_duplicate(self, row_num: int, description: str, row_content: str = ""):
        """Add a duplicate row to the report."""
        self.duplicates.append({
            'row': row_num,
            'type': 'DUPLICATE_ROW',
            'description': description,
            'content': row_content[:500] if row_content else ""
        })
        
        
    def generate_report(self) -> str:
        """Generate a formatted text report."""
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        
        report = []
        report.append("=" * 80)
        report.append("DATA FILE VALIDATION REPORT")
        report.append("=" * 80)
        report.append(f"\nFile: {self.filename}")
        report.append(f"File Size: {self.file_size / (1024*1024):.2f} MB")
        report.append(f"File Type: {self.file_type}")
        report.append(f"Validation Time: {duration:.2f} seconds")
        report.append(f"Timestamp: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        
        # Show cancellation or pass/fail status
        if self.cancelled:
            report.append("-" * 80)
            report.append("⚠ VALIDATION CANCELLED BY USER")
            report.append("-" * 80)
            report.append(f"\nPartial Results (validated {self.total_rows:,} rows before cancellation)")
        else:
            report.append("-" * 80)
            report.append("VALIDATION RESULT: " + ("✓ PASSED" if self.passed else "✗ FAILED"))
            report.append("-" * 80)
        
        report.append(f"\nTotal Rows Processed: {self.total_rows:,}")
        report.append(f"Valid Rows: {self.valid_rows:,}")
        report.append(f"Invalid Rows: {self.invalid_rows:,}")
        
        if self.delimiter:
            report.append(f"Delimiter: '{self.delimiter}' (detected)")
        if self.expected_columns > 0:
            report.append(f"Expected Columns: {self.expected_columns}")
        
        if self.errors:
            report.append(f"\n" + "=" * 80)
            report.append(f"ERRORS ({len(self.errors)} found)")
            report.append("=" * 80)
            
            # Group errors by type
            error_groups = defaultdict(list)
            for error in self.errors:
                error_groups[error['type']].append(error)
            
            for error_type, errors in error_groups.items():
                report.append(f"\n{error_type} ({len(errors)} occurrences):")
                report.append("-" * 80)
                for error in errors[:10]:  # Show first 10 of each type
                    report.append(f"  Row {error['row']}: {error['description']}")
                if len(errors) > 10:
                    report.append(f"  ... and {len(errors) - 10} more similar errors")
        
        if self.warnings:
            report.append(f"\n" + "=" * 80)
            report.append(f"WARNINGS ({len(self.warnings)} found)")
            report.append("=" * 80)
            
            # Group warnings by type
            warning_groups = defaultdict(list)
            for warning in self.warnings:
                warning_groups[warning['type']].append(warning)
            
            for warning_type, warnings in warning_groups.items():
                report.append(f"\n{warning_type} ({len(warnings)} occurrences):")
                report.append("-" * 80)
                for warning in warnings[:10]:
                    report.append(f"  Row {warning['row']}: {warning['description']}")
                if len(warnings) > 10:
                    report.append(f"  ... and {len(warnings) - 10} more similar warnings")
        
        if self.duplicates:
            report.append(f"\n" + "=" * 80)
            report.append(f"DUPLICATES ({len(self.duplicates)} found)")
            report.append("=" * 80)
            report.append("\nNote: Duplicates do not cause validation to fail.\n")
            
            # Show first 20 duplicates
            for duplicate in self.duplicates[:20]:
                report.append(f"  Row {duplicate['row']}: {duplicate['description']}")
            if len(self.duplicates) > 20:
                report.append(f"  ... and {len(self.duplicates) - 20} more duplicates")
        
        
        if not self.errors and not self.warnings and not self.cancelled:
            report.append("\n✓ No errors or warnings found. File is valid!")
        elif self.cancelled and not self.errors and not self.warnings:
            report.append("\n✓ No errors or warnings found in scanned portion.")
        
        report.append("\n" + "=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def export_errors_csv(self, output_path: str):
        """Export errors to a CSV file for easy analysis."""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Row Number', 'Error Type', 'Description', 'Row Content Preview'])
            for error in self.errors:
                content_preview = error.get('content', '')[:200]  # First 200 chars
                writer.writerow([
                    error['row'], 
                    error['type'], 
                    error['description'], 
                    content_preview
                ])

class DelimitedFileValidator:
    """Validates delimited files (CSV, TSV, pipe-delimited, etc.)"""
    
    COMMON_DELIMITERS = [',', '|', '\t', '*', ';', ':']
    
    def __init__(self, filepath: str, delimiter: Optional[str] = None, 
                 max_errors: int = 1000, chunk_size: int = 8192, check_duplicates: bool = False, cancel_event: Optional[threading.Event] = None):
        self.filepath = filepath
        self.delimiter = delimiter
        self.max_errors = max_errors
        self.chunk_size = chunk_size
        self.check_duplicates = check_duplicates
        self.report = ValidationReport(os.path.basename(filepath))
        self.cancel_event = cancel_event
        
    def detect_delimiter(self, sample_lines: List[str]) -> str:
        """Detect the delimiter used in the file."""
        if self.delimiter:
            return self.delimiter
            
        delimiter_counts = {delim: [] for delim in self.COMMON_DELIMITERS}
        
        for line in sample_lines[:20]:  # Use first 20 lines
            line = line.strip()
            if not line:
                continue
                
            for delim in self.COMMON_DELIMITERS:
                # Count delimiters outside of quotes
                count = self._count_delimiter_outside_quotes(line, delim)
                delimiter_counts[delim].append(count)
        
        # Find delimiter with most consistent count (and count > 0)
        best_delimiter = None
        best_score = -1
        
        for delim, counts in delimiter_counts.items():
            if not counts or all(c == 0 for c in counts):
                continue
            
            # Calculate consistency score
            unique_counts = set(counts)
            if len(unique_counts) == 1 and counts[0] > 0:
                # Perfect consistency - this is ideal
                avg_count = counts[0]
                consistency_score = avg_count * 100  # Heavy weight for perfect consistency
                
                if consistency_score > best_score:
                    best_score = consistency_score
                    best_delimiter = delim
            elif len(unique_counts) <= 3:  # Allow some variation
                # Good enough consistency
                avg_count = sum(counts) / len(counts)
                # Calculate variance penalty
                variance = sum((c - avg_count) ** 2 for c in counts) / len(counts)
                consistency_score = avg_count * (1 / (1 + variance))
                
                if consistency_score > best_score and avg_count > 0:
                    best_score = consistency_score
                    best_delimiter = delim
        
        # If still no delimiter found, default to comma
        return best_delimiter if best_delimiter else ','
    
    def _count_delimiter_outside_quotes(self, line: str, delimiter: str) -> int:
        """Count delimiters that are outside quoted sections."""
        count = 0
        in_quotes = False
        quote_char = None
        
        for i, char in enumerate(line):
            if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            elif char == delimiter and not in_quotes:
                count += 1
        
        return count
    
    def _parse_line_with_quotes(self, line: str, delimiter: str) -> List[str]:
        """Parse a line respecting quoted sections."""
        fields = []
        current_field = []
        in_quotes = False
        quote_char = None
        
        i = 0
        while i < len(line):
            char = line[i]
            
            if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    # Check for escaped quote (double quote)
                    if i + 1 < len(line) and line[i + 1] == quote_char:
                        current_field.append(char)
                        i += 1
                    else:
                        in_quotes = False
                        quote_char = None
                else:
                    current_field.append(char)
            elif char == delimiter and not in_quotes:
                fields.append(''.join(current_field))
                current_field = []
            else:
                current_field.append(char)
            
            i += 1
        
        fields.append(''.join(current_field))
        return fields
    
    def validate(self, progress_callback=None) -> ValidationReport:
        """Validate the delimited file."""
        self.report.start_time = datetime.now()
        self.report.file_size = os.path.getsize(self.filepath)
        
        try:
            with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
                # Read sample for delimiter detection
                sample_lines = []
                for _ in range(50):
                    line = f.readline()
                    if not line:
                        break
                    sample_lines.append(line)
                
                if not sample_lines:
                    self.report.add_error(0, "EMPTY_FILE", "File is empty")
                    self.report.end_time = datetime.now()
                    return self.report
                
                # Detect delimiter
                self.delimiter = self.detect_delimiter(sample_lines)
                self.report.delimiter = repr(self.delimiter).strip("'")
                
                # Determine expected columns from header
                header_line = sample_lines[0].strip()
                expected_columns = self._count_delimiter_outside_quotes(header_line, self.delimiter) + 1
                self.report.expected_columns = expected_columns
                
                # Reset file pointer
                f.seek(0)
                
                row_num = 0
                bytes_processed = 0
                row_hashes = {}  # For duplicate detection: hash -> list of (row_num, line)
                
                for line in f:
                    row_num += 1
                    bytes_processed += len(line.encode('utf-8'))
                    
                    # Check for cancellation
                    if self.cancel_event and self.cancel_event.is_set():
                        self.report.cancelled = True
                        break
                    
                    if progress_callback and row_num % 1000 == 0:
                        progress = (bytes_processed / self.report.file_size) * 100
                        progress_callback(progress, row_num, len(self.report.errors))
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    self.report.total_rows += 1
                    
                    # Collect row hash for duplicate detection
                    if self.check_duplicates:
                        row_hash = hashlib.md5(line.encode('utf-8')).hexdigest()
                        if row_hash not in row_hashes:
                            row_hashes[row_hash] = []
                        row_hashes[row_hash].append((row_num, line))
                    
                    # Count delimiters
                    delimiter_count = self._count_delimiter_outside_quotes(line, self.delimiter)
                    actual_columns = delimiter_count + 1
                    
                    if actual_columns != expected_columns:
                        self.report.invalid_rows += 1
                        if len(self.report.errors) < self.max_errors:
                            self.report.add_error(
                                row_num,
                                "COLUMN_COUNT_MISMATCH",
                                f"Expected {expected_columns} columns, found {actual_columns}",
                                line
                            )
                    else:
                        # Parse the line to check for unescaped delimiters in data
                        fields = self._parse_line_with_quotes(line, self.delimiter)
                        
                        # Check for unclosed quotes
                        quote_count_double = line.count('"') - line.count('\\"')
                        quote_count_single = line.count("'") - line.count("\\'")
                        
                        if quote_count_double % 2 != 0:
                            self.report.invalid_rows += 1
                            if len(self.report.errors) < self.max_errors:
                                self.report.add_error(
                                    row_num,
                                    "UNCLOSED_QUOTES",
                                    "Unclosed double quotes detected",
                                    line
                                )
                        elif quote_count_single % 2 != 0:
                            if len(self.report.warnings) < self.max_errors:
                                self.report.add_warning(
                                    row_num,
                                    "UNCLOSED_QUOTES",
                                    "Unclosed single quotes detected"
                                )
                        else:
                            self.report.valid_rows += 1
                


                # Check for duplicates
                if self.check_duplicates:
                    for row_hash, occurrences in row_hashes.items():
                        if len(occurrences) > 1:
                            # All rows with this hash are duplicates
                            duplicate_rows = [str(rnum) for rnum, _ in occurrences]
                            for rnum, line_content in occurrences:
                                other_rows = ', '.join([r for r in duplicate_rows if r != str(rnum)])
                                self.report.add_duplicate(
                                    rnum,
                                    f"Exact duplicate of row(s): {other_rows}",
                                    line_content
                                )
                                
                                if len(self.report.duplicates) >= self.max_errors:
                                    break
                        
                        if len(self.report.duplicates) >= self.max_errors:
                            break
                
                
                self.report.file_type = f"Delimited (delimiter: {repr(self.delimiter).strip(chr(39))})"
                
        except Exception as e:
            self.report.add_error(0, "FILE_READ_ERROR", f"Error reading file: {str(e)}")
        
        self.report.end_time = datetime.now()
        self.report.passed = self.report.invalid_rows == 0 and len(self.report.errors) == 0
        
        return self.report

class JSONValidator:
    """Validates JSON files."""
    
    def __init__(self, filepath: str, max_errors: int = 1000, cancel_event: Optional[threading.Event] = None):
        self.filepath = filepath
        self.max_errors = max_errors
        self.report = ValidationReport(os.path.basename(filepath))
        self.cancel_event = cancel_event
        
    def validate(self, progress_callback=None) -> ValidationReport:
        """Validate the JSON file."""
        self.report.start_time = datetime.now()
        self.report.file_size = os.path.getsize(self.filepath)
        self.report.file_type = "JSON"
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if progress_callback:
                    progress_callback(50, 0, len(self.report.errors))
                
                try:
                    data = json.loads(content)
                    
                    # Analyze structure
                    if isinstance(data, list):
                        self.report.total_rows = len(data)
                        self.report.valid_rows = len(data)
                        
                        # Check for consistent structure
                        if data and isinstance(data[0], dict):
                            expected_keys = set(data[0].keys())
                            self.report.expected_columns = len(expected_keys)
                            
                            for idx, item in enumerate(data[1:], start=2):
                                # Check for cancellation
                                if self.cancel_event and self.cancel_event.is_set():
                                    self.report.cancelled = True
                                    break
                                    
                                if not isinstance(item, dict):
                                    self.report.invalid_rows += 1
                                    self.report.valid_rows -= 1
                                    if len(self.report.errors) < self.max_errors:
                                        self.report.add_error(
                                            idx,
                                            "TYPE_MISMATCH",
                                            f"Expected dict, got {type(item).__name__}"
                                        )
                                elif set(item.keys()) != expected_keys:
                                    if len(self.report.warnings) < self.max_errors:
                                        missing = expected_keys - set(item.keys())
                                        extra = set(item.keys()) - expected_keys
                                        msg = []
                                        if missing:
                                            msg.append(f"Missing keys: {missing}")
                                        if extra:
                                            msg.append(f"Extra keys: {extra}")
                                        self.report.add_warning(
                                            idx,
                                            "KEY_MISMATCH",
                                            "; ".join(msg)
                                        )
                    
                    elif isinstance(data, dict):
                        self.report.total_rows = 1
                        self.report.valid_rows = 1
                        self.report.expected_columns = len(data.keys())
                    
                    else:
                        self.report.total_rows = 1
                        self.report.valid_rows = 1
                    
                    if progress_callback:
                        progress_callback(100, self.report.total_rows, len(self.report.errors))
                    
                except json.JSONDecodeError as e:
                    self.report.add_error(e.lineno, "JSON_PARSE_ERROR", 
                                        f"Invalid JSON: {str(e)}")
                    self.report.invalid_rows = 1
                    
        except Exception as e:
            self.report.add_error(0, "FILE_READ_ERROR", f"Error reading file: {str(e)}")
        
        self.report.end_time = datetime.now()
        self.report.passed = self.report.invalid_rows == 0 and len(self.report.errors) == 0
        
        return self.report

class DataValidatorApp:
    """Main application class with tkinter UI."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("File Proof")
        self.root.geometry("960x705")  # Increased width by 20% (800 * 1.2 = 960)
        
        # Set style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colorful progress bar
        style.configure("Colorful.Horizontal.TProgressbar",
                       troughcolor='#E0E0E0',
                       bordercolor='#BDBDBD',
                       background='#4CAF50',  # Green
                       lightcolor='#81C784',
                       darkcolor='#388E3C')
        
        # Create accent button style with lighter blue
        style.configure('Accent.TButton',
                       background='#90CAF9',  # Light blue
                       foreground='#000000',
                       borderwidth=1,
                       focuscolor='none',
                       font=('Helvetica', 10, 'bold'))
        style.map('Accent.TButton',
                 background=[('active', '#64B5F6')])
        
        # Variables
        self.filepath = tk.StringVar()
        self.validation_running = False
        self.current_report = None
        self.progress_color_state = 0
        self.all_errors = []  # For error navigator
        self.all_duplicates = []  # For duplicate tracking
        self.check_duplicates = tk.BooleanVar(value=True)
        self.cancel_event = threading.Event()  # For cancelling validation
        self.validation_completed = False  # Track if full validation completed (not cancelled)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
        # Create menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Create Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.open_documentation)
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="Select File", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="File:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(file_frame, textvariable=self.filepath, width=60).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(file_frame, text="Browse", command=self.browse_file).grid(
            row=0, column=2, sticky=tk.E, padx=(0, 10))
        
        # Validate button in the same frame
        self.validate_btn = ttk.Button(file_frame, text="🔍 Validate File", 
                                       command=self.start_validation,
                                       style='Accent.TButton')
        self.validate_btn.grid(row=0, column=3, sticky=tk.E)
        
        # Cancel button
        self.cancel_btn = ttk.Button(file_frame, text="❌ Cancel", 
                                     command=self.cancel_validation,
                                     state='disabled')
        self.cancel_btn.grid(row=0, column=4, sticky=tk.E, padx=(5, 0))
        
        # Duplicate detection checkbox
        ttk.Checkbutton(file_frame, text="Check for duplicate rows", 
                       variable=self.check_duplicates).grid(row=1, column=0, columnspan=4, 
                                                            sticky=tk.W, pady=(5, 0))
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_label = ttk.Label(progress_frame, text="", font=('Helvetica', 9))
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(progress_frame, 
                                           mode='determinate', 
                                           length=400,
                                           style="Colorful.Horizontal.TProgressbar")
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Results frame - Error Navigator
        results_frame = ttk.LabelFrame(main_frame, text="Error Navigator", padding="10")
        results_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        self.setup_error_navigator(results_frame)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, sticky=tk.E)
        
        ttk.Button(buttons_frame, text="Save Report", 
                  command=self.save_report).grid(row=0, column=0, padx=5)
        ttk.Button(buttons_frame, text="Clear", 
                  command=self.clear_results).grid(row=0, column=1, padx=5)
        self.fix_save_btn = ttk.Button(buttons_frame, text="Fix & Save", 
                  command=self.show_save_dialog, state='disabled')
        self.fix_save_btn.grid(row=0, column=2, padx=5)
    
    def setup_error_navigator(self, parent_frame):
        """Setup the interactive error navigation panel."""
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.rowconfigure(1, weight=1)
        
        # Filter and controls frame
        filter_frame = ttk.Frame(parent_frame, padding="5")
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        filter_frame.columnconfigure(2, weight=1)
        
        # Error type filter
        ttk.Label(filter_frame, text="Filter by Type:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.error_filter = tk.StringVar(value="All Errors")
        self.filter_combo = ttk.Combobox(filter_frame, textvariable=self.error_filter, 
                                         state='readonly', width=25)
        self.filter_combo['values'] = ['All Errors']
        self.filter_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self.apply_error_filter())
        
        # Stats label
        self.error_stats_label = ttk.Label(filter_frame, text="No errors", 
                                          font=('Helvetica', 9, 'italic'))
        self.error_stats_label.grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        
        # Duplicate stats label
        self.duplicate_stats_label = ttk.Label(filter_frame, text="", 
                                              font=('Helvetica', 9, 'italic'))
        self.duplicate_stats_label.grid(row=0, column=2, sticky=tk.W, padx=(130, 0))
        
        # Search frame
        search_frame = ttk.Frame(filter_frame)
        search_frame.grid(row=0, column=3, sticky=tk.E, padx=(20, 0))
        
        ttk.Label(search_frame, text="Search Row:").grid(row=0, column=0, padx=(0, 5))
        self.row_search = tk.StringVar()
        self.row_search_entry = ttk.Entry(search_frame, textvariable=self.row_search, width=10)
        self.row_search_entry.grid(row=0, column=1, padx=(0, 5))
        ttk.Button(search_frame, text="Find", command=self.search_error_row).grid(row=0, column=2)
        
        # Error table frame
        table_frame = ttk.Frame(parent_frame)
        table_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")
        
        # Treeview for error table
        self.error_table = ttk.Treeview(table_frame, 
                                        columns=('row', 'type', 'description', 'preview'),
                                        show='headings',
                                        yscrollcommand=vsb.set,
                                        xscrollcommand=hsb.set,
                                        height=15)
        
        vsb.config(command=self.error_table.yview)
        hsb.config(command=self.error_table.xview)
        
        # Configure columns
        self.error_table.heading('row', text='Row #', command=lambda: self.sort_errors('row'))
        self.error_table.heading('type', text='Error Type', command=lambda: self.sort_errors('type'))
        self.error_table.heading('description', text='Description', command=lambda: self.sort_errors('description'))
        self.error_table.heading('preview', text='Row Content Preview', command=lambda: self.sort_errors('preview'))
        
        self.error_table.column('row', width=80, anchor='center')
        self.error_table.column('type', width=180)
        self.error_table.column('description', width=250)
        self.error_table.column('preview', width=300)
        
        # Grid layout
        self.error_table.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Bind double-click to show detail
        self.error_table.bind('<Double-1>', self.show_error_detail)
        
        # Action buttons frame
        action_frame = ttk.Frame(parent_frame, padding="5")
        action_frame.grid(row=2, column=0, sticky=tk.E, pady=(10, 0))
        
        ttk.Button(action_frame, text="📋 Copy Row Numbers", 
                  command=self.copy_error_rows).grid(row=0, column=0, padx=5)
        ttk.Button(action_frame, text="🔍 Show All Details", 
                  command=self.show_all_error_details).grid(row=0, column=1, padx=5)
        
        # Initialize sort state
        self.sort_column = 'row'
        self.sort_reverse = False
        
    def browse_file(self):
        """Open file browser dialog."""
        filename = filedialog.askopenfilename(
            title="Select a data file",
            filetypes=[
                ("All Supported", "*.csv *.txt *.dat *.json *.tsv"),
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
                ("Data files", "*.dat"),
                ("JSON files", "*.json"),
                ("TSV files", "*.tsv"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.filepath.set(filename)
    
    def start_validation(self):
        """Start the validation process in a separate thread."""
        if not self.filepath.get():
            messagebox.showerror("Error", "Please select a file to validate")
            return
        
        if not os.path.exists(self.filepath.get()):
            messagebox.showerror("Error", "Selected file does not exist")
            return
        
        if self.validation_running:
            messagebox.showwarning("Warning", "Validation is already running")
            return
        
        self.validation_running = True
        self.validate_btn.config(state='disabled')
        self.cancel_event.clear()  # Clear any previous cancel signal
        self.cancel_btn.config(state='normal')  # Enable cancel button
        self.validation_completed = False  # Reset completion flag
        self.fix_save_btn.config(state='disabled')  # Disable Fix & Save until validation completes
        self.clear_results()
        
        # Run validation in separate thread
        thread = threading.Thread(target=self.run_validation)
        thread.daemon = True
        thread.start()
    
    def cancel_validation(self):
        """Cancel the currently running validation."""
        if self.validation_running:
            self.cancel_event.set()  # Signal cancellation
            self.cancel_btn.config(state='disabled')
    
    def run_validation(self):
        """Run the validation process."""
        filepath = self.filepath.get()
        
        # Store the filepath for save operations
        self.last_validated_file = filepath
        
        # Always auto-detect file type and delimiter
        filetype = "auto"
        delimiter = None
        
        # Reset progress bar to starting color
        style = ttk.Style()
        style.configure("Colorful.Horizontal.TProgressbar",
                      background='#2196F3',
                      lightcolor='#64B5F6',
                      darkcolor='#1976D2')
        
        try:
            # Determine file type
            if filetype == "auto":
                ext = os.path.splitext(filepath)[1].lower()
                if ext == '.json':
                    filetype = 'json'
                else:
                    filetype = 'delimited'
            
            # Create appropriate validator
            if filetype == 'json':
                validator = JSONValidator(filepath, cancel_event=self.cancel_event)
            else:
                validator = DelimitedFileValidator(filepath, delimiter=delimiter, check_duplicates=self.check_duplicates.get(), cancel_event=self.cancel_event)
            
            # Run validation with progress updates
            def progress_callback(progress, rows, errors):
                self.root.after(0, self.update_progress, progress, rows, errors)
            
            report = validator.validate(progress_callback)
            self.current_report = report
            
            # Display results
            self.root.after(0, self.display_results, report)
            
        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error", 
                          f"Validation failed: {str(e)}")
        finally:
            self.validation_running = False
            self.root.after(0, lambda: self.validate_btn.config(state='normal'))
            self.root.after(0, lambda: self.cancel_btn.config(state='disabled'))
    
    def update_progress(self, progress, rows, errors=0):
        """Update the progress bar and label - stays blue while processing."""
        self.progress_bar['value'] = progress
        self.progress_label.config(text=f"Processing... {progress:.1f}% ({rows:,} rows)")
        
        # Update error count display
        if errors > 0:
            self.error_stats_label.config(text=f"{errors:,} error(s) detected")
        else:
            self.error_stats_label.config(text="No errors detected yet")
        
        # Keep progress bar blue during processing
        # Color will change to green/red only when validation completes
        
        self.root.update_idletasks()
    
    def display_results(self, report: ValidationReport):
        """Display validation results in the error navigator."""
        # Re-enable validate button and disable cancel button
        self.validation_running = False
        self.validate_btn.config(state='normal')
        self.cancel_btn.config(state='disabled')
        
        # Enable Fix & Save button only if validation completed AND there are errors or duplicates
        if not report.cancelled:
            self.validation_completed = True
            # Only enable Fix & Save if there are errors or duplicates to fix
            has_errors = len(report.errors) > 0
            has_duplicates = len(report.duplicates) > 0
            if has_errors or has_duplicates:
                self.fix_save_btn.config(state='normal')
            else:
                self.fix_save_btn.config(state='disabled')
        else:
            self.validation_completed = False
            self.fix_save_btn.config(state='disabled')
        
        # Color code the result with enhanced styling
        if report.cancelled:
            self.progress_label.config(
                text=f"⚠ Validation Cancelled - {report.total_rows:,} rows scanned, {len(report.errors)} error(s) found", 
                foreground='#FF9800',
                font=('Helvetica', 10, 'bold')
            )
            # Set progress bar to orange for cancellation
            style = ttk.Style()
            style.configure("Colorful.Horizontal.TProgressbar",
                          background='#FF9800',
                          lightcolor='#FFB74D',
                          darkcolor='#F57C00')
        elif report.passed:
            self.progress_label.config(
                text="✓ Validation Passed - File is Valid!", 
                foreground='#4CAF50',
                font=('Helvetica', 10, 'bold')
            )
            # Set progress bar to green for success
            style = ttk.Style()
            style.configure("Colorful.Horizontal.TProgressbar",
                          background='#4CAF50',
                          lightcolor='#81C784',
                          darkcolor='#388E3C')
            self.progress_bar['value'] = 100
        else:
            self.progress_label.config(
                text=f"✗ Validation Failed - {len(report.errors)} Error(s) Found", 
                foreground='#F44336',
                font=('Helvetica', 10, 'bold')
            )
            # Set progress bar to red for failure
            style = ttk.Style()
            style.configure("Colorful.Horizontal.TProgressbar",
                          background='#F44336',
                          lightcolor='#E57373',
                          darkcolor='#D32F2F')
            self.progress_bar['value'] = 100
        
        # Populate error navigator
        self.populate_error_navigator(report)
    
    def populate_error_navigator(self, report: ValidationReport):
        """Populate the error navigator table with errors from the report."""
        # Clear existing items
        for item in self.error_table.get_children():
            self.error_table.delete(item)
        
        # Store errors for filtering/sorting
        self.all_errors = report.errors
        self.all_duplicates = report.duplicates
        
        # Get unique error types for filter
        error_types = ['All Errors']
        if self.all_errors:
            unique_types = sorted(set(error['type'] for error in self.all_errors))
            error_types.extend(unique_types)
        if self.all_duplicates:
            error_types.append('DUPLICATE_ROW')
        
        self.filter_combo['values'] = error_types
        self.error_filter.set('All Errors')
        
        # Populate table
        for error in self.all_errors:
            preview = error.get('content', '')[:100]  # First 100 chars
            if len(error.get('content', '')) > 100:
                preview += '...'
            
            self.error_table.insert('', 'end', values=(
                error['row'],
                error['type'],
                error['description'],
                preview
            ))
        
        # Add duplicates to table
        for duplicate in self.all_duplicates:
            preview = duplicate.get('content', '')[:100]
            if len(duplicate.get('content', '')) > 100:
                preview += '...'
            
            self.error_table.insert('', 'end', values=(
                duplicate['row'],
                duplicate['type'],
                duplicate['description'],
                preview
            ))
        
        
        # Update stats
        self.update_error_stats()
        self.update_duplicate_stats()
    
    def update_error_stats(self):
        """Update the error statistics label."""
        total_errors = len(self.all_errors) if hasattr(self, 'all_errors') else 0
        
        if total_errors == 0:
            self.error_stats_label.config(text="No errors found")
        else:
            self.error_stats_label.config(text=f"Errors: {total_errors}")
    
    
    
    def update_duplicate_stats(self):
        """Update the duplicate statistics label."""
        # Only show duplicate stats if duplicate checking is enabled
        if not self.check_duplicates.get():
            self.duplicate_stats_label.config(text="")
            return
        
        total_duplicates = len(self.all_duplicates) if hasattr(self, 'all_duplicates') else 0
        
        if total_duplicates == 0:
            self.duplicate_stats_label.config(text="No duplicates")
        else:
            self.duplicate_stats_label.config(text=f"Duplicates: {total_duplicates}")
    
    def apply_error_filter(self):
        """Filter errors based on selected type."""
        if not hasattr(self, 'all_errors'):
            return
        
        # Clear table
        for item in self.error_table.get_children():
            self.error_table.delete(item)
        
        filter_type = self.error_filter.get()
        
        # Repopulate with filtered errors
        for error in self.all_errors:
            if filter_type == 'All Errors' or error['type'] == filter_type:
                preview = error.get('content', '')[:100]
                if len(error.get('content', '')) > 100:
                    preview += '...'
                
                self.error_table.insert('', 'end', values=(
                    error['row'],
                    error['type'],
                    error['description'],
                    preview
                ))
        
        # Also add filtered duplicates
        if hasattr(self, 'all_duplicates'):
            for duplicate in self.all_duplicates:
                if filter_type == 'All Errors' or duplicate['type'] == filter_type:
                    preview = duplicate.get('content', '')[:100]
                    if len(duplicate.get('content', '')) > 100:
                        preview += '...'
                    
                    self.error_table.insert('', 'end', values=(
                        duplicate['row'],
                        duplicate['type'],
                        duplicate['description'],
                        preview
                    ))
        
        
        self.update_error_stats()
    
    def search_error_row(self):
        """Search for a specific row number in the error table."""
        search_row = self.row_search.get().strip()
        
        if not search_row:
            messagebox.showwarning("Search", "Please enter a row number")
            return
        
        try:
            row_num = int(search_row)
        except ValueError:
            messagebox.showerror("Search", "Please enter a valid row number")
            return
        
        # Search in table
        found = False
        for item in self.error_table.get_children():
            values = self.error_table.item(item)['values']
            if values[0] == row_num:
                # Select and show the item
                self.error_table.selection_set(item)
                self.error_table.see(item)
                self.error_table.focus(item)
                found = True
                break
        
        if not found:
            messagebox.showinfo("Search", f"Row {row_num} not found in error list")
    
    def sort_errors(self, column):
        """Sort error table by column."""
        # Toggle sort direction if same column
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        # Get all items
        items = [(self.error_table.item(item)['values'], item) 
                 for item in self.error_table.get_children()]
        
        # Determine column index
        col_index = {'row': 0, 'type': 1, 'description': 2, 'preview': 3}[column]
        
        # Sort items
        if column == 'row':
            items.sort(key=lambda x: int(x[0][col_index]), reverse=self.sort_reverse)
        else:
            items.sort(key=lambda x: str(x[0][col_index]).lower(), reverse=self.sort_reverse)
        
        # Reinsert items in sorted order
        for index, (values, item) in enumerate(items):
            self.error_table.move(item, '', index)
    
    def show_error_detail(self, event):
        """Show detailed information for selected error or duplicate (double-click)."""
        selection = self.error_table.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.error_table.item(item)['values']
        
        # Find the full error or duplicate data
        row_num = values[0]
        error_type = values[1]
        data = None
        is_duplicate = False
        
        # First check in errors
        for error in self.all_errors:
            if error['row'] == row_num and error['type'] == error_type:
                data = error
                break
        
        # If not found in errors, check duplicates
        if not data:
            for duplicate in self.all_duplicates:
                if duplicate['row'] == row_num:
                    data = duplicate
                    is_duplicate = True
                    break
        
        if not data:
            return
        
        # Create detail window
        detail_window = tk.Toplevel(self.root)
        window_title = f"Duplicate Detail - Row {row_num}" if is_duplicate else f"Error Detail - Row {row_num}"
        detail_window.title(window_title)
        detail_window.geometry("700x400")
        
        # Detail frame
        detail_frame = ttk.Frame(detail_window, padding="10")
        detail_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        detail_window.columnconfigure(0, weight=1)
        detail_window.rowconfigure(0, weight=1)
        detail_frame.columnconfigure(1, weight=1)
        detail_frame.rowconfigure(4, weight=1)
        
        # Information labels
        ttk.Label(detail_frame, text="Row Number:", font=('Helvetica', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(detail_frame, text=str(data['row'])).grid(
            row=0, column=1, sticky=tk.W, pady=5)
        
        type_label = "Type:" if is_duplicate else "Error Type:"
        ttk.Label(detail_frame, text=type_label, font=('Helvetica', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(detail_frame, text=data['type']).grid(
            row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(detail_frame, text="Description:", font=('Helvetica', 9, 'bold')).grid(
            row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(detail_frame, text=data['description'], wraplength=500).grid(
            row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(detail_frame, text="Row Content:", font=('Helvetica', 9, 'bold')).grid(
            row=3, column=0, sticky=(tk.W, tk.N), pady=5)
        
        # Row content text widget
        content_text = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, 
                                                 height=10, font=('Courier', 9))
        content_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        content_text.insert('1.0', data.get('content', 'No content available'))
        content_text.config(state='disabled')
        
        # Close button
        ttk.Button(detail_frame, text="Close", command=detail_window.destroy).grid(
            row=5, column=0, columnspan=2, pady=(10, 0))
    
    def show_all_error_details(self):
        """Show all error details in a new window."""
        if not hasattr(self, 'all_errors') or not self.all_errors:
            messagebox.showinfo("Error Details", "No errors to display")
            return
        
        # Create detail window
        detail_window = tk.Toplevel(self.root)
        detail_window.title("All Error Details")
        detail_window.geometry("900x600")
        
        # Text widget with scrollbar
        frame = ttk.Frame(detail_window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        detail_window.columnconfigure(0, weight=1)
        detail_window.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
        text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=('Courier', 9))
        text_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Build detailed text
        visible_errors = []
        for item in self.error_table.get_children():
            row_num = self.error_table.item(item)['values'][0]
            for error in self.all_errors:
                if error['row'] == row_num:
                    visible_errors.append(error)
                    break
        
        for i, error in enumerate(visible_errors, 1):
            text_widget.insert('end', f"{'=' * 80}\n")
            text_widget.insert('end', f"ERROR #{i}\n")
            text_widget.insert('end', f"{'=' * 80}\n")
            text_widget.insert('end', f"Row Number: {error['row']}\n")
            text_widget.insert('end', f"Error Type: {error['type']}\n")
            text_widget.insert('end', f"Description: {error['description']}\n")
            text_widget.insert('end', f"\nRow Content:\n")
            text_widget.insert('end', f"{error.get('content', 'No content available')}\n\n")
        
        text_widget.config(state='disabled')
        
        # Close button
        ttk.Button(frame, text="Close", command=detail_window.destroy).grid(
            row=1, column=0, pady=(10, 0))
    
    def copy_error_rows(self):
        """Copy row numbers of visible errors to clipboard."""
        if not self.error_table.get_children():
            messagebox.showinfo("Copy Row Numbers", "No errors to copy")
            return
        
        # Get all visible row numbers
        row_numbers = []
        for item in self.error_table.get_children():
            values = self.error_table.item(item)['values']
            row_numbers.append(str(values[0]))
        
        # Copy to clipboard
        row_list = ', '.join(row_numbers)
        self.root.clipboard_clear()
        self.root.clipboard_append(row_list)
        
        messagebox.showinfo("Copy Row Numbers", 
                          f"Copied {len(row_numbers)} row number(s) to clipboard:\n{row_list[:200]}...")
    
    def export_errors(self):
        """Export visible errors to CSV file."""
        if not hasattr(self, 'current_report') or not self.current_report:
            messagebox.showwarning("Export Errors", "No errors to export")
            return
        
        if not self.current_report.errors:
            messagebox.showinfo("Export Errors", "No errors found to export")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Errors to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if filename:
            try:
                self.current_report.export_errors_csv(filename)
                messagebox.showinfo("Export Errors", f"Errors exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export errors: {str(e)}")
    
    def save_report(self):
        """Save the validation report to a file."""
        if not self.current_report:
            messagebox.showwarning("Warning", "No report to save")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Save Validation Report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.current_report.generate_report())
                messagebox.showinfo("Success", f"Report saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save report: {str(e)}")
    
    def clear_results(self):
        """Clear the results display."""
        self.progress_label.config(text="", foreground='black', font=('Helvetica', 9))
        self.progress_bar['value'] = 0
        
        # Clear error navigator
        for item in self.error_table.get_children():
            self.error_table.delete(item)
        self.all_errors = []
        self.all_duplicates = []
        self.error_filter.set('All Errors')
        self.error_stats_label.config(text="No errors")
        self.duplicate_stats_label.config(text="")
        
        # Reset validation state and disable Fix & Save button
        self.validation_completed = False
        self.fix_save_btn.config(state='disabled')
        
        # Reset progress bar to default blue color
        style = ttk.Style()
        style.configure("Colorful.Horizontal.TProgressbar",
                      background='#2196F3',
                      lightcolor='#64B5F6',
                      darkcolor='#1976D2')
    
    def open_documentation(self):
        """Open the documentation URL in the default browser."""
        try:
            webbrowser.open("https://github.com/jackworthen/file-proof")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open documentation: {str(e)}")
    
    def show_save_dialog(self):
        """Show dialog for saving options."""
        if not hasattr(self, 'current_report') or not self.current_report:
            messagebox.showwarning("Save", "No validation results to save. Please validate a file first.")
            return
        
        if not hasattr(self, 'last_validated_file'):
            messagebox.showwarning("Save", "Original file path not available.")
            return
        
        # Check if validation completed without cancellation
        if not self.validation_completed or (hasattr(self.current_report, 'cancelled') and self.current_report.cancelled):
            messagebox.showwarning("Save", "Cannot use Fix & Save on an incomplete validation. Please run a complete validation scan first.")
            return
        
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Options")
        dialog.geometry("365x280")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)
        
        # Title
        ttk.Label(main_frame, text="Select save options:", 
                 font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 15))
        
        # Checkboxes - determine what's available based on validation results
        has_errors = len(self.current_report.errors) > 0
        has_duplicates = len(self.current_report.duplicates) > 0
        
        # Set default values and states based on what was found
        self.save_without_errors_var = tk.BooleanVar(value=has_errors)
        self.remove_duplicates_var = tk.BooleanVar(value=has_duplicates)
        self.export_errors_var = tk.BooleanVar(value=has_errors)
        self.export_duplicates_var = tk.BooleanVar(value=has_duplicates)
        
        # Create checkboxes with conditional states
        save_without_errors_cb = ttk.Checkbutton(main_frame, text="Export file without error records",
                       variable=self.save_without_errors_var,
                       state='normal' if has_errors else 'disabled')
        save_without_errors_cb.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        remove_duplicates_cb = ttk.Checkbutton(main_frame, text="Remove duplicate records",
                       variable=self.remove_duplicates_var,
                       state='normal' if has_duplicates else 'disabled')
        remove_duplicates_cb.grid(row=2, column=0, sticky=tk.W, pady=5)
        
        export_errors_cb = ttk.Checkbutton(main_frame, text="Export error records",
                       variable=self.export_errors_var,
                       state='normal' if has_errors else 'disabled')
        export_errors_cb.grid(row=3, column=0, sticky=tk.W, pady=5)
        
        export_duplicates_cb = ttk.Checkbutton(main_frame, text="Export duplicate records",
                       variable=self.export_duplicates_var,
                       state='normal' if has_duplicates else 'disabled')
        export_duplicates_cb.grid(row=4, column=0, sticky=tk.W, pady=5)
        
        # Info label
        info_text = "Note: Options 1 & 2 will save to the same file if both are selected."
        ttk.Label(main_frame, text=info_text, foreground='gray', 
                 font=('Helvetica', 8)).grid(row=5, column=0, sticky=tk.W, pady=(15, 0))
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, sticky=tk.E, pady=(20, 0))
        
        def on_save():
            if not self.save_without_errors_var.get() and not self.remove_duplicates_var.get() and not self.export_errors_var.get() and not self.export_duplicates_var.get():
                messagebox.showwarning("Save", "Please select at least one option.")
                return
            dialog.destroy()
            self.perform_save_operation()
        
        ttk.Button(button_frame, text="Save", command=on_save).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).grid(row=0, column=1, padx=5)
    
    def perform_save_operation(self):
        """Perform the selected save operations."""
        try:
            # Get error and duplicate row numbers
            error_rows = set(error['row'] for error in self.current_report.errors)
            duplicate_rows = set(dup['row'] for dup in self.current_report.duplicates)
            
            # Read the original file
            with open(self.last_validated_file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            # Get delimiter from the report
            delimiter = self.current_report.delimiter if hasattr(self.current_report, 'delimiter') and self.current_report.delimiter else ','
            
            saved_files = []
            
            # Option 1 & 2 Combined: Export file without errors and/or duplicates
            if self.save_without_errors_var.get() or self.remove_duplicates_var.get():
                # Determine what to exclude and set appropriate title/filename
                exclude_rows = set()
                description_parts = []
                
                if self.save_without_errors_var.get():
                    exclude_rows.update(error_rows)
                    description_parts.append("errors")
                
                if self.remove_duplicates_var.get():
                    # Group duplicates by their content to keep only the first occurrence
                    duplicate_groups = defaultdict(list)
                    for dup in self.current_report.duplicates:
                        # Use content as key to group duplicates
                        content_key = dup.get('content', '')
                        duplicate_groups[content_key].append(dup['row'])
                    
                    # For each group, exclude all but the first occurrence
                    for content_key, row_numbers in duplicate_groups.items():
                        if len(row_numbers) > 0:
                            # Sort to ensure we keep the first occurrence
                            sorted_rows = sorted(row_numbers)
                            # Add all except the first to exclude_rows
                            exclude_rows.update(sorted_rows[1:])
                    
                    description_parts.append("duplicates")
                
                # Create title and filename based on what's being excluded
                if len(description_parts) == 2:
                    title = "Save File Without Errors and Duplicates"
                    suffix = "_clean"
                    file_description = "File without errors and duplicates"
                elif "errors" in description_parts:
                    title = "Save File Without Errors"
                    suffix = "_no_errors"
                    file_description = "File without errors"
                else:
                    title = "Save File Without Duplicates"
                    suffix = "_no_duplicates"
                    file_description = "File without duplicates"
                
                filename = filedialog.asksaveasfilename(
                    title=title,
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")],
                    initialfile=f"{os.path.splitext(os.path.basename(self.last_validated_file))[0]}{suffix}.csv"
                )
                
                if filename:
                    with open(filename, 'w', encoding='utf-8', newline='') as f:
                        for i, line in enumerate(lines, 1):
                            if i not in exclude_rows:
                                f.write(line)
                    saved_files.append(f"{file_description}: {filename}")
            
            # Option 3: Export error records
            if self.export_errors_var.get():
                filename = filedialog.asksaveasfilename(
                    title="Save Error Records Only",
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")],
                    initialfile=f"{os.path.splitext(os.path.basename(self.last_validated_file))[0]}_errors_only.csv"
                )
                
                if filename:
                    with open(filename, 'w', encoding='utf-8', newline='') as f:
                        # Write header if it exists (row 1)
                        if len(lines) > 0 and 1 not in error_rows:
                            f.write(lines[0])
                        
                        # Write only error rows
                        for i, line in enumerate(lines, 1):
                            if i in error_rows:
                                f.write(line)
                    saved_files.append(f"Error records only: {filename}")
            
            # Option 4: Export duplicate records
            if self.export_duplicates_var.get():
                filename = filedialog.asksaveasfilename(
                    title="Save Duplicate Records Only",
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")],
                    initialfile=f"{os.path.splitext(os.path.basename(self.last_validated_file))[0]}_duplicates_only.csv"
                )
                
                if filename:
                    with open(filename, 'w', encoding='utf-8', newline='') as f:
                        # Write header if it exists (row 1)
                        if len(lines) > 0 and 1 not in duplicate_rows:
                            f.write(lines[0])
                        
                        # Write only duplicate rows
                        for i, line in enumerate(lines, 1):
                            if i in duplicate_rows:
                                f.write(line)
                    saved_files.append(f"Duplicate records only: {filename}")
            
            # Show success message
            if saved_files:
                message = "Successfully saved:\n\n" + "\n".join(saved_files)
                messagebox.showinfo("Save Complete", message)
        
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save files: {str(e)}")

def main():
    """Main entry point."""
    root = tk.Tk()
    app = DataValidatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()