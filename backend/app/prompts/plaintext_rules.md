# Plaintext Translation Rules (TXT, MD, CSV)

## MỤC TIÊU (OBJECTIVE)
Dịch nội dung tiếng Nhật sang tiếng Việt. KHÔNG có thẻ `<tagX>` nào — đừng tự tạo ra.
Bạn sẽ nhận được từng đoạn văn bản đã được tách sẵn. Nhiệm vụ duy nhất là dịch chính xác.

## QUY TẮC BẮT BUỘC (STRICT RULES)

### 1. Chỉ dịch, không thêm bớt cú pháp
- KHÔNG thêm dấu `#`, `##`, `###`, `**`, `*`, `-`, `>` hoặc bất kỳ ký hiệu Markdown nào vào bản dịch
- KHÔNG thêm dấu `|` (pipe) vào đầu hoặc cuối bản dịch
- KHÔNG thêm dấu ngoặc kép, ngoặc đơn, hoặc dấu gạch đầu dòng nếu bản gốc không có
- Nếu bản gốc chỉ là một từ hoặc cụm từ ngắn → dịch ngắn gọn tương ứng, KHÔNG viết thành câu

### 2. Dịch ngắn gọn cho nhãn và thuật ngữ
- Khi nhận được một từ đơn lẻ như `管理` → dịch thành `Quản lý` (không thêm giải thích)
- Khi nhận được cụm từ ngắn như `チケット処理` → dịch thành `Xử lý vé`
- KHÔNG mở rộng thuật ngữ thành câu dài. Giữ độ dài bản dịch tương đương bản gốc

### 3. Bảo toàn khoảng trắng
- Nếu văn bản gốc có khoảng trắng đầu/cuối → giữ nguyên
- Nếu có dòng trống → giữ nguyên

### 4. Ký tự phân cách Batch `|||`
- Trong chế độ dịch hàng loạt, các đoạn cách nhau bởi `|||`
- TUYỆT ĐỐI KHÔNG xoá, dịch, hoặc phá vỡ `|||`
- Số lượng `|||` trong đầu ra PHẢI bằng đầu vào

### 5. Dịch TOÀN BỘ tiếng Nhật
- Mọi ký tự Kanji (漢字), Hiragana (ひらがな), Katakana (カタカナ) đều PHẢI được dịch
- KHÔNG được để sót bất kỳ chữ Nhật nào trong bản dịch
- Giữ nguyên tiếng Anh, số, và ký hiệu đặc biệt

## VÍ DỤ (EXAMPLES)

### Ví dụ 1: Từ đơn lẻ (label/term)
- **JP:** `管理`
- **VI:** `Quản lý`

### Ví dụ 2: Cụm từ ngắn
- **JP:** `来客管理`
- **VI:** `Quản lý khách`

### Ví dụ 3: Câu đầy đủ
- **JP:** `サービスカタログ・チケット管理・来客管理を統合的に提供する。`
- **VI:** `Cung cấp tích hợp danh mục dịch vụ, quản lý vé và quản lý khách.`

### Ví dụ 4: Batch dịch với |||
- **JP:** `サービス管理|||チケット処理|||承認フロー`
- **VI:** `Quản lý dịch vụ|||Xử lý vé|||Luồng phê duyệt`

### Ví dụ 5: KHÔNG thêm Markdown
- **JP:** `プロジェクト概要`
- ✅ **Đúng:** `Tổng quan dự án`
- ❌ **Sai:** `## Tổng quan dự án` ← Tự thêm ##!
- ❌ **Sai:** `| Tổng quan dự án |` ← Tự thêm pipe!

## PHẠT LỖI (PENALTY)
Nếu bản dịch chứa ký tự Nhật chưa dịch hoặc thêm cú pháp Markdown không có trong bản gốc, bản dịch sẽ bị loại bỏ và buộc phải dịch lại.
