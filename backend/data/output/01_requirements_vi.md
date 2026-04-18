# Office OS - Tài liệu định nghĩa yêu cầu

## 1. Tổng quan dự án

### 1.1 Tên dự án
**Office OS** - Nền tảng quản lý văn phòng tích hợp

### 1.2 Tầm nhìn
Nền tảng SaaS cung cấp tích hợp các chức năng cần thiết cho nghiệp vụ văn phòng như danh mục dịch vụ, quản lý vé, quản lý khách, đặt phòng cơ sở vật chất, tri thức, quản lý sự kiện, bản đồ tầng, v.v.
Quản trị viên định nghĩa luồng nghiệp vụ, thành viên trong công ty sử dụng, và tác nhân xử lý, quản lý. Trong tương lai, đây sẽ là hub kết nối với các tác nhân AI.

### 1.3 Sơ đồ khái niệm

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                  Thành viên trong công ty(Requester)                              │
│                                                                                   │
│  ┌────────────────┐ ┌───────────┐ ┌──────────────────────────┐ ┌──────────┐       │
│  │ Dịch vụ        │ │ Kiến thức │ │ Đặt phòng cơ sở vật chất │ │ Sự kiện  │       │
│  │ Cổng thông tin │ │ Xem       │ │                          │ │ Tham gia │       │
│  └────────┬───────┘ └─────┬─────┘ └─────────────┬────────────┘ └─────┬────┘       │
│           │               │                     │                    │            │
└───────────┼───────────────┼─────────────────────┼────────────────────┼────────────┘
            │               │                     │                    │
            ▼               ▼                     ▼                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                      Office OS                                             │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                   REST API Layer                                   │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│  ┌──────────┐ ┌───────────────┐ ┌────────────────────┐ ┌───────────┐       │
│  │ Dịch vụ  │ │ Quản lý khách │ │ Đặt cơ sở vật chất │ │ Kiến thức │       │
│  │ Danh mục │ │               │ │                    │ │ Cơ sở     │       │
│  └──────────┘ └───────────────┘ └────────────────────┘ └───────────┘       │
│                                                                            │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐                      │
│  │ Vé       │ │ Thông báo │ │ Sự kiện  │ │ Tầng     │                      │
│  │ Quản lý  │ │           │ │ Quản lý  │ │ Bản đồ   │                      │
│  └──────────┘ └───────────┘ └──────────┘ └──────────┘                      │
│                                                                            │
│  ┌───────────┐ ┌───────────────────┐ ┌─────────────┐                       │
│  │ Phê duyệt │ │ RBAC              │ │ RAG Chat    │                       │
│  │ Công việc │ │ Quản lý quyền hạn │ │ (Tương lai) │                       │
│  │ Luồng     │ │                   │ │             │                       │
│  └───────────┘ └───────────────────┘ └─────────────┘                       │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │              PostgreSQL + pgvector                                 │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│          Agent / Quản trị viên(Agent / Admin)                            │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ Màn hình quản lý(Xử lý vé / Phê duyệt/ Chỉnh sửa kiến thức/     │     │
│  │ Tiếp đón khách/ Quản lý cơ sở vật chất/ Vận hành sự kiện)       │     │
│  └─────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Người dùng và vai trò

### 2.1 Kiến trúc 3 chế độ

| Chế độ | Route | Đối tượng | Tổng quan |
|--------|--------|------|------|
| Chế độ yêu cầu | `(requester)/` | Thành viên nội bộ | Xem danh mục, yêu cầu, xem kiến thức, đặt cơ sở vật chất, tham gia sự kiện |
| Chế độ xử lý | `agent/` | Agent | Xử lý vé, phê duyệt, tiếp khách, quản lý kiến thức, vận hành sự kiện |
| Chế độ quản lý | `admin/` | Quản trị viên | Thiết lập danh mục, quản lý tổ chức, quản lý master |

### 2.2 Định nghĩa vai trò

