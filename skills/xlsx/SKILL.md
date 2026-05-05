---
name: xlsx
description: "Use this skill whenever a spreadsheet file is the primary input or output. This includes any task in which the user wants to: open, read, edit, or repair an existing .xlsx, .xlsm, .csv, or .tsv file (e.g., add columns, compute formulas, formatting, charts, cleaning messy data); create a new spreadsheet from scratch or from other data sources; or convert between tabular file formats. Trigger especially when the user mentions a spreadsheet file by name or path — even in passing (e.g., \"the xlsx in my downloads\") — and wants something done with it or produced from it. Also trigger when cleaning or restructuring messy tabular data files (malformed rows, misplaced headers, junk data) into normal spreadsheets. The artifact must be a spreadsheet file. Do NOT trigger when the primary artifact is a Word document, an HTML report, a standalone Python script, a database pipeline, or a Google Sheets API integration, even if tabular data is involved."
---

# Artifact requirements

## All Excel files

### Professional font
- Use a consistent professional font (e.g., Arial, Times New Roman) for all artifacts unless the user specifies otherwise

### Zero formula errors
- Every Excel model MUST be delivered with ZERO formula errors (#REF!, #DIV/0!, #VALUE!, #N/A, #NAME?)

### Preserving existing templates (when updating templates)
- Study and EXACTLY match existing format, style, and conventions when modifying files
- Never impose standardized formatting on files with established templates
- Existing template conventions ALWAYS override this guidance

## Financial models

### Color coding standards
Unless the user or an existing template specifies otherwise

#### Industry color conventions
- **Blue text (RGB: 0,0,255)**: Hardcoded inputs and numbers users will change for scenarios
- **Black text (RGB: 0,0,0)**: ALL formulas and calculations
- **Green text (RGB: 0,128,0)**: References pulling from other sheets in the same workbook
- **Red text (RGB: 255,0,0)**: External references to other files
- **Yellow background (RGB: 255,255,0)**: Key assumptions requiring attention or cells that must be updated

### Number formatting standards

#### Required format rules
- **Years**: Formatted as text strings (e.g., "2024", not "2,024")
- **Currency**: Use the format $#,##0; ALWAYS specify units in headers ("Revenue ($mm)")
- **Zeros**: Use number formatting so all zeros display as "-", including percentages (e.g., "$#,##0;($#,##0);-")
- **Percentages**: Default to 0.0% format (one decimal)
- **Multiples**: Formatted as 0.0x for valuation multiples (EV/EBITDA, P/E)
- **Negative numbers**: Use parentheses (123), not a minus -123

### Formula construction rules

#### Assumption placement
- Place ALL assumptions (growth rates, margins, multiples, etc.) in dedicated assumption cells
- Use cell references instead of hardcoded values in formulas
- Example: use =B5*(1+$B$6) instead of =B5*1.05

#### Preventing formula errors
- Verify correctness of all cell references
- Check for off-by-one errors in ranges
- Ensure formula consistency across all forecast periods
- Test edge cases (zero values, negative numbers)
- Verify there are no unintended circular references

#### Hardcode documentation requirements
- Comment in or in adjacent cells (if at the end of a table). Format: "Source: [System/Document], [Date], [Specific Reference], [URL if applicable]"
- Examples:
  - "Source: Company 10-K, FY2024, Page 45, Revenue Note, [SEC EDGAR URL]"
  - "Source: Company 10-Q, Q2 2025, Exhibit 99.1, [SEC EDGAR URL]"
  - "Source: Bloomberg Terminal, 8/15/2025, AAPL US Equity"
  - "Source: FactSet, 8/20/2025, Consensus Estimates Screen"

# Creating, editing, and analyzing XLSX

## Overview

The user may ask you to create, edit, or analyze the contents of an .xlsx file. Different tools and workflows are available for different tasks.

## Important requirements

**LibreOffice is required for formula recalculation**: You may assume that LibreOffice is installed for recalculating formula values via the `scripts/recalc.py` script. The script automatically configures LibreOffice on first run, including in sandbox environments where Unix sockets are restricted (handled by `scripts/office/soffice.py`)

## Reading and analyzing data

### Data analysis with pandas
For data analysis, visualization, and basic operations, use **pandas**, which provides powerful data manipulation capabilities:

```python
import pandas as pd

# Read Excel
df = pd.read_excel('file.xlsx')  # Default: first sheet
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)  # All sheets as dict

# Analyze
df.head()      # Preview data
df.info()      # Column info
df.describe()  # Statistics

# Write Excel
df.to_excel('output.xlsx', index=False)
```

## Excel file workflows

## CRITICAL: use formulas, not hardcoded values

**Always use Excel formulas instead of computing values in Python and hardcoding them.** This ensures the spreadsheet remains dynamic and updatable.

### ❌ WRONG — hardcoding computed values
```python
# Bad: Calculating in Python and hardcoding result
total = df['Sales'].sum()
sheet['B10'] = total  # Hardcodes 5000

# Bad: Computing growth rate in Python
growth = (df.iloc[-1]['Revenue'] - df.iloc[0]['Revenue']) / df.iloc[0]['Revenue']
sheet['C5'] = growth  # Hardcodes 0.15

# Bad: Python calculation for average
avg = sum(values) / len(values)
sheet['D20'] = avg  # Hardcodes 42.5
```

### ✅ CORRECT — using Excel formulas
```python
# Good: Let Excel calculate the sum
sheet['B10'] = '=SUM(B2:B9)'

# Good: Growth rate as Excel formula
sheet['C5'] = '=(C4-C2)/C2'

# Good: Average using Excel function
sheet['D20'] = '=AVERAGE(D2:D19)'
```

This applies to ALL calculations — sums, percentages, ratios, differences, etc. The spreadsheet should be able to recalculate when source data changes.

## Common workflow
1. **Choose tool**: pandas for data, openpyxl for formulas/formatting
2. **Create/Load**: Create a new workbook or load an existing file
3. **Modify**: Add/edit data, formulas, and formatting
4. **Save**: Write to a file
5. **Recalculate formulas (REQUIRED WHEN USING FORMULAS)**: Use the scripts/recalc.py script
   ```bash
   python scripts/recalc.py output.xlsx
   ```
6. **Verify and fix any errors**:
   - The script returns JSON with error details
   - If `status` is `errors_found`, check `error_summary` for specific error types and locations
   - Fix the identified errors and recalculate again
   - Common errors to fix:
     - `#REF!`: Invalid cell references
     - `#DIV/0!`: Division by zero
     - `#VALUE!`: Wrong data type in formula
     - `#NAME?`: Unrecognized formula name

### Creating new Excel files

```python
# Using openpyxl for formulas and formatting
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
sheet = wb.active

# Add data
sheet['A1'] = 'Hello'
sheet['B1'] = 'World'
sheet.append(['Row', 'of', 'data'])

# Add formula
sheet['B2'] = '=SUM(A1:A10)'

# Formatting
sheet['A1'].font = Font(bold=True, color='FF0000')
sheet['A1'].fill = PatternFill('solid', start_color='FFFF00')
sheet['A1'].alignment = Alignment(horizontal='center')

# Column width
sheet.column_dimensions['A'].width = 20

wb.save('output.xlsx')
```

### Editing existing Excel files

```python
# Using openpyxl to preserve formulas and formatting
from openpyxl import load_workbook

# Load existing file
wb = load_workbook('existing.xlsx')
sheet = wb.active  # or wb['SheetName'] for specific sheet

# Working with multiple sheets
for sheet_name in wb.sheetnames:
    sheet = wb[sheet_name]
    print(f"Sheet: {sheet_name}")

# Modify cells
sheet['A1'] = 'New Value'
sheet.insert_rows(2)  # Insert row at position 2
sheet.delete_cols(3)  # Delete column 3

# Add new sheet
new_sheet = wb.create_sheet('NewSheet')
new_sheet['A1'] = 'Data'

wb.save('modified.xlsx')
```

## Formula recalculation

Excel files created or modified by openpyxl contain formulas as strings, but not computed values. Use the bundled `scripts/recalc.py` script to recalculate formulas:

```bash
python scripts/recalc.py <excel_file> [timeout_seconds]
```

Example:
```bash
python scripts/recalc.py output.xlsx 30
```

The script:
- Automatically configures the LibreOffice macro on first run
- Recalculates all formulas across all sheets
- Scans ALL cells for Excel errors (#REF!, #DIV/0!, etc.)
- Returns JSON with detailed error locations and counts
- Works on Linux and macOS

## Formula verification checklist

Quick checks to confirm formulas work correctly:

### Essential verification
- [ ] **Test 2-3 sample references**: Verify they pull the correct values before building the full model
- [ ] **Column matching**: Confirm Excel columns line up (e.g., column 64 = BL, not BK)
- [ ] **Row offsets**: Remember that Excel rows are 1-indexed (DataFrame row 5 = Excel row 6)

### Common pitfalls
- [ ] **NaN handling**: Check for null values via `pd.notna()`
- [ ] **Right-side columns**: FY data is often in columns 50+
- [ ] **Multiple matches**: Look for all occurrences, not just the first
- [ ] **Division by zero**: Check denominators before using `/` in formulas (#DIV/0!)
- [ ] **Bad references**: Verify all cell references point to the intended cells (#REF!)
- [ ] **Cross-sheet references**: Use the correct format (Sheet1!A1) for linked sheets

### Formula testing strategy
- [ ] **Start small**: Test formulas on 2-3 cells before applying broadly
- [ ] **Verify dependencies**: Confirm all cells referenced by formulas exist
- [ ] **Test edge cases**: Include zero, negative, and very large values

### Interpreting scripts/recalc.py output
The script returns JSON with error details:
```json
{
  "status": "success",           // or "errors_found"
  "total_errors": 0,              // Total error count
  "total_formulas": 42,           // Number of formulas in file
  "error_summary": {              // Only present if errors found
    "#REF!": {
      "count": 2,
      "locations": ["Sheet1!B5", "Sheet1!C10"]
    }
  }
}
```

## Best practices

### Library selection
- **pandas**: Best for data analysis, bulk operations, and simple data exports
- **openpyxl**: Best for complex formatting, formulas, and Excel-specific features

### Working with openpyxl
- Cell indices are 1-based (row=1, column=1 references cell A1)
- Use `data_only=True` to read computed values: `load_workbook('file.xlsx', data_only=True)`
- **Warning**: If you open with `data_only=True` and save, formulas are replaced with values and lost permanently
- For large files: use `read_only=True` for reading or `write_only=True` for writing
- Formulas are preserved but not evaluated — use scripts/recalc.py to refresh values

### Working with pandas
- Specify data types to avoid inference issues: `pd.read_excel('file.xlsx', dtype={'id': str})`
- For large files, read specific columns: `pd.read_excel('file.xlsx', usecols=['A', 'C', 'E'])`
- Handle dates correctly: `pd.read_excel('file.xlsx', parse_dates=['date_column'])`

## Code style guide
**IMPORTANT**: When generating Python code for Excel operations:
- Write minimal, concise Python without unnecessary comments
- Avoid verbose variable names and redundant operations
- Avoid unnecessary print statements

**For the Excel files themselves**:
- Add cell comments to complex formulas or important assumptions
- Document data sources for hardcoded values
- Include notes for key calculations and model sections
