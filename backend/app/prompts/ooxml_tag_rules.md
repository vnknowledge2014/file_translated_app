# OOXML Inline Tag Translation Rules (DOCX, PPTX, XLSX)

## MỤC TIÊU (OBJECTIVE)
Khi dịch văn bản từ các tệp Office (Word, PowerPoint, Excel), văn bản sẽ chứa các thẻ đánh dấu định dạng `<tagX>...</tagX>`. Các thẻ này đại diện cho in đậm, đổi màu, font chữ, v.v. trong tệp gốc.
**SỐ LƯỢNG VÀ THỨ TỰ CỦA CÁC THẺ `<tagX>` PHẢI ĐƯỢC BẢO TOÀN NGUYÊN VẸN 100%.** Mọi sự thất thoát thẻ đều sẽ dẫn đến việc tệp đầu ra bị hỏng (Corrupted).

## QUY TẮC BẤT KHẢ XÂM PHẠM (STRICT RULES)
1. **Tuyệt đối không** xóa bất kỳ thẻ `<tagX>` và `</tagX>` nào.
2. **Tuyệt đối không** tự tạo thêm thẻ `<tagX>` mới nếu bản gốc không có.
3. Nội dung bên trong cặp thẻ `<tagX>Nội dung</tagX>` bắt buộc phải được dịch ra tiếng Việt và đặt đúng vào giữa cặp thẻ tương ứng.
4. Đảm bảo ngữ pháp tiếng Việt mượt mà ngay cả khi chữ bị cắt ngang bởi thẻ.
5. **Ranh giới từ tiếng Việt:** Tiếng Việt dùng dấu cách tách từ. PHẢI có dấu cách giữa từ tiếng Việt và thẻ tag. KHÔNG ĐƯỢC để chữ dính sát vào thẻ.
6. **Bảo toàn khoảng trắng:** Nếu văn bản gốc có khoảng trắng ở đầu/cuối, PHẢI giữ nguyên. Ví dụ: ` テスト ` → ` Kiểm thử `.
7. **Bảo toàn thẻ rỗng:** Nếu cặp thẻ không chứa nội dung (vd: `<tag1></tag1>`), PHẢI giữ nguyên, KHÔNG được xoá.

## VÍ DỤ (EXAMPLES)

### Ví dụ 1: In đậm
- **JP:** これは<tag1>重要</tag1>なポイントです。
- **VI:** Đây là một điểm <tag1>quan trọng</tag1>.

### Ví dụ 2: Nhiều thẻ
- **JP:** <tag1>赤色</tag1>と<tag2>青色</tag2>を選択してください。
- **VI:** Vui lòng chọn <tag1>màu đỏ</tag1> và <tag2>màu xanh</tag2>.

### Ví dụ 3: Đảo ngữ pháp JP↔VI
- **JP:** <tag1>システム</tag1>の<tag2>設定ファイル</tag2>を更新する。
- **VI:** Cập nhật <tag2>tệp cấu hình</tag2> của <tag1>hệ thống</tag1>.

### Ví dụ 4: Dấu cách bắt buộc (QUAN TRỌNG)
- **JP:** <tag1>会社</tag1>の<tag2>規則</tag2>に従ってください。
- ✅ **Đúng:** Hãy tuân theo <tag2>quy tắc</tag2> của <tag1>công ty</tag1>.
- ❌ **Sai:** Hãy tuân theo<tag2>quy tắc</tag2>của<tag1>công ty</tag1>. ← Thiếu dấu cách!

### Ví dụ 5: Thẻ rỗng
- **JP:** 結果は<tag1></tag1>以下の通りです。
- **VI:** Kết quả <tag1></tag1>như sau.

## PHẠT LỖI (PENALTY)
Bất kỳ kết quả nào bị thiếu dù chỉ 1 thẻ sẽ bị chặn bởi Python Validator và buộc phải dịch lại.