| Vai trò | Mô tả | Phương pháp xác thực |
|--------|------|----------|
| **SystemAdmin** | Quản trị viên toàn hệ thống. Tạo tenant, thiết lập hệ thống | Google Workspace |
| **Admin** | Quản trị viên tenant. Thiết lập danh mục, quản lý thành viên, thiết lập tổ chức | Google Workspace |
| **Agent** | Người xử lý. Xử lý vé, quản lý khách, quản lý kiến thức, vận hành sự kiện | Google Workspace |
| **Approver** | Người phê duyệt. Thực hiện phê duyệt/từ chối trong luồng phê duyệt (có thể kiêm nhiệm Agent) | Google Workspace |
| **Requester** | Thành viên nội bộ. Yêu cầu danh mục, xem kiến thức, đặt cơ sở vật chất, tham gia sự kiện | Google Workspace |
| **APIClient** | Hệ thống bên ngoài (CLI/MCP/AI agent) | API key |

### 2.3 Cấu hình đa thuê bao

```
SystemAdmin (Office O S Vận hành)
  ├── Tenant A (Doanh nghiệp A)
  │     ├── Admin
  │     ├── Agent (Nhiều) ── Một phần Approver Kiêm nhiệm
  │     └── Requester (Nhiều)
  ├── Tenant B (Doanh nghiệp B)
  │     ├── Admin
  │     ├── Agent (Nhiều)
  │     └── Requester (Nhiều)
  └── ...
```

- Dữ liệu giữa các tenant được tách biệt hoàn toàn
- 1 người dùng có thể thuộc nhiều tenant
- 1 người dùng có thể kiêm nhiệm nhiều vai trò

---

## 3. Danh sách mô-đun chức năng

### 3.1 Quản lý tổ chức

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| ORG-001 | Quản lý thành viên | Mời, quản lý và vô hiệu hóa thành viên tenant |
| ORG-002 | Quản lý nhóm chức năng | Sử dụng để kiểm soát phạm vi công khai của mục dịch vụ, khả năng hiển thị của agent và nhóm phê duyệt. Hỗ trợ cấu trúc cây |
| ORG-003 | Quản lý vai trò | Định nghĩa vai trò và phân quyền bằng RBAC |
| ORG-004 | Quản lý bộ phận | Cấu trúc cây đa cấp (Bộ phận > Phòng > Tổ). Thiết lập trưởng bộ phận. Sử dụng để tự động giải quyết cấp trên trong luồng phê duyệt |
| ORG-005 | Quản lý chi nhánh | Đăng ký và quản lý chi nhánh. Liên kết với bản đồ tầng, quản lý khách và đặt cơ sở vật chất |

> Chi tiết: `docs/10_rbac_spec.md`

### 3.2 Danh mục dịch vụ

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| CAT-001 | Quản lý mục dịch vụ | Tạo, công khai menu yêu cầu và định nghĩa trường tùy chỉnh |
| CAT-002 | Trường tùy chỉnh | Xây dựng biểu mẫu động. Phân nhánh điều kiện, xác thực và liên kết nguồn dữ liệu |
| CAT-003 | Quản lý danh mục | Phân loại danh mục mục dịch vụ |
| CAT-004 | Kiểm soát phạm vi công khai | Kiểm soát hiển thị mục theo nhóm chức năng |
| CAT-005 | Thiết lập chi phí và thời hạn giao hàng | Đơn giá tiêu chuẩn, thời gian tiêu chuẩn SLA, thời hạn dự kiến |
| CAT-006 | Nguồn dữ liệu | Lấy các tùy chọn của trường tùy chỉnh từ master bên ngoài |

> Chi tiết: `docs/20_service_catalog_spec.md`

### 3.3 Quản lý vé

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| TKT-001 | Danh sách/Tìm kiếm vé | Lọc theo trạng thái, mức độ ưu tiên, loại và kênh |
| TKT-002 | Xử lý vé | Quản lý trạng thái, chỉ định người phụ trách, bình luận, ghi chú nội bộ |
| TKT-003 | Xuất CSV | Xuất bao gồm các mục trường tùy chỉnh |
| TKT-004 | Tự động tính tổng tiền | Lưu số tiền xác định bằng Đơn giá × Số lượng |
| TKT-005 | Quản lý SLA | Tự động tính hạn giải quyết và cảnh báo quá hạn |
| TKT-006 | Vé định kỳ | Tự động tạo vé dựa trên lịch trình |
| TKT-007 | Yêu cầu của tôi | Danh sách vé và xác nhận tiến độ của người yêu cầu |

> Chi tiết: `docs/21_ticket_spec.md`, `docs/24_recurring_ticket_spec.md`

