# Drive Health Monitor

Mot ung dung Windows don gian de theo doi suc khoe o cung, tu dong thu thap du lieu tu CrystalDiskInfo va xuat ra file CSV moi 5 phut.

## Cac tinh nang chinh

- Chay ngam duoi khay he thong (System Tray).
- Tu dong chay cung Windows (Startup).
- Giao dien GUI don gian voi bo dem nguoc thoi gian.
- Tu dong thu thap thong so SMART, nhiet do va thoi gian su dung o cung.
- Xuat bao cao dinh dang CSV theo ngay (Hard_drive_summary_YYYYMMDD.csv).

## Yeu cau he thong

- Windows 10 hoac 11.
- Quyen Administrator (de doc thong so SMART).
- CrystalDiskInfo (DiskInfo64.exe) phai nam cung thu muc voi chuong trinh.

## Huong dan cai dat nhanh

1. Tai ve va giai nen goi DriveMonitor.
2. Nhap dup chuot vao file `install.bat`.
3. Chuong trinh se tu dong:
   - Copy vao thu muc `C:\DriveMonitor`.
   - Dang ky khoi dong cung Windows.
   - Kich hoat ung dung ngay lap tuc.

## Cau hinh (config.json)

Ban co the tuy chinh cac thong so sau trong file `config.json`:

- `Process`: Ten tien trinh hoac du an.
- `Machine`: Ten may tram hoac server.
- `PC`: Ten may tinh (neu de trong se tu dong lay theo Windows).
- `IP`: Dia chi IP (neu de trong se tu dong lay IP cua may).
- `OutputPath`: Duong dan thu muc luu file CSV (neu de trong se luu tai thu muc cai dat).

## Huong dan cho lap trinh vien

### Yeu cau moi truong
- Python 3.12+
- Thu vien: `pystray`, `Pillow`

### Dong goi ung dung
Su dung PyInstaller de tao file EXE duy nhat:

```bash
pyinstaller --noconsole --onefile --uac-admin --name DriveMonitor drive_monitor_gui.py
```

## Luu y
Chuong trinh nay su dung du lieu tu CrystalDiskInfo bang cach goi lenh `/CopyExit`. Dam bao file `DiskInfo64.exe` va thu muc `CdiResource` luon hien dien cung cap voi file thuc thi.
