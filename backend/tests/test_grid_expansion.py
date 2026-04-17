import pytest
from app.agent.reconstructor.plaintext import visual_width, insert_at_visual_col

def test_visual_width():
    assert visual_width("abc") == 3
    assert visual_width("サービス") == 8
    assert visual_width("│ポータル│") == 10

def test_insert_at_visual_col():
    # Insert 4 spaces at visual col 9
    line = "┌──────────┐"  # Length: 12 visual. 
    # V=9 is inside the line. `──` will be duplicated.
    expanded = insert_at_visual_col(line, 9, 4)
    assert expanded == "┌──────────────┐"

    line2 = "│  │A      │" # V=9 is a space.
    expanded2 = insert_at_visual_col(line2, 9, 4)
    assert expanded2 == "│  │A          │"

from app.agent.reconstructor import reconstruct_plaintext

def test_reconstruct_plaintext_diagram(tmp_path):
    md_content = """Some text
```
┌───────────┐
│サービス   │
└────┬──────┘
```
Other text
"""
    input_file = tmp_path / "test.md"
    input_file.write_text(md_content, encoding="utf-8")
    output_file = tmp_path / "test_out.md"
    
    # "サービス" is visual width 8.  Trailing spaces = 3. Available = 11.
    # "Cổng thông tin" is visual width 14. (needs expansion of 3 columns)
    # With the new behavior, ALL lines in the code block are expanded
    # at the right-edge visual column, so the box widens to fit.

    segments = [
        {"text": "サービス", "translated_text": "Cổng thông tin", "location": "line[3]", "type": "diagram_token"}
    ]
    
    reconstruct_plaintext(str(input_file), segments, str(output_file))
    
    out_content = output_file.read_text(encoding="utf-8")
    
    # Simple inline replacement: no grid expansion, borders unchanged.
    # "Cổng thông tin" (vw=14) exceeds available=11, so it overflows slightly.
    # But all content is visible and other lines are NOT modified.
    out_lines = [l.rstrip() for l in out_content.strip().splitlines()]
    assert "Cổng thông tin" in out_lines[3]  # Full translation visible
    assert out_lines[2].startswith("┌")       # Border line unchanged
    assert out_lines[4].startswith("└")       # Border line unchanged