### 3.4 Luồng phê duyệt

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| APR-001 | Phê duyệt nhiều cấp | Phê duyệt nhiều cấp tuần tự. Bỏ qua có điều kiện |
| APR-002 | Loại bước phê duyệt | Người dùng cụ thể / Phê duyệt nhóm / Cấp trên tự động giải quyết / Trưởng bộ phận |
| APR-003 | Phê duyệt thay thế・Ủy quyền | Ủy quyền quyền phê duyệt theo thời gian chỉ định |
| APR-004 | Hạn chót phê duyệt và leo thang | Nhắc nhở trước hạn và xử lý tự động khi quá hạn |
| APR-005 | Trả lại và yêu cầu phê duyệt lại | Chỉnh sửa sau khi bị từ chối và khởi động lại luồng phê duyệt |

> Chi tiết: `docs/22_approval_flow_spec.md`, `docs/23_approval_flow_guide.md`

### 3.5 Quản lý khách

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| VST-001 | Đặt lịch hẹn khách | Đăng ký ngày giờ thăm, người tiếp đón, mục đích và thông tin khách |
| VST-002 | Quản lý trạng thái đến thăm | Chuyển đổi trạng thái: Dự kiến → Đến nơi → Đang phỏng vấn → Rời đi |
| VST-003 | Trường tùy chỉnh theo chi nhánh | Các mục biểu mẫu riêng cho từng chi nhánh |
| VST-004 | Mục dịch vụ khách | Đơn xin dịch vụ bổ sung gắn với đặt lịch khách |
| VST-005 | Quản lý tài sản・Cho mượn | Quản lý cho mượn・trả thẻ khách và thiết bị |

> Chi tiết: `docs/30_visitor_management_spec.md`, `docs/31_visitor_service_items_spec.md`

### 3.6 Đặt cơ sở vật chất

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| FAC-001 | Quản lý loại cơ sở vật chất | Quản lý phân loại phòng họp, chỗ ngồi, không gian sự kiện, thiết bị |
| FAC-002 | Đặt chỗ cơ sở vật chất | Tạo đặt chỗ và kiểm tra trùng lặp trên UI lịch |
| FAC-003 | Đặt chỗ lặp lại | Mẫu đặt chỗ định kỳ |
| FAC-004 | Liên kết quản lý khách đến | Đặt trước phòng họp đồng thời từ đặt lịch khách đến (tương lai) |

> Chi tiết: `docs/40_facility_reservation_spec.md`

### 3.7 Bản đồ tầng

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| FLR-001 | Quản lý bản vẽ tầng | Tải lên hình ảnh bản vẽ tầng theo từng chi nhánh |
| FLR-002 | Đặt ghim | Đặt ghim vị trí chỗ ngồi, phòng họp, thiết bị |
| FLR-003 | Xem bản đồ tầng | Thu phóng, di chuyển, hiển thị chi tiết ghim, tìm kiếm người dùng |

> Chi tiết: `docs/41_floor_map_spec.md`

### 3.8 Thông báo

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| ANN-001 | Quản lý thông báo | Tạo, công khai và quản lý thời hạn bài viết bằng rich text (tiptap) |
| ANN-002 | Kiểm soát đối tượng công khai | Hạn chế xem theo Toàn bộ / Bộ phận / Nhóm chỉ định |
| ANN-003 | Quản lý trạng thái đã đọc | Theo dõi đã đọc/chưa đọc |
| ANN-004 | Quản lý danh mục | Quản lý master danh mục thông báo |

> Chi tiết: `docs/50_announcement_spec.md`

### 3.9 Quản lý sự kiện

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| EVT-001 | CRU D sự kiện | Tạo và công khai sự kiện bằng rich text |
| EVT-002 | Loại vé ・ Đăng ký tham gia | Định nghĩa nhiều loại vé và đăng ký tham gia |
| EVT-003 | Quản lý điểm danh | Tiếp đón bằng mã QR và check-in thủ công |
| EVT-004 | Công khai ra ngoài và khách tham gia | Trang công khai không cần xác thực và khách tham gia qua email |
| EVT-005 | Khảo sát | Khảo sát và tổng hợp dựa trên trường tùy chỉnh |
| EVT-006 | Phân tích | Phân tích tỷ lệ tham dự, tỷ lệ quay lại và theo thuộc tính |

> Chi tiết: `docs/51_event_management_spec.md`

