# OOXML Inline Tag Translation Rules (DOCX, PPTX, XLSX)

## OBJECTIVE
When translating text from Office files, the text will contain formatting tags like `<tagX>...</tagX>`. These tags represent bold, colors, fonts, etc. in the original file.
**THE NUMBER AND ORDER OF `<tagX>` TAGS MUST BE PRESERVED 100%.** Any missing tags will corrupt the output file.

## STRICT RULES
1. **Never** delete any `<tagX>` or `</tagX>` tags.
2. **Never** invent new `<tagX>` tags that were not in the original text.
3. The text inside the tags `<tagX>Text</tagX>` MUST be translated into {{TARGET_LANG}} and placed properly between the corresponding tags.
4. Ensure smooth {{TARGET_LANG}} grammar even if a word is split by a tag.
5. **Word Boundaries:** Ensure appropriate spacing between translated words and tags based on {{TARGET_LANG}} spacing rules.
6. **Preserve Whitespace:** If the original text has leading/trailing spaces, you MUST keep them. Example: ` Test ` → ` Kiểm thử `.
7. **Preserve Empty Tags:** If a tag pair is empty (e.g. `<tag1></tag1>`), you MUST keep it exactly as `<tag1></tag1>`. Do NOT delete empty tags.

## EXAMPLES

### Example 1: Bold text
- **Source:** これは<tag1>重要</tag1>なポイントです。
- **Target:** This is an <tag1>important</tag1> point.

### Example 2: Multiple tags
- **Source:** <tag1>赤色</tag1>と<tag2>青色</tag2>を選択してください。
- **Target:** Please select <tag1>red</tag1> and <tag2>blue</tag2>.

### Example 3: Grammar inversion
- **Source:** <tag1>システム</tag1>の<tag2>設定ファイル</tag2>を更新する。
- **Target:** Update the <tag2>configuration file</tag2> of the <tag1>system</tag1>.

### Example 4: Mandatory spacing
- **Source:** <tag1>会社</tag1>の<tag2>規則</tag2>に従ってください。
- ✅ **Correct:** Please follow the <tag2>rules</tag2> of the <tag1>company</tag1>.
- ❌ **Wrong:** Please follow the<tag2>rules</tag2>of the<tag1>company</tag1>. (Missing spaces!)

### Example 5: Empty tags
- **Source:** 結果は<tag1></tag1>以下の通りです。
- **Target:** The result <tag1></tag1>is as follows.
