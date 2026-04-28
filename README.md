# Drive Health Monitor

Một ứng dụng Windows đơn giản để theo dõi sức khỏe ổ cứng, tự động thu thập dữ liệu từ CrystalDiskInfo và xuất ra file CSV mỗi 5 phút.

## Các tính năng chính

- Chạy ngầm dưới khay hệ thống (System Tray).
- Tự động chạy cùng Windows (Startup).
- Giao diện GUI đơn giản với bộ đếm ngược thời gian.
- Tự động thu thập thông số SMART, nhiệt độ và thời gian sử dụng ổ cứng.
- Xuất báo cáo định dạng CSV theo ngày (Hard_drive_summary_YYYYMMDD.csv).

## Yêu cầu hệ thống

- Windows 10 hoặc 11.
- Quyền Administrator (để đọc thông số SMART).
- CrystalDiskInfo (DiskInfo64.exe) phải nằm cùng thư mục với chương trình.

## Hướng dẫn cài đặt nhanh

1. Tải về và giải nén gói DriveMonitor.
2. Nhấp đúp chuột vào file `install.bat`.
3. Chương trình sẽ tự động:
   - Copy vào thư mục `C:\DriveMonitor`.
   - Đăng ký khởi động cùng Windows.
   - Kích hoạt ứng dụng ngay lập tức.

## Cấu hình (config.json)

Bạn có thể tùy chỉnh các thông số sau trong file `config.json`:

- `Process`: Tên tiến trình hoặc dự án.
- `Machine`: Tên máy trạm hoặc server.
- `PC`: Tên máy tính (nếu để trống sẽ tự động lấy theo Windows).
- `IP`: Địa chỉ IP (nếu để trống sẽ tự động lấy IP của máy).
- `OutputPath`: Đường dẫn thư mục lưu file CSV (nếu để trống sẽ lưu tại thư mục cài đặt).

## Hướng dẫn cho lập trình viên

### Yêu cầu môi trường
- Python 3.12+
- Thư viện: `pystray`, `Pillow`

### Đóng gói ứng dụng
Sử dụng PyInstaller để tạo file EXE duy nhất:

```bash
pyinstaller --noconsole --onefile --uac-admin --name DriveMonitor drive_monitor_gui.py
```

## Lưu ý
Chương trình này sử dụng dữ liệu từ CrystalDiskInfo bằng cách gọi lệnh `/CopyExit`. Đảm bảo file `DiskInfo64.exe` và thư mục `CdiResource` luôn hiện diện cùng cấp với file thực thi.
