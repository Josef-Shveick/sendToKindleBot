import os
import subprocess

# 📁 Folder containing your PDFs
folder_path = r"C:\Users\<user>\Downloads\project"

# Output folder
output_dir = os.path.join(folder_path, "epubs")
os.makedirs(output_dir, exist_ok=True)

# Collect all PDFs
pdfs = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

for pdf_file in pdfs:
    pdf_path = os.path.join(folder_path, pdf_file)
    epub_path = os.path.join(output_dir, os.path.splitext(pdf_file)[0] + ".epub")

    print(f"📘 Converting: {pdf_file} → {epub_path}")

    try:
        subprocess.run([
            "ebook-convert", pdf_path, epub_path,
            "--enable-heuristics",
            "--embed-all-fonts",
            "--pretty-print",
            "--preserve-cover-aspect-ratio",
            "--smarten-punctuation",
            "--language", "en"
        ], check=True)
        print(f"✅ Successfully converted: {epub_path}\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Conversion failed for {pdf_file}: {e}\n")

print("🎯 All conversions complete.")
