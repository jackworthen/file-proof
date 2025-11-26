#!/usr/bin/env python3
"""
Data File Validator
A robust application for validating data files with various formats and delimiters.
Supports large files up to 1GB with detailed error reporting.
"""

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
        
    def add_error(self, row_num: int, error_type: str, description: str):
        """Add an error to the report."""
        self.errors.append({
            'row': row_num,
            'type': error_type,
            'description': description
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
                                f"Expected {expected_columns} columns, found {actual_columns}"
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
                                    "Unclosed double quotes detected"
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
        self.root.geometry("800x700")
        
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
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Validation Report", padding="10")
        results_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, 
                                                      height=20, font=('Courier', 9))
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, sticky=tk.E)
        
        ttk.Button(buttons_frame, text="Save Report", 
                  command=self.save_report).grid(row=0, column=0, padx=5)
        ttk.Button(buttons_frame, text="Clear", 
                  command=self.clear_results).grid(row=0, column=1, padx=5)
        
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
        """Update the progress bar and label with dynamic colors."""
        self.progress_bar['value'] = progress
        self.progress_label.config(text=f"Processing... {progress:.1f}% ({rows:,} rows)")
        
        # Dynamic color changes based on progress
        style = ttk.Style()
        if progress < 25:
            # Blue for early stage
            style.configure("Colorful.Horizontal.TProgressbar",
                          background='#2196F3',  # Blue
                          lightcolor='#64B5F6',
                          darkcolor='#1976D2')
        elif progress < 50:
            # Cyan for second quarter
            style.configure("Colorful.Horizontal.TProgressbar",
                          background='#00BCD4',  # Cyan
                          lightcolor='#4DD0E1',
                          darkcolor='#0097A7')
        elif progress < 75:
            # Orange for third quarter
            style.configure("Colorful.Horizontal.TProgressbar",
                          background='#FF9800',  # Orange
                          lightcolor='#FFB74D',
                          darkcolor='#F57C00')
        else:
            # Green for final stage
            style.configure("Colorful.Horizontal.TProgressbar",
                          background='#4CAF50',  # Green
                          lightcolor='#81C784',
                          darkcolor='#388E3C')
        
        self.root.update_idletasks()
    
    def display_results(self, report: ValidationReport):
        """Display validation results in the text widget."""
        self.results_text.delete('1.0', tk.END)
        report_text = report.generate_report()
        self.results_text.insert('1.0', report_text)
        
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
        
        # Auto-scroll to top
        self.results_text.see('1.0')
    
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
        self.results_text.delete('1.0', tk.END)
        self.progress_label.config(text="", foreground='black', font=('Helvetica', 9))
        self.progress_bar['value'] = 0
        
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