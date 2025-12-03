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
        self.passed = False
        
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
        
        if not self.errors and not self.warnings:
            report.append("\n✓ No errors or warnings found. File is valid!")
        
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
                 max_errors: int = 1000, chunk_size: int = 8192):
        self.filepath = filepath
        self.delimiter = delimiter
        self.max_errors = max_errors
        self.chunk_size = chunk_size
        self.report = ValidationReport(os.path.basename(filepath))
        
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
                
                for line in f:
                    row_num += 1
                    bytes_processed += len(line.encode('utf-8'))
                    
                    if progress_callback and row_num % 1000 == 0:
                        progress = (bytes_processed / self.report.file_size) * 100
                        progress_callback(progress, row_num)
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    self.report.total_rows += 1
                    
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
                
                self.report.file_type = f"Delimited (delimiter: {repr(self.delimiter).strip(chr(39))})"
                
        except Exception as e:
            self.report.add_error(0, "FILE_READ_ERROR", f"Error reading file: {str(e)}")
        
        self.report.end_time = datetime.now()
        self.report.passed = self.report.invalid_rows == 0 and len(self.report.errors) == 0
        
        return self.report

class JSONValidator:
    """Validates JSON files."""
    
    def __init__(self, filepath: str, max_errors: int = 1000):
        self.filepath = filepath
        self.max_errors = max_errors
        self.report = ValidationReport(os.path.basename(filepath))
        
    def validate(self, progress_callback=None) -> ValidationReport:
        """Validate the JSON file."""
        self.report.start_time = datetime.now()
        self.report.file_size = os.path.getsize(self.filepath)
        self.report.file_type = "JSON"
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if progress_callback:
                    progress_callback(50, 0)
                
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
                        progress_callback(100, self.report.total_rows)
                    
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
        self.root.geometry("960x700")  # Increased width by 20% (800 * 1.2 = 960)
        
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
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface."""
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
        ttk.Button(action_frame, text="💾 Export Errors to CSV", 
                  command=self.export_errors).grid(row=0, column=1, padx=5)
        ttk.Button(action_frame, text="🔍 Show All Details", 
                  command=self.show_all_error_details).grid(row=0, column=2, padx=5)
        
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
        self.clear_results()
        
        # Run validation in separate thread
        thread = threading.Thread(target=self.run_validation)
        thread.daemon = True
        thread.start()
    
    def run_validation(self):
        """Run the validation process."""
        filepath = self.filepath.get()
        
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
                validator = JSONValidator(filepath)
            else:
                validator = DelimitedFileValidator(filepath, delimiter=delimiter)
            
            # Run validation with progress updates
            def progress_callback(progress, rows):
                self.root.after(0, self.update_progress, progress, rows)
            
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
    
    def update_progress(self, progress, rows):
        """Update the progress bar and label - stays blue while processing."""
        self.progress_bar['value'] = progress
        self.progress_label.config(text=f"Processing... {progress:.1f}% ({rows:,} rows)")
        
        # Keep progress bar blue during processing
        # Color will change to green/red only when validation completes
        
        self.root.update_idletasks()
    
    def display_results(self, report: ValidationReport):
        """Display validation results in the error navigator."""
        # Color code the result with enhanced styling
        if report.passed:
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
        
        # Get unique error types for filter
        error_types = ['All Errors']
        if self.all_errors:
            unique_types = sorted(set(error['type'] for error in self.all_errors))
            error_types.extend(unique_types)
        
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
        
        # Update stats
        self.update_error_stats()
    
    def update_error_stats(self):
        """Update the error statistics label."""
        visible_count = len(self.error_table.get_children())
        total_count = len(self.all_errors) if hasattr(self, 'all_errors') else 0
        
        if visible_count == 0:
            self.error_stats_label.config(text="No errors found")
        elif visible_count == total_count:
            self.error_stats_label.config(text=f"Showing all {total_count} error(s)")
        else:
            self.error_stats_label.config(text=f"Showing {visible_count} of {total_count} error(s)")
    
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
        """Show detailed information for selected error (double-click)."""
        selection = self.error_table.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.error_table.item(item)['values']
        
        # Find the full error data
        row_num = values[0]
        error_data = None
        for error in self.all_errors:
            if error['row'] == row_num:
                error_data = error
                break
        
        if not error_data:
            return
        
        # Create detail window
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Error Detail - Row {row_num}")
        detail_window.geometry("700x400")
        
        # Detail frame
        detail_frame = ttk.Frame(detail_window, padding="10")
        detail_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        detail_window.columnconfigure(0, weight=1)
        detail_window.rowconfigure(0, weight=1)
        detail_frame.columnconfigure(1, weight=1)
        detail_frame.rowconfigure(4, weight=1)
        
        # Error information
        ttk.Label(detail_frame, text="Row Number:", font=('Helvetica', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(detail_frame, text=str(error_data['row'])).grid(
            row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(detail_frame, text="Error Type:", font=('Helvetica', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(detail_frame, text=error_data['type']).grid(
            row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(detail_frame, text="Description:", font=('Helvetica', 9, 'bold')).grid(
            row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(detail_frame, text=error_data['description'], wraplength=500).grid(
            row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(detail_frame, text="Row Content:", font=('Helvetica', 9, 'bold')).grid(
            row=3, column=0, sticky=(tk.W, tk.N), pady=5)
        
        # Row content text widget
        content_text = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, 
                                                 height=10, font=('Courier', 9))
        content_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        content_text.insert('1.0', error_data.get('content', 'No content available'))
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
        self.error_filter.set('All Errors')
        self.error_stats_label.config(text="No errors")
        
        # Reset progress bar to default blue color
        style = ttk.Style()
        style.configure("Colorful.Horizontal.TProgressbar",
                      background='#2196F3',
                      lightcolor='#64B5F6',
                      darkcolor='#1976D2')

def main():
    """Main entry point."""
    root = tk.Tk()
    app = DataValidatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()