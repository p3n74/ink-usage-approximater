import fitz 
import numpy as np
from PIL import Image
import os
import glob

unit_counts = {
    "Cyan": 0,
    "Magenta": 0,
    "Yellow": 0,
    "Black": 0
}


A4_AREA_MM2 = 210 * 297  # 62,370 mm²
REALISTIC_INK_PER_A4_ML = 1.9  # ml per A4 at 100% coverage (based on HP data)
DPI = 1800
MM_PER_INCH = 25.4
PIXELS_PER_MM = DPI / MM_PER_INCH
PIXELS_PER_A4 = A4_AREA_MM2 * (PIXELS_PER_MM ** 2)

# Calculate realistic ink per pixel
INK_PER_UNIT_ML = REALISTIC_INK_PER_A4_ML / PIXELS_PER_A4
INK_PRICE_PER_ML = 5.0  # pesos per ml
COST_PER_UNIT = INK_PER_UNIT_ML * INK_PRICE_PER_ML

def rgb_to_cmyk_units(r, g, b):
    """Convert RGB to CMYK values (0-1 range)"""
    c = 1 - (r / 255)
    m = 1 - (g / 255)
    y = 1 - (b / 255)
    k = min(c, m, y)
    c = max(0, c - k)
    m = max(0, m - k)
    y = max(0, y - k)
    return c, m, y, k

def process_image(image):
    global unit_counts
    image = image.convert("RGB")
    pixels = image.load()
    width, height = image.size

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            c, m, y_val, k = rgb_to_cmyk_units(r, g, b)
            unit_counts["Cyan"] += c
            unit_counts["Magenta"] += m
            unit_counts["Yellow"] += y_val
            unit_counts["Black"] += k

def analyze_pdf(file_path):
    global unit_counts
    unit_counts = {
        "Cyan": 0,
        "Magenta": 0,
        "Yellow": 0,
        "Black": 0
    }
    
    doc = fitz.open(file_path)
    total_pixels = 0
    
    for page_num in range(len(doc)):
        print(f"Processing page {page_num + 1}...")
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        total_pixels += pix.width * pix.height
        process_image(image)
    
    doc.close()
    
    total_usage = sum(unit_counts.values())
    return total_usage, unit_counts.copy(), total_pixels

def analyze_all_pdfs():
    pdf_folder = "main files"
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in '{pdf_folder}' folder")
        return
    
    
    pdf_results = {}
    
    for pdf_file in pdf_files:
        filename = os.path.basename(pdf_file)
        print(f"\n{'='*50}")
        print(f"Analyzing: {filename}")
        print(f"{'='*50}")
        
        total_usage, color_counts, total_pixels = analyze_pdf(pdf_file)
        
        # Add flat 80.5% to ink coverage since its full page
        total_usage_with_buffer = total_usage * 1.8
        
        # Calculate realistic ink usage and cost
        total_ink_ml = total_usage_with_buffer * INK_PER_UNIT_ML
        total_cost = total_usage_with_buffer * COST_PER_UNIT
        
        # Calculate coverage statistics
        max_possible_units = total_pixels * 4  # C+M+Y+K all at 1.0
        coverage_percentage = (total_usage_with_buffer / max_possible_units) * 100 if max_possible_units > 0 else 0
        
        pdf_results[filename] = {
            'total_units': total_usage_with_buffer,
            'colors': color_counts,
            'ink_ml': total_ink_ml,
            'cost': total_cost,
            'pixels': total_pixels,
            'coverage_pct': coverage_percentage
        }
        
        print(f"\nResults for {filename}:")
        print(f"Total pixels: {total_pixels:,}")
        print(f"CMYK units used: {total_usage:,.2f} (with 15% buffer: {total_usage_with_buffer:,.2f})")
        print(f"Effective coverage: {coverage_percentage:.1f}%")
        
        print(f"\nColor breakdown:")
        for color, count in color_counts.items():
            color_ink_ml = count * INK_PER_UNIT_ML
            color_cost = count * COST_PER_UNIT
            color_pct = (count / total_pixels) * 100 if total_pixels > 0 else 0
            print(f"{color:8}: {count:12,.0f} units ({color_pct:5.1f}% avg) = {color_ink_ml:6.4f} ml = ₱{color_cost:6.2f}")
        
        print(f"\nTOTALS:")
        print(f"Total ink volume: {total_ink_ml:.4f} ml")
        print(f"Total ink cost: ₱{total_cost:.2f}")
        
        # Show cost per page equivalent
        pages_equivalent = total_pixels / PIXELS_PER_A4
        cost_per_page = total_cost / pages_equivalent if pages_equivalent > 0 else 0
        print(f"Equivalent pages: {pages_equivalent:.2f}")
        print(f"Cost per page: ₱{cost_per_page:.2f}")
    
    print(f"\n{'='*60}")
    print("SUMMARY - Ranked by total ink cost:")
    print(f"{'='*60}")
    
    for filename, results in sorted(pdf_results.items(), key=lambda x: x[1]['cost'], reverse=True):
        pages_equiv = results['pixels'] / PIXELS_PER_A4
        cost_per_page = results['cost'] / pages_equiv if pages_equiv > 0 else 0
        print(f"{filename}")
        print(f"  {results['ink_ml']:6.3f} ml = ₱{results['cost']:6.2f} ({results['coverage_pct']:4.1f}% coverage, ₱{cost_per_page:.2f}/page)")
    
    if pdf_results:
        highest_pdf = max(pdf_results, key=lambda x: pdf_results[x]['cost'])
        highest_results = pdf_results[highest_pdf]
        highest_pages = highest_results['pixels'] / PIXELS_PER_A4
        highest_cost_per_page = highest_results['cost'] / highest_pages
        
        print(f"\nHIGHEST INK USAGE: {highest_pdf}")
        print(f"   Volume: {highest_results['ink_ml']:.3f} ml")
        print(f"   Cost: ₱{highest_results['cost']:.2f}")
        print(f"   Coverage: {highest_results['coverage_pct']:.1f}%")
        print(f"   Cost per page: ₱{highest_cost_per_page:.2f}")

analyze_all_pdfs()
