import os
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import pytest

# Paths
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), '../../samples')
TEST_XLSX = os.path.join(SAMPLES_DIR, '【基本設計書】依頼届出_雇保給付金申請_高年齢_画面設計_202510.xlsx')

def test_xlsx_native_extraction():
    """Validate that we can read sharedStrings.xml via zipfile cleanly."""
    assert os.path.exists(TEST_XLSX), "Sample file missing"
    
    namespaces = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    extracted = []
    
    with zipfile.ZipFile(TEST_XLSX, 'r') as z:
        assert 'xl/sharedStrings.xml' in z.namelist()
        xml_data = z.read('xl/sharedStrings.xml')
        root = ET.fromstring(xml_data)
        
        for si in root.findall('main:si', namespaces):
            text_runs = []
            
            # Simple <t> nodes
            t_node = si.find('main:t', namespaces)
            if t_node is not None and t_node.text:
                text_runs.append(t_node.text)
            
            # Rich text <r><t> nodes mapped exactly
            for idx, r in enumerate(si.findall('main:r', namespaces)):
                rt = r.find('main:t', namespaces)
                if rt is not None and rt.text:
                    # Mock Serialization
                    text_runs.append(f"<tag{idx+1}>{rt.text}</tag{idx+1}>")
            
            if text_runs:
                extracted.append("".join(text_runs))
                
    # Basic assertions to ensure we caught text
    assert len(extracted) > 0
    assert "作成者" in extracted
    assert "項目名" in extracted

def test_zero_corruption_clone():
    """Validate that repacking an XLSX via stream copy yields an un-corrupted file."""
    assert os.path.exists(TEST_XLSX)
    
    # 1. Setup temp environment
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, 'cloned.xlsx')
        
        # 2. Re-pack identical zip
        with zipfile.ZipFile(TEST_XLSX, 'r') as zin, \
             zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
                 
            for item in zin.infolist():
                buffer = zin.read(item.filename)
                
                # Mock a slight modification to sharedStrings.xml to simulate translation
                if item.filename == 'xl/sharedStrings.xml':
                    # Parse and modify nothing structurally, just re-serialize to prove no corruption
                    root = ET.fromstring(buffer)
                    # We just write it back using ET.tostring
                    buffer = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                
                zout.writestr(item, buffer)
        
        # 3. Assert cloned file size is reasonably close to original 
        # (might differ slightly due to compression/xml declaration, but should not be 50% smaller like openpyxl)
        orig_size = os.path.getsize(TEST_XLSX)
        clone_size = os.path.getsize(output_path)
        
        size_diff = abs(orig_size - clone_size) / orig_size
        
        # We expect highly similar sizes (< 5% drift). If openpyxl deletes drawings, drift is 20-40%.
        assert size_diff < 0.05, f"Clone size massively drifted: {orig_size} vs {clone_size}"

def test_tag_validation_logic():
    """Validate python-based RALPH guardrail logic"""
    import re
    
    original_text = "This is a <tag1>Bold</tag1> and <tag2>Red</tag2> text."
    
    # LLM translates perfectly
    good_translation = "Đây là văn bản <tag1>Đậm</tag1> và <tag2>Đỏ</tag2>."
    
    # LLM drops a tag
    bad_translation = "Đây là văn bản Đậm và <tag2>Đỏ</tag2>."
    
    def count_tags(text):
        return len(re.findall(r'<tag\d+>', text))
    
    orig_tags = count_tags(original_text)
    
    assert count_tags(good_translation) == orig_tags, "Good translation should pass"
    assert count_tags(bad_translation) != orig_tags, "Bad translation should be caught by RALPH"
