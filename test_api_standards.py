#!/usr/bin/env python3
"""
Test pdf-large-reader with real API standards PDFs.
"""

import time
from pathlib import Path
from src.main import (
    process_large_pdf,
    extract_text_only,
    extract_everything
)

# Test files
pdf1 = "/mnt/ace/O&G-Standards/raw/Oil and Gas Codes/API Stds/API/API RP 579 (2000).pdf"
pdf2 = "/mnt/ace/O&G-Standards/raw/Oil and Gas Codes/API Stds/API/API Std 650 (2001).pdf"

def test_file(pdf_path, test_name):
    """Test a single PDF file with multiple approaches."""
    print(f"\n{'='*80}")
    print(f"Testing: {test_name}")
    print(f"File: {pdf_path}")
    print(f"Size: {Path(pdf_path).stat().st_size / (1024*1024):.1f} MB")
    print('='*80)

    # Test 1: Quick text extraction
    print("\n1️⃣  Quick Text Extraction (extract_text_only)")
    print("-" * 80)
    start_time = time.time()
    text = extract_text_only(pdf_path)
    elapsed = time.time() - start_time

    print(f"✅ Extracted {len(text):,} characters in {elapsed:.2f} seconds")
    print(f"   First 200 characters: {text[:200]}")
    print(f"   Performance: {len(text)/elapsed:,.0f} chars/sec")

    # Test 2: Process with auto strategy (list format)
    print("\n2️⃣  Process with Auto Strategy (list format)")
    print("-" * 80)
    start_time = time.time()
    pages = process_large_pdf(
        pdf_path,
        output_format="list",
        auto_strategy=True
    )
    elapsed = time.time() - start_time

    print(f"✅ Processed {len(pages)} pages in {elapsed:.2f} seconds")
    print(f"   Performance: {len(pages)/elapsed:.2f} pages/sec")

    # Show first page info
    if pages:
        first_page = pages[0]
        print(f"\n   Page 1 Details:")
        print(f"   - Text length: {len(first_page.text)} characters")
        print(f"   - Images: {len(first_page.images)}")
        print(f"   - Metadata keys: {list(first_page.metadata.keys())}")
        print(f"   - First 150 chars: {first_page.text[:150]}")

    # Test 3: Generator format (memory efficient)
    print("\n3️⃣  Memory-Efficient Generator Processing")
    print("-" * 80)
    start_time = time.time()

    page_count = 0
    total_chars = 0

    for page in process_large_pdf(pdf_path, output_format="generator"):
        page_count += 1
        total_chars += len(page.text)
        if page_count % 50 == 0:
            print(f"   Processed {page_count} pages... ({total_chars:,} chars)")

    elapsed = time.time() - start_time
    print(f"✅ Generator processed {page_count} pages in {elapsed:.2f} seconds")
    print(f"   Total characters: {total_chars:,}")
    print(f"   Performance: {page_count/elapsed:.2f} pages/sec")

    # Test 4: Extract everything (with images and tables)
    print("\n4️⃣  Complete Extraction (extract_everything)")
    print("-" * 80)
    start_time = time.time()

    all_pages = extract_everything(pdf_path)

    elapsed = time.time() - start_time
    print(f"✅ Extracted everything from {len(all_pages)} pages in {elapsed:.2f} seconds")

    # Count total images and tables
    total_images = sum(len(p.images) for p in all_pages)
    total_text = sum(len(p.text) for p in all_pages)

    print(f"   Total images found: {total_images}")
    print(f"   Total text characters: {total_text:,}")
    print(f"   Average chars per page: {total_text/len(all_pages):.0f}")

    return {
        'pages': len(pages),
        'text_chars': len(text),
        'images': total_images
    }

# Progress callback for testing
def progress_callback(current, total):
    """Display progress."""
    percent = (current / total) * 100
    if current % 20 == 0 or current == total:
        print(f"   Progress: {current}/{total} ({percent:.1f}%)")

# Main tests
if __name__ == "__main__":
    print("\n" + "="*80)
    print("PDF-LARGE-READER - API Standards Testing")
    print("="*80)

    # Test both PDFs
    results1 = test_file(pdf1, "API RP 579 (2000) - 41 MB")
    results2 = test_file(pdf2, "API Std 650 (2001) - 28 MB")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nAPI RP 579 (2000):")
    print(f"  - Pages: {results1['pages']}")
    print(f"  - Text: {results1['text_chars']:,} characters")
    print(f"  - Images: {results1['images']}")

    print(f"\nAPI Std 650 (2001):")
    print(f"  - Pages: {results2['pages']}")
    print(f"  - Text: {results2['text_chars']:,} characters")
    print(f"  - Images: {results2['images']}")

    print("\n✅ All tests completed successfully!")
