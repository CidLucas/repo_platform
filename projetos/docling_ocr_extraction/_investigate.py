"""Investigate PDF structure to understand extraction gaps."""
import pdfplumber

pdf = pdfplumber.open("sample.pdf")

# Page 2 (native) - check table cell content
page2 = pdf.pages[1]
tbl0 = page2.find_tables()[0]
data = tbl0.extract()
print("=== Page 2 Table 0 — all rows ===")
for j, row in enumerate(data):
    filled = [(k, v) for k, v in enumerate(row) if v and v.strip()]
    empty_count = sum(1 for v in row if not v or not v.strip())
    if filled:
        print(f"  Row {j}: {len(filled)} filled, {empty_count} empty: {filled[:3]}")
    else:
        print(f"  Row {j}: ALL {empty_count} cells EMPTY")

# Chars within table 0 bbox
t0_bbox = tbl0.bbox
chars_in = [c for c in page2.chars
            if t0_bbox[0] <= c["x0"] <= t0_bbox[2] and t0_bbox[1] <= c["top"] <= t0_bbox[3]]
print(f"\nChars in table0 bbox: {len(chars_in)}")
if chars_in:
    text = "".join(c["text"] for c in chars_in)
    print(f"Text: {text[:300]}")

# How many digit chars on ALL pages?
print("\n=== Digit chars per page ===")
for i, page in enumerate(pdf.pages):
    digits = [c for c in page.chars if c["text"] in "0123456789"]
    comma_digits = [c for c in page.chars if c["text"] in "0123456789,."]
    total = len(page.chars)
    print(f"  Page {i+1}: {total} chars, {len(digits)} digits, {len(comma_digits)} digit/comma/dot")

# Page 3 (classified as OCR): does it also have some text chars?
print("\n=== Page 3 (OCR-classified) ===")
page3 = pdf.pages[2]
print(f"  chars={len(page3.chars)}, tables={len(page3.find_tables())}")
tables3 = page3.find_tables()
for i, tbl in enumerate(tables3[:2]):
    data = tbl.extract()
    filled_total = sum(1 for row in data for cell in row if cell and cell.strip())
    print(f"  Table {i}: {len(data)} rows, filled_cells={filled_total}")

# Check: what percentage of table VALUE cells are empty on native pages?
print("\n=== Native page table emptiness ===")
for pg_idx in [0, 1]:  # pages 1 and 2
    page = pdf.pages[pg_idx]
    tables = page.find_tables()
    for ti, tbl in enumerate(tables):
        data = tbl.extract()
        total_cells = sum(len(row) for row in data)
        empty = sum(1 for row in data for cell in row if not cell or not cell.strip())
        print(f"  Page {pg_idx+1} Table {ti}: {total_cells} cells, {empty} empty ({100*empty/max(total_cells,1):.0f}%)")

# Bottom chart sections on page 2 (tables 2-5)
print("\n=== Page 2 bottom sections (tables 2-5) — chart or table? ===")
for ti in range(2, min(6, len(page2.find_tables()))):
    tbl = page2.find_tables()[ti]
    data = tbl.extract()
    print(f"  Table {ti}: bbox=({tbl.bbox[0]:.0f},{tbl.bbox[1]:.0f},{tbl.bbox[2]:.0f},{tbl.bbox[3]:.0f}), rows={len(data)}")
    for row in data[:2]:
        filled = [(k, v[:30]) for k, v in enumerate(row) if v and v.strip()]
        if filled:
            print(f"    {filled}")
        else:
            print(f"    ALL EMPTY")

pdf.close()
