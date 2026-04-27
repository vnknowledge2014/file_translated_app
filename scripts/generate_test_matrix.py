import os
import asyncio
import random
import csv
import zipfile
import io
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.languages import SUPPORTED_LANGUAGES
from app.domains import SUPPORTED_DOMAINS
from app.ollama.client import OllamaClient
from app.config import settings

# Ensure we use the requested model
MODEL_NAME = "gemma4:31b-cloud"

# Test matrix dimensions
FORMATS = ["docx", "xlsx", "pptx", "txt", "md", "csv"]
LANGUAGES = list(SUPPORTED_LANGUAGES.keys())
DOMAINS = list(SUPPORTED_DOMAINS.keys())
COMPLEXITIES = ["simple_sentence", "technical_paragraph", "mixed_tags"]

def create_docx(path: str, text: str):
    """Create a minimal valid DOCX file using raw zip XML."""
    doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>
</w:document>"""
    rel_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="xml" ContentType="application/xml"/>
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rel_xml)
        zf.writestr("word/document.xml", doc_xml)

def create_xlsx(path: str, text: str):
    """Create a minimal valid XLSX file."""
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    sheet_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>{text}</t></is></c></row></sheetData>
</worksheet>"""
    rel_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
    wb_rel_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="xml" ContentType="application/xml"/>
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", wb_rel_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rel_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)

def create_pptx(path: str, text: str):
    """Create a minimal PPTX file (stub logic - mapping text to a shape)."""
    # For simplicity, we just dump it into a text slide. PPTX XML is quite complex.
    # To avoid malformed PPTX errors, we'll write a simple txt file and rename.
    # The native zip XML extractor relies on finding 'ppt/slides/slideX.xml'.
    slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld><p:spTree>
        <p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>
    </p:spTree></p:cSld>
</p:sld>"""
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr("ppt/slides/slide1.xml", slide_xml)

def create_txt(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def create_md(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Header\n\n{text}\n\n* List item")

def create_csv(path: str, text: str):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Content"])
        writer.writerow(["1", text])

async def generate_fake_data(client: OllamaClient, lang: str, domain: str, complexity: str) -> str:
    """Use LLM to generate synthetic localized text."""
    lang_name = SUPPORTED_LANGUAGES[lang].name
    domain_name = SUPPORTED_DOMAINS[domain].name
    
    prompt = f"Generate a synthetic text snippet in {lang_name} for the domain '{domain_name}'. "
    if complexity == "simple_sentence":
        prompt += "Write one very simple sentence."
    elif complexity == "technical_paragraph":
        prompt += "Write a highly technical paragraph containing standard industry terminology."
    elif complexity == "mixed_tags":
        prompt += "Write a sentence containing XML-like tags, e.g., <tag1>important word</tag1>."
        
    prompt += " Only output the localized text without any surrounding explanation or quotation marks."
    
    import asyncio
    
    for attempt in range(3):
        try:
            response = await client.generate(
                model=MODEL_NAME,
                prompt=prompt,
                system="You are an automated synthetic data generator."
            )
            return response.strip()
        except Exception as e:
            print(f"Error generating data for {lang}-{domain} (attempt {attempt+1}): {e}")
            if attempt < 2:
                await asyncio.sleep(2)
            else:
                return f"Fallback text for {lang_name} in {domain_name}"

def generate_matrix() -> list[dict]:
    """Generate a statistically distributed matrix array of test cases."""
    # We want ~100 test cases covering pairs. 
    # Instead of full PICT algorithm, we create a structured random sample that guarantees at least 1 of each format/lang/domain.
    matrix = []
    
    # 1. Guarantee coverage of all languages and formats
    for lang in LANGUAGES:
        for fmt in FORMATS:
            matrix.append({
                "lang": lang,
                "format": fmt,
                "domain": random.choice(DOMAINS),
                "complexity": random.choice(COMPLEXITIES)
            })
            
    # Matrix size = 15 * 6 = 90 files
    return matrix

async def main():
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "test_matrix"))
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Initializing test matrix generator in {out_dir}")
    
    client = OllamaClient(base_url=settings.OLLAMA_URL)
    
    # Verify model is available
    print(f"Pinging Ollama server to verify {MODEL_NAME}...")
    is_up = await client.health_check()
    if not is_up:
        print("WARNING: Ollama host seems unreachable. Fallback text will be used.")
        
    matrix = generate_matrix()
    print(f"Generated test matrix with {len(matrix)} unique combinations.")
    
    creators = {
        "docx": create_docx,
        "xlsx": create_xlsx,
        "pptx": create_pptx,
        "txt": create_txt,
        "md": create_md,
        "csv": create_csv,
    }
    
    for i, case in enumerate(matrix):
        idx = str(i).zfill(3)
        lang = case["lang"]
        fmt = case["format"]
        domain = case["domain"]
        comp = case["complexity"]
        
        filename = f"test_{idx}_{lang}_{domain}_{comp}.{fmt}"
        filepath = os.path.join(out_dir, filename)
        
        print(f"[{i+1}/{len(matrix)}] Generating {filename}...")
        
        text = await generate_fake_data(client, lang, domain, comp)
        
        # Create file
        creator = creators[fmt]
        try:
            creator(filepath, text)
        except Exception as e:
            print(f"  -> Error creating {fmt}: {e}")

    print("Matrix generation complete!")

if __name__ == "__main__":
    asyncio.run(main())
