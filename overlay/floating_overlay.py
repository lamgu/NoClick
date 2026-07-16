from PySide6.QtWidgets import QWidget, QLabel, QApplication, QHBoxLayout
from PySide6.QtCore import Qt, QTimer

class FloatingOverlay(QWidget):
    def __init__(self):
        super().__init__()
        # Membuat jendela transparan total, selalu di atas, tanpa border, dan tidak mengganggu klik mouse (clik-through)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Area lebar jendela agar lingkaran bisa bergerak bebas ke kanan/kiri di tengah layar
        self.setFixedSize(600, 200)
        
        # Posisikan jendela otomatis tepat di TENGAH-TENGAH LAYAR UTAMA
        self.center_on_screen()

        # Membuat elemen lingkaran besar (Indicator Bead)
        self.circle_indicator = QLabel(self)
        self.circle_size = 90 # Ukuran diameter lingkaran (cukup besar dan jelas)
        self.circle_indicator.setFixedSize(self.circle_size, self.circle_size)
        
        # Default State: Sangat samar (hampir tidak terlihat) saat standby agar tidak mengganggu slide
        self.style_disabled = f"background-color: rgba(255, 255, 255, 0.03); border: 2px dashed rgba(255, 255, 255, 0.1); border-radius: {self.circle_size//2}px;"
        # Active State: Berwarna Neon Cyan transparan 30% saat READY TO SWIPE
        self.style_active = f"background-color: rgba(0, 255, 204, 0.30); border: 3px solid rgba(0, 255, 204, 0.6); border-radius: {self.circle_size//2}px;"
        # Success State: Berwarna Hijau menyala saat berhasil memindahkan slide
        self.style_success = f"background-color: rgba(46, 204, 113, 0.6); border: 3px solid rgba(46, 204, 113, 1.0); border-radius: {self.circle_size//2}px;"
        
        self.circle_indicator.setStyleSheet(self.style_disabled)
        self.current_status = "DISABLED"

        # Kembalikan lingkaran ke titik tengah absolut internal window
        self.reset_circle_position()

    def center_on_screen(self):
        """Menghitung geometri resolusi layar dan meletakkan widget pas di tengah."""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def reset_circle_position(self):
        """Mengembalikan koordinat lingkaran tepat di tengah-tengah area overlay."""
        center_x = (self.width() - self.circle_size) // 2
        center_y = (self.height() - self.circle_size) // 2
        self.circle_indicator.move(center_x, center_y)

    def update_status(self, status):
        self.current_status = status
        
        if status == "ACTIVE":
            # Saat telapak tangan berhasil di-hold (Ready), hidupkan opacity lingkaran ke 30%
            self.circle_indicator.setStyleSheet(self.style_active)
        elif "SLIDE" in status:
            # Flash hijau saat slide berpindah
            self.circle_indicator.setStyleSheet(self.style_success)
        else:
            # Kembali redup jika dalam kondisi WAITING, COOLDOWN, atau DISABLED
            self.circle_indicator.setStyleSheet(self.style_disabled)
            self.reset_circle_position()

    def update_swipe_progress(self, progress: float):
        """
        Menggeser lingkaran secara horizontal berdasarkan koordinat tangan asli (-1.0 s/d 1.0).
        """
        # Lingkaran hanya bergerak jika status sudah ACTIVE (Ready to Swipe)
        if self.current_status != "ACTIVE":
            return
            
        center_x = (self.width() - self.circle_size) // 2
        center_y = (self.height() - self.circle_size) // 2
        
        # Batas maksimum pergeseran lingkaran ke kanan/kiri di dalam window (dalam piksel)
        max_travel_distance = 220 
        
        # Hitung pergeseran dinamis real-time
        new_x = center_x + int(progress * max_travel_distance)
        
        self.circle_indicator.move(new_x, center_y)

    def show_gesture(self, gesture_info):
        """Menangani efek kilat perubahan style saat trigger swipe sukses dilewati."""
        if "SLIDE" in gesture_info:
            self.update_status("SLIDE_SUCCESS")
            # Berikan jeda waktu sebelum lingkaran kembali ke mode standby di tengah
            QTimer.singleShot(800, lambda: self.update_status("COOLDOWN"))