### 3.10 Cơ sở kiến thức

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| KNW-001 | Bài viết kiến thức | Tạo FAQ, hướng dẫn, quy trình bằng rich text (tiptap) |
| KNW-002 | Thư viện tệp | Quản lý tài liệu như PDF, Word |
| KNW-003 | Mẫu | Định nghĩa và lựa chọn mẫu tạo bài viết |
| KNW-004 | Kiểm soát đối tượng công khai | Hạn chế xem theo bộ phận/nhóm |
| KNW-005 | Danh mục/Thẻ | Phân loại theo danh mục phân cấp + thẻ phẳng |
| KNW-006 | Chuẩn bị dữ liệu RAG | Pipeline vector hóa (bài viết, tệp, vé, v.v.) |
| KNW-007 | RAG Chat | AI chat tìm kiếm kiến thức để trả lời (tương lai) |

> Chi tiết: `docs/60_knowledge_base_spec.md`

### 3.11 Liên kết hệ thống bên ngoài (tương lai)

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| EXT-001 | Liên kết API / CLI / MCP | Tạo vé và cập nhật trạng thái từ bên ngoài |
| EXT-002 | Liên kết Salesforce | Đồng bộ hóa trường hợp và leo thang |

### 3.12 Quản lý SaaS (Dành cho vận hành)

| ID | Tên chức năng | Chi tiết |
|----|--------|------|
| SAS-001 | Quản lý tenant | Tạo và quản lý trạng thái tenant |
| SAS-002 | Quản lý gói | Định nghĩa gói và gán cho tenant |
| SAS-003 | Giám sát tình trạng sử dụng | Số lượng thành viên, số lượng vé và dung lượng lưu trữ theo từng tenant |

> Chi tiết: `docs/71_saas_admin_spec.md`

---

## 4. Yêu cầu phi chức năng

### 4.1 Xác thực và Bảo mật

| Hạng mục | Yêu cầu |
|------|------|
| Xác thực | Google Workspace OAuth 2.0 (OIDC) |
| Ủy quyền | RBAC (Kiểm soát truy cập dựa trên vai trò) + Phân cấp quyền hạn |
| Phân tách dữ liệu | Phân tách dữ liệu hoàn toàn giữa các tenant |
| Truyền thông | Bắt buộc HTTPS |
| API key | Lưu hash SHA-256 (tương lai) |
| Session | Chiến lược JWT (lưu Cookie), có thời hạn hiệu lực |

### 4.2 Hiệu suất

| Hạng mục | Giá trị mục tiêu |
|------|--------|
| Tải trang | < 2 giây (lần đầu) |
| Phản hồi API | < 500ms (Percentile thứ 95) |
| Kết nối đồng thời | Hỗ trợ quy mô 100.000 người dùng |

### 4.3 Tính khả dụng và vận hành

| Hạng mục | Yêu cầu |
|------|------|
| Tỷ lệ hoạt động | 99.5% |
| Triển khai | Google Cloud Run (Container) |
| DB | Cloud SQL for PostgreSQL + pgvector |
| Lưu trữ | Google Cloud Storage |
| Giám sát | Cloud Monitoring / Cloud Logging / Sentry |
| Sao lưu | Cloud SQ L lưu giữ 30 ngày + PITR 7 ngày, GCS Versioning |

### 4.4 Stack kỹ thuật

| Lớp | Kỹ thuật |
|----------|------|
| Frontend | Next.js 15 (App Router) / React 19 / TypeScript |
| Styling | Tailwind CSS v3 / shadcn/ui |
| Backend | Next.js API Routes (Route Handlers) |
| ORM | Prisma 6 |
| DB | PostgreSQL 17 + pgvector |
| Auth | NextAuth.js v5 (Auth.js) / Google Provider |
| Rich text | tiptap |
| Embedding | Vertex AI (text-embedding-004) |
| LLM | Gemini API (Vertex AI) |
| Deploy | Google Cloud Run |
| CI/CD | GitHub Actions |
| Container | Docker |
| Giám sát | Sentry + Cloud Monitoring |

---

## 5. Định nghĩa thuật ngữ

