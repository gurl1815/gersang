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
    

    def _try_click_methods(self, center_x, center_y, screen_x, screen_y):
        """커서 이동 없이, 눈에는 안 보이지만 클릭이 들어가는 방식"""
        try:
            hwnd = self.hwnd
            is_game_active = (win32gui.GetForegroundWindow() == hwnd)
            print(f"[자동] 게임 활성화 상태: {is_game_active}")

            # 클릭 신호만 하드웨어 이벤트로 전송
            down_input = INPUT(
                type=INPUT_MOUSE,
                mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)
            )
            up_input = INPUT(
                type=INPUT_MOUSE,
                mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)
            )

            # 실제 하드웨어 입력 전송
            ctypes.windll.user32.SendInput(1, ctypes.byref(down_input), ctypes.sizeof(down_input))
            time.sleep(0.03)
            ctypes.windll.user32.SendInput(1, ctypes.byref(up_input), ctypes.sizeof(up_input))
            time.sleep(0.03)

            print(f"[자동] 커서 이동 없이 하드웨어 클릭 입력 완료 ({screen_x}, {screen_y})")
            return True

        except Exception as e:
            print(f"[자동] 하드웨어 클릭 실패: {e}")
            return False