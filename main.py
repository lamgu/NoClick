import sys
from PySide6.QtWidgets import QApplication
from pynput import keyboard

# Import modul internal sesuai arsitektur modular
from config.settings import ConfigManager
from vision.camera_thread import CameraThread
from gesture.engine import GestureEngine
from controller.keyboard_action import KeyboardController
from overlay.floating_overlay import FloatingOverlay
from ui.main_window import ControlPanel

class MainApp:
    def __init__(self) -> None:
        # 1. Inisialisasi Service Utama & Konfigurasi
        self.config_manager = ConfigManager()
        self.keyboard_ctrl = KeyboardController()
        
        # 2. Inisialisasi Engine & Overlay
        self.gesture_engine = GestureEngine(self.config_manager.config)
        self.overlay = FloatingOverlay()
        
        # 3. Inisialisasi UI Utama dengan konfigurasi terakhir dari JSON
        self.control_panel = ControlPanel(self.config_manager.config)
        
        # 4. State Management untuk Kendali Thread & Hotkey
        self.camera_thread: CameraThread | None = None
        self.hotkey_listener: keyboard.GlobalHotKeys | None = None
        self.gesture_enabled: bool = False

        # 5. Hubungkan semua sinyal antar komponen
        self.init_connections()
        
        # 6. Tampilkan Jendela Utama (Control Panel)
        self.control_panel.show()

    def init_connections(self) -> None:
        """Menghubungkan jalur komunikasi (Signals & Slots) antar modul."""
        # Koneksi dari Control Panel UI ke Main Controller
        self.control_panel.config_saved.connect(self.save_new_config)
        self.control_panel.engine_started.connect(self.start_engine)
        self.control_panel.engine_stopped.connect(self.stop_engine)
        
        # Koneksi dari Gesture Engine ke Visual Overlay & Keyboard Simulator
        self.gesture_engine.status_changed.connect(self.overlay.update_status)
        self.gesture_engine.gesture_detected.connect(self.handle_gesture)
        
        # [TAMBAHAN BARU] Hubungkan data tracking pergeseran tangan ke ikon di overlay
        self.gesture_engine.swipe_progress.connect(self.overlay.update_swipe_progress)

    def save_new_config(self, new_settings: dict) -> None:
        """Menyimpan konfigurasi terbaru dari UI ke file JSON dan memperbarui Engine."""
        self.config_manager.save_config(new_settings)
        self.gesture_engine.config = self.config_manager.config

    def parse_hotkey_to_pynput(self, hotkey_str: str) -> str:
        """Mengonversi format teks hotkey Qt menjadi format string yang dikenali pynput."""
        clean = hotkey_str.strip().lower()
        if not clean:
            return '<f8>'
            
        # Jika tombol fungsi tunggal (misal: F1 sampai F12)
        if clean.startswith('f') and clean[1:].isdigit():
            return f"<{clean}>"
            
        # Jika berupa kombinasi tombol dengan modifier (misal: Ctrl+F8 atau Alt+A)
        if '+' in clean:
            parts = clean.split('+')
            formatted_parts = [f"<{p}>" if len(p) > 1 else p for p in parts]
            return '+'.join(formatted_parts)
            
        return f"<{clean}>" if len(clean) > 1 else clean

    def setup_hotkey(self) -> None:
        """Mengaktifkan global hotkey listener berdasarkan input dari pengguna."""
        user_hotkey = self.config_manager.config.get('hotkey', 'F8')
        pynput_hotkey_str = self.parse_hotkey_to_pynput(user_hotkey)
        
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys({
                pynput_hotkey_str: self.toggle_gesture
            })
            self.hotkey_listener.start()
        except Exception as e:
            print(f"[Error] Gagal mendaftarkan hotkey {user_hotkey}, fallback ke F8. Detail: {e}")
            # Fallback otomatis ke tombol F8 jika format kustom bermasalah
            self.hotkey_listener = keyboard.GlobalHotKeys({'<f8>': self.toggle_gesture})
            self.hotkey_listener.start()

    def toggle_gesture(self) -> None:
        """Fungsi Toggle (On/Off) aktivasi deteksi gestur saat hotkey ditekan."""
        if self.camera_thread and self.camera_thread.isRunning():
            self.gesture_enabled = not self.gesture_enabled
            self.gesture_engine.toggle_enabled(self.gesture_enabled)

    def handle_gesture(self, gesture_info: str) -> None:
        """Menerima hasil deteksi dari engine, memperbarui overlay, dan mensimulasikan keyboard."""
        self.overlay.show_gesture(gesture_info)
        
        # Kirim perintah panah keyboard jika gestur valid terdeteksi
        if gesture_info == "NEXT SLIDE":
            self.keyboard_ctrl.press_right()
        elif gesture_info == "PREVIOUS SLIDE":
            self.keyboard_ctrl.press_left()
        elif gesture_info == "TAB_SWITCH_START":
            self.keyboard_ctrl.press_win_tab()
        elif gesture_info == "TAB_SWITCH_RIGHT":
            self.keyboard_ctrl.press_right()
        elif gesture_info == "TAB_SWITCH_LEFT":
            self.keyboard_ctrl.press_left()
        elif gesture_info == "TAB_SWITCH_END":
            self.keyboard_ctrl.press_enter()

    def start_engine(self) -> None:
        """Menyalakan kamera, mediaPipe tracker, hotkey, dan menampilkan overlay."""
        # Inisialisasi dan jalankan Thread Kamera Terpisah
        self.camera_thread = CameraThread(self.config_manager.config)
        self.camera_thread.landmarks_ready.connect(self.gesture_engine.process_landmarks)
        
        # Hubungkan stream gambar kamera ke fungsi render pratinjau di UI utama
        self.camera_thread.frame_ready.connect(self.control_panel.update_preview_frame)
        
        # Hubungkan tombol toggle preview UI ke variabel flag di dalam thread
        self.control_panel.preview_toggled.connect(self._set_thread_preview)
        
        self.camera_thread.start()
        
        # Aktifkan Hotkey global & tampilkan overlay informasi
        self.setup_hotkey()
        self.overlay.show()

    def _set_thread_preview(self, active: bool) -> None:
        """Mengontrol apakah thread kamera perlu menggambar kerangka tangan atau tidak."""
        if self.camera_thread:
            self.camera_thread.show_preview = active

    def stop_engine(self) -> None:
        """Menghentikan seluruh proses background secara aman (Anti-Freeze)."""
        # Matikan Thread Kamera
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread = None
        
        # Matikan Hotkey Listener
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        
        # Sembunyikan Overlay & Reset State deteksi
        self.overlay.hide()
        self.gesture_enabled = False
        self.gesture_engine.toggle_enabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Mencegah aplikasi menggantung di background proses saat window utama ditutup
    app.setQuitOnLastWindowClosed(True) 
    
    main_app = MainApp()
    
    # Interseksi closeEvent window utama untuk memastikan cleanup thread berjalan aman
    original_close = main_app.control_panel.closeEvent
    def secure_close_event(event):
        main_app.stop_engine()
        original_close(event)
        
    main_app.control_panel.closeEvent = secure_close_event

    sys.exit(app.exec())