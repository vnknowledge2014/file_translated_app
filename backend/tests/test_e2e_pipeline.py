import os
import shutil
import tempfile
import zipfile
import pytest

from app.agent.extractor import extract_xlsx, extract_docx, extract_pptx
from app.agent.reconstructor import reconstruct_xlsx, reconstruct_docx, reconstruct_pptx

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), '../../samples')
TEST_XLSX = os.path.join(SAMPLES_DIR, '【基本設計書】依頼届出_雇保給付金申請_高年齢_画面設計_202510.xlsx')

def test_full_pipeline_xlsx():
    """
    End-to-End pipeline simulation without invoking the slow Ollama LLM.
    Ensures that Native parsing extracts segments, and Native reconstructing
    safely rebuilds the file with zero corruption.
    """
    if not os.path.exists(TEST_XLSX):
        pytest.skip(f"E2E test skipped: {TEST_XLSX} missing.")
        
    # 1. Extraction
    segments = extract_xlsx(TEST_XLSX)
    assert len(segments) > 0, "Failed to extract translatable Japanese strings."
    
    # 2. Mock Translation (just append _vi)
    translated_segments = []
    for seg in segments:
        text = seg['text']
        translated_segments.append({
            'text': text,
            'translated_text': text + " _vi"
        })
        
    # 3. Reconstruction
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "e2e_output.xlsx")
        
        # Native ZIP Reconstruction
        reconstruct_xlsx(TEST_XLSX, translated_segments, output_path)
        
        # 4. Validation
        assert os.path.exists(output_path), "Failed to generate output file"
        
        orig_size = os.path.getsize(TEST_XLSX)
        clone_size = os.path.getsize(output_path)
        size_diff = abs(orig_size - clone_size) / orig_size
        
        # Size should only realistically drift by a couple percentages at maximum, 
        # compared to 40% drift seen previously with openpyxl drawing droppings.
        assert size_diff < 0.10, f"Size radically drifted: {orig_size} -> {clone_size}"
        
        # Ensure it is a valid Zip Archive
        with zipfile.ZipFile(output_path, 'r') as zout:
            assert 'xl/sharedStrings.xml' in zout.namelist()
            assert 'xl/drawings/drawing1.xml' in zout.namelist() or 'xl/drawings/vmlDrawing1.vml' in zout.namelist()
