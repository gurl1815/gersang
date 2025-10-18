# monitoring/auto_click_monitor.py

import threading
import time
import win32gui
import win32con
import win32api
import ctypes
from ctypes import wintypes
import ctypes.wintypes as wintypes
import pyautogui
import pydirectinput
from core.window_utils import WindowUtils
import subprocess
import shutil
import logging
import os

log = logging.getLogger(__name__)

# 경로: 필요시 절대경로로 바꿔 주세요
DD_DLL_PATH = os.path.abspath("./DD94687.64.dll")  # 또는 "C:\\path\\to\\DD94687.64.dll"

class ClassDD:
    def __init__(self, dll_path=DD_DLL_PATH):
        self.dll_path = dll_path
        self.dll = None
        self.loaded = False
        # 실제 호출 규약이 stdcall이면 WinDLL, cdecl이면 CDLL
        try:
            if os.path.exists(dll_path):
                # 기본으로 WinDLL 사용 (많은 ClassDD 계열이 stdcall 사용)
                self.dll = ctypes.WinDLL(dll_path)
                # 함수 존재/시그니처 안전 설정 (실제 DLL export에 따라 수정)
                if hasattr(self.dll, "DD_key"):
                    self.dll.DD_key.argtypes = (ctypes.c_int, ctypes.c_int)
                    self.dll.DD_key.restype  = ctypes.c_int
                if hasattr(self.dll, "DD_mouse"):
                    self.dll.DD_mouse.argtypes = (ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int)
                    self.dll.DD_mouse.restype  = ctypes.c_int
                if hasattr(self.dll, "DD_move"):
                    self.dll.DD_move.argtypes = (ctypes.c_int, ctypes.c_int)
                    self.dll.DD_move.restype  = ctypes.c_int
                self.loaded = True
                log.info("ClassDD DLL loaded: %s", dll_path)
            else:
                log.info("ClassDD DLL not found at %s", dll_path)
        except Exception as e:
            log.exception("Failed to load ClassDD DLL: %s", e)
            self.loaded = False

    def key(self, code, action):
        if not self.loaded or not hasattr(self.dll, "DD_key"):
            raise RuntimeError("DD_key not available")
        return int(self.dll.DD_key(int(code), int(action)))

    def mouse(self, x, y, button=1, action=1):
        # button/action 의미는 DLL 스펙에 따름; 예시는 (x,y,button,action)
        if not self.loaded or not hasattr(self.dll, "DD_mouse"):
            raise RuntimeError("DD_mouse not available")
        return int(self.dll.DD_mouse(int(x), int(y), int(button), int(action)))

    def move(self, x, y):
        if not self.loaded or not hasattr(self.dll, "DD_move"):
            raise RuntimeError("DD_move not available")
        return int(self.dll.DD_move(int(x), int(y)))

# 싱글톤 인스턴스 (파일 로드 시 한 번 생성)
_classdd = ClassDD(DD_DLL_PATH)

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
        """
        ClassDD 우선 시도. 실패 시 win32/pydirectinput 사용자 레벨 클릭으로 폴백.
        이 함수는 원본 시그니처를 유지합니다.
        """
        try:
            hwnd = self.hwnd
            is_game_active = (win32gui.GetForegroundWindow() == hwnd)
            log.info("[자동] 게임 활성화 상태: %s", is_game_active)

            # 1) ClassDD (DLL) 우선 사용
            try:
                if _classdd.loaded:
                    log.debug("[자동] ClassDD 사용 시도: move->click")
                    # 가능한 경우 move 사용
                    try:
                        # ClassDD.move이 존재하면 절대 좌표로 이동 시도
                        _classdd.move(screen_x, screen_y)
                        time.sleep(0.01)
                    except Exception:
                        log.debug("DD_move 미제공 또는 실패 - 건너뜀")

                    # 우선 DD_mouse 호출 시도 (있으면 사용)
                    try:
                        if hasattr(_classdd.dll, "DD_mouse"):
                            # action 1=down, 2=up 가정 (DLL 스펙 확인 필요)
                            _classdd.mouse(screen_x, screen_y, 1, 1)  # down
                            time.sleep(0.02)
                            _classdd.mouse(screen_x, screen_y, 1, 2)  # up
                            log.info("[자동] ClassDD DD_mouse로 클릭 성공")
                            return True
                        else:
                            # DD_mouse가 없으면 DD_key로 마우스/핫키 시뮬 (게임에서 사용하는 키코드 필요)
                            # 예: 201 같은 마우스/단축키 코드 (사용 환경에 따라 수정)
                            _classdd.key(201, 1)
                            time.sleep(0.02)
                            _classdd.key(201, 2)
                            log.info("[자동] ClassDD DD_key로 클릭(대체) 성공")
                            return True
                    except Exception as e:
                        log.exception("ClassDD 클릭 시도 실패: %s", e)
                        # DLL 실패인 경우 아래 폴백으로 넘어감
                else:
                    log.debug("ClassDD DLL 미로딩 상태, 건너뜀")
            except Exception as e:
                log.exception("ClassDD 전체 시도 중 예외: %s", e)

            # 2) DLL이 없거나 실패하면 사용자 레벨 클릭 (폴백)
            # 방법 A: win32api로 커서 이동 + mouse_event (기본 fallback)
            try:
                # 현재 커서 보관
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                pt = POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                orig_x, orig_y = pt.x, pt.y

                # 절대 이동 (SetCursorPos은 픽셀 단위)
                win32api.SetCursorPos((int(screen_x), int(screen_y)))
                time.sleep(0.01)

                # 마우스 클릭 이벤트 (mouse_event 사용)
                # 이 방법은 일부 게임/안티치트에서 막힐 수 있음
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.02)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.01)

                # 원복
                try:
                    win32api.SetCursorPos((int(orig_x), int(orig_y)))
                except Exception:
                    log.debug("커서 원복 실패")

                log.info("[자동] win32api mouse_event로 클릭 성공 (폴백)")
                return True
            except Exception as e:
                log.exception("win32api 폴백 실패: %s", e)

            # 3) 마지막 폴백: pydirectinput (더 높은 권한/대체 라이브러리)
            try:
                # pydirectinput은 게임에서 더 잘 먹히는 경우가 있음
                pydirectinput.moveTo(int(screen_x), int(screen_y))
                time.sleep(0.01)
                pydirectinput.click()
                log.info("[자동] pydirectinput로 클릭 성공 (최종 폴백)")
                return True
            except Exception as e:
                log.exception("pydirectinput 폴백 실패: %s", e)

            log.warning("[자동] 모든 클릭 방법 실패")
            return False

        except Exception as e:
            log.exception("[자동] _try_click_methods 예외: %s", e)
            return False