| Thuật ngữ | Định nghĩa |
|------|------|
| **Tenant** | Tổ chức khách hàng sử dụng Office OS |
| **Service Catalog** | Tập hợp các mục dịch vụ có thể yêu cầu |
| **Mục dịch vụ (Service Item)** | Một menu yêu cầu trong danh mục (Ví dụ: Yêu cầu mua P C, đặt danh thiếp) |
| **Vé (Ticket)** | Đơn vị yêu cầu/đề nghị mà người yêu cầu tạo ra sau khi chọn mục dịch vụ |
| **Trường tùy chỉnh (Custom Field)** | Các mục biểu mẫu nhập liệu động liên kết với item dịch vụ |
| **Nhân viên hỗ trợ (Agent)** | Người phụ trách xử lý vé, tiếp khách và quản lý kiến thức |
| **Người yêu cầu (Requester)** | Thành viên nội bộ yêu cầu dịch vụ từ danh mục |
| **Người phê duyệt (Approver)** | Người thực hiện phê duyệt/từ chối trong luồng phê duyệt |
| **Bộ phận (Department)** | Đơn vị cấu thành phân cấp tổ chức trong tenant. Được sử dụng để tự động giải quyết cấp trên |
| **Nhóm chức năng (TenantGroup)** | Nhóm được sử dụng để kiểm soát phạm vi công khai và quản lý quyền hạn. Hỗ trợ cấu trúc cây |
| **Chi nhánh (Location)** | Địa điểm văn phòng vật lý. Liên kết với quản lý khách, đặt cơ sở vật chất và bản đồ tầng |
| **Kiến thức (Knowledge)** | Tài liệu nội bộ như FAQ, hướng dẫn, quy trình |
| **RAG** | Retrieval-Augmented Generation. Cơ chế AI tìm kiếm kiến thức để trả lời |
| **SLA** | Service Level Agreement. Thỏa thuận về thời hạn giải quyết vé |

---

## 6. Danh sách tài liệu

### Tài liệu nền tảng

| # | Tệp | Nội dung |
|---|---------|------|
| 01 | `01_requirements.md` | Định nghĩa yêu cầu (tài liệu này) |
| 02 | `02_data_model.md` | Thiết kế mô hình dữ liệu |
| 03 | `03_screen_spec.md` | Thông số màn hình |
| 04 | `04_api_spec.md` | Thông số API |
| 05 | `05_roadmap.md` | Lộ trình phát triển |
| 06 | `06_development_rules.md` | Quy tắc phát triển ・ Quy ước lập trình |

### Quản lý tổ chức

| # | Tệp | Nội dung |
|---|---------|------|
| 10 | `10_rbac_spec.md` | RBAC・Quyền hạn・Vai trò・Nhóm・Kiểm soát phạm vi công khai |

### Danh mục dịch vụ

| # | Tệp | Nội dung |
|---|---------|------|
| 20 | `20_service_catalog_spec.md` | Danh mục dịch vụ, trường tùy chỉnh, phân nhánh điều kiện |
| 21 | `21_ticket_spec.md` | Quản lý vé |
| 22 | `22_approval_flow_spec.md` | Thông số luồng phê duyệt |
| 23 | `23_approval_flow_guide.md` | Hướng dẫn sử dụng luồng phê duyệt |
| 24 | `24_recurring_ticket_spec.md` | Tự động đăng ký vé định kỳ |

### Quản lý khách

| # | Tệp | Nội dung |
|---|---------|------|
| 30 | `30_visitor_management_spec.md` | Quản lý khách |
| 31 | `31_visitor_service_items_spec.md` | Mục dịch vụ khách |

### Quản lý cơ sở vật chất

| # | Tệp | Nội dung |
|---|---------|------|
| 40 | `40_facility_reservation_spec.md` | Đặt chỗ cơ sở vật chất |
| 41 | `41_floor_map_spec.md` | Sơ đồ tầng |

### Chia sẻ thông tin

| # | Tệp | Nội dung |
|---|---------|------|
| 50 | `50_announcement_spec.md` | Thông báo |
| 51 | `51_event_management_spec.md` | Quản lý sự kiện |

### Kiến thức・AI

| # | Tệp | Nội dung |
|---|---------|------|
| 60 | `60_knowledge_base_spec.md` | Cơ sở kiến thức・RAG |

### Hạ tầng・Vận hành

| # | Tệp | Nội dung |
|---|---------|------|
| 70 | `70_gcp_deployment.md` | Quy trình triển khai GCP |
| 71 | `71_saas_admin_spec.md` | Trang quản lý SaaS |

### Tham khảo

| # | Tệp | Nội dung |
|---|---------|------|
| 90 | `90_implementation_status.md` | Trạng thái triển khai |
