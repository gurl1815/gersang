# monitoring/auto_click_monitor.py

import threading
import time
import win32gui
import win32con
import win32api
import ctypes
from ctypes import wintypes
import pyautogui
import pydirectinput
from core.window_utils import WindowUtils
import subprocess
import shutil

# ----- 사용자 환경 변수(필요시 경로 수정) -----
# intercept CLI 실행파일(빌드/설치한 바이너리 경로) - PATH에 넣어놨다면 그냥 "intercept"로 둬도 됨
INTERCEPT_CLI = "intercept"   # 예: "C:\\tools\\intercept.exe" 또는 "intercept" (PATH에 있으면)
# ------------------------------------------------

# Win32 구조체 정의
PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("mi", MOUSEINPUT)]

# 상수 정의
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class AutoClickMonitor:
    """주기적으로 이미지를 찾아 클릭하는 모니터링 클래스"""
    
    def __init__(self, gui, hwnd, template_name, interval=5.0, threshold=0.7):
        """
        Args:
            gui: GUI 객체 참조
            hwnd: 대상 윈도우 핸들
            template_name: 찾을 템플릿 이미지 이름
            interval: 검색 간격 (초)
            threshold: 매칭 임계값
        """
        self.gui = gui
        self.hwnd = hwnd
        self.template_name = template_name
        self.interval = interval
        self.threshold = threshold
        self.running = False
        self.thread = None
    
    def start(self):
        """모니터링 시작"""
        if self.thread and self.thread.is_alive():
            return False  # 이미 실행 중
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True  # 메인 프로그램 종료 시 함께 종료
        self.thread.start()
        return True
    
    def stop(self):
        """모니터링 중지"""
        self.running = False
        if self.thread:
            self.thread.join(2.0)  # 최대 2초 대기
    
    def _monitoring_loop(self):
        """모니터링 메인 루프"""
        while self.running:
            try:
                # 윈도우가 유효한지 확인
                if not win32gui.IsWindow(self.hwnd):
                    print(f"윈도우가 더 이상 존재하지 않음: {self.hwnd}")
                    self.running = False
                    break
                
                # 윈도우 제목 확인 (디버깅)
                window_title = win32gui.GetWindowText(self.hwnd)
                print(f"모니터링: '{window_title}' (핸들: {self.hwnd})")
                
                # 스크린샷 캡처 (윈도우 활성화 없이)
                screenshot = WindowUtils.capture_window(self.hwnd)
                if screenshot is None:
                    print("스크린샷 캡처 실패")
                    time.sleep(self.interval)
                    continue
                
                # 이미지 인식
                image_recognition = self.gui.image_recognition
                found, position, confidence = image_recognition.find_template(
                    screenshot, self.template_name, self.threshold
                )
                
                if found:
                    # 이미지 발견 정보
                    x, y, w, h = position
                    center_x = x + w // 2
                    center_y = y + h // 2
                    print(f"[자동] 이미지 발견: {self.template_name}, 위치=({x},{y}), 신뢰도={confidence:.4f}")
                    
                    # 윈도우 위치 가져오기
                    left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
                    
                    # 화면 절대 좌표 계산
                    screen_x = left + center_x
                    screen_y = top + center_y
                    
                    # 클릭 시도 (여러 방법)
                    self._try_click_methods(center_x, center_y, screen_x, screen_y)
                    
                    # 클릭 후 더 긴 간격으로 대기 (옵션)
                    time.sleep(self.interval)
                else:
                    print(f"[자동] 이미지를 찾을 수 없음: {self.template_name}")
            
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[자동] 모니터링 오류: {str(e)}")
            
            # 다음 검사까지 대기
            time.sleep(self.interval)
    

    # --------- 변경된 _try_click_methods 함수 ---------
    def _try_click_methods(self, center_x, center_y, screen_x, screen_y):
        """Interception CLI로 절대 클릭(커서 표시 여부는 시스템/CLI 구현에 따름)"""
        try:
            hwnd = self.hwnd
            is_game_active = (win32gui.GetForegroundWindow() == hwnd)
            print(f"[자동] 게임 활성화 상태: {is_game_active}")

            # 인터셉트 CLI 찾기
            cli_path = _find_intercept_cli()
            if not cli_path:
                print("[자동] Intercept CLI를 찾지 못했습니다. INTERCEPTION 드라이버 및 CLI가 설치/빌드되어 있어야 합니다.")
                print("         (설치가 되어있다면, CLI 실행파일을 PATH에 추가하거나 INTERCEPT_CLI 변수에 경로를 지정하세요.)")
                return False

            # (선택) 현재 커서 위치 저장 (원복 원하면 사용)
            # ctypes 방식으로 현재 커서 얻기
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            orig_x, orig_y = pt.x, pt.y

            # 1) 대상 위치로 마우스 워프(절대 이동)
            try:
                _call_intercept_move(cli_path, screen_x, screen_y)
                time.sleep(0.02)
            except subprocess.CalledProcessError as e:
                print(f"[자동] Intercept move 실패: {e}")
                return False

            # 2) 클릭 (left)
            try:
                _call_intercept_click(cli_path, "left")
                time.sleep(0.03)
            except subprocess.CalledProcessError as e:
                print(f"[자동] Intercept click 실패: {e}")
                return False

            # 3) (선택) 원래 위치로 복원 — 필요 없으면 주석 처리
            try:
                _call_intercept_move(cli_path, orig_x, orig_y)
                time.sleep(0.02)
            except Exception:
                # 복원 실패해도 치명적이지 않으므로 로그만 남김
                print("[자동] 경고: 커서 원복에 실패했습니다.")

            print(f"[자동] Interception 클릭 완료 ({screen_x}, {screen_y}) via {cli_path}")
            return True

        except Exception as e:
            print(f"[자동] Interception 방식 실패: {e}")
            return False
        
        
    def _find_intercept_cli(cli_candidates=("intercept", "interception-cli", "intercept.exe", "interception.exe")):
        """PATH나 지정된 이름에서 intercept CLI를 찾음"""
        # 1) 먼저 전역으로 지정된 INTERCEPT_CLI가 실행 가능한지 체크
        if shutil.which(INTERCEPT_CLI):
            return shutil.which(INTERCEPT_CLI)
        # 2) 후보 이름들 중 PATH에서 찾기
        for name in cli_candidates:
            p = shutil.which(name)
            if p:
                return p
        return None

    def _call_intercept_move(cli_path, x, y):
        """
        CLI 호출 예시: intercept mouse move <x> <y>
        실제 CLI의 인자/명령은 빌드한 유틸리티에 따라 다를 수 있으므로,
        필요하면 해당 유틸의 사용법에 맞게 여기를 수정하세요.
        """
        # Windows 좌표(픽셀)를 바로 전달하는 예제 명령어
        # 일부 CLI는 절대 좌표가 0~65535 스케일을 요구할 수 있음. CLI 매뉴얼 참고.
        cmd = [cli_path, "mouse", "move", str(int(x)), str(int(y))]
        subprocess.run(cmd, check=True)

    def _call_intercept_click(cli_path, button="left"):
        cmd = [cli_path, "mouse", "click", button]
        subprocess.run(cmd, check=True)