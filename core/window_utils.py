# core/window_utils.py

import win32gui
import win32con
import win32api
import win32ui
import win32process  # 이 라인 추가
from ctypes import windll
from PIL import Image
import numpy as np
import time

class WindowUtils:
    """윈도우 API를 활용한 유틸리티 클래스"""
    
    @staticmethod
    def find_window(window_name=None, window_class=None):
        """
        윈도우 이름 또는 클래스로 윈도우 핸들 찾기
        
        Args:
            window_name (str, optional): 윈도우 이름
            window_class (str, optional): 윈도우 클래스 이름
            
        Returns:
            int: 윈도우 핸들 (없으면 0)
        """
        return win32gui.FindWindow(window_class, window_name)
    
    @staticmethod
    def find_windows_by_title(title_pattern):
        """
        제목 패턴으로 모든 매칭되는 윈도우 핸들 찾기
        
        Args:
            title_pattern (str): 윈도우 제목에 포함된 문자열
            
        Returns:
            list: 윈도우 핸들 리스트
        """
        result = []
        
        def enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title_pattern in window_title:
                    results.append(hwnd)
        
        win32gui.EnumWindows(enum_callback, result)
        return result
    
    @staticmethod
    def get_window_title(hwnd):
        """
        윈도우 핸들로 윈도우 제목 가져오기
        
        Args:
            hwnd (int): 윈도우 핸들
            
        Returns:
            str: 윈도우 제목
        """
        return win32gui.GetWindowText(hwnd)
    
    @staticmethod
    def get_window_rect(hwnd):
        """
        윈도우 위치 및 크기 가져오기
        
        Args:
            hwnd (int): 윈도우 핸들
            
        Returns:
            tuple: (left, top, right, bottom)
        """
        return win32gui.GetWindowRect(hwnd)
    
    @staticmethod
    def set_foreground(hwnd):
        """
        윈도우를 포그라운드로 가져오기
        
        Args:
            hwnd (int): 윈도우 핸들
            
        Returns:
            bool: 성공 여부
        """
        if not win32gui.IsWindow(hwnd):
            return False
            
        # 최소화된 경우 복원
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
        # 다른 프로그램이 전면에 있을 수 있으므로 대체 방법 시도
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            # 대체 방법: 현재 전면 윈도우와 타겟 윈도우 간의 스레드 연결 시도
            current_foreground = win32gui.GetForegroundWindow()
            current_thread = win32process.GetWindowThreadProcessId(current_foreground)[0]
            target_thread = win32process.GetWindowThreadProcessId(hwnd)[0]
            
            win32process.AttachThreadInput(current_thread, target_thread, True)
            win32gui.SetForegroundWindow(hwnd)
            win32process.AttachThreadInput(current_thread, target_thread, False)
            
        return win32gui.GetForegroundWindow() == hwnd
    
    @staticmethod
    def capture_window(hwnd):
        """
        윈도우 화면 캡처하기
        
        Args:
            hwnd (int): 윈도우 핸들
            
        Returns:
            numpy.ndarray: 캡처된 이미지 (OpenCV 형식)
        """
        if not hwnd or not win32gui.IsWindow(hwnd):
            return None
            
        # 윈도우 크기 가져오기
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        # 캡처를 위한 디바이스 컨텍스트 생성
        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        
        # 비트맵 생성
        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)
        
        # 화면 복사
        windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 0)
        
        # 비트맵 정보 가져오기
        bmpinfo = save_bitmap.GetInfo()
        bmpstr = save_bitmap.GetBitmapBits(True)
        
        # PIL 이미지로 변환
        img = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)
        
        # 리소스 해제
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)
        
        # OpenCV 형식으로 변환
        return np.array(img)
    
    @staticmethod
    def send_mouse_click(hwnd, x, y, button='left'):
        """
        마우스 클릭 이벤트 전송
        
        Args:
            hwnd (int): 윈도우 핸들
            x (int): 윈도우 내 X 좌표
            y (int): 윈도우 내 Y 좌표
            button (str): 'left', 'right', 'middle' 중 하나
            
        Returns:
            bool: 성공 여부
        """
        # 윈도우가 유효한지 확인
        if not hwnd or not win32gui.IsWindow(hwnd):
            return False
            
        # 클라이언트 좌표로 변환
        client_x, client_y = WindowUtils.screen_to_client(hwnd, x, y)
        
        # 마우스 이벤트 설정
        if button == 'left':
            down_msg = win32con.WM_LBUTTONDOWN
            up_msg = win32con.WM_LBUTTONUP
        elif button == 'right':
            down_msg = win32con.WM_RBUTTONDOWN
            up_msg = win32con.WM_RBUTTONUP
        elif button == 'middle':
            down_msg = win32con.WM_MBUTTONDOWN
            up_msg = win32con.WM_MBUTTONUP
        else:
            return False
            
        # 좌표 파라미터 생성
        l_param = win32api.MAKELONG(client_x, client_y)
        
        # 클릭 이벤트 전송
        win32gui.SendMessage(hwnd, down_msg, win32con.MK_LBUTTON, l_param)
        time.sleep(0.1)  # 클릭 간 짧은 지연
        win32gui.SendMessage(hwnd, up_msg, 0, l_param)
        
        return True
    
    @staticmethod
    def send_key(hwnd, key, press_type='click'):
        """
        키보드 이벤트 전송
        
        Args:
            hwnd (int): 윈도우 핸들
            key (int): 가상 키 코드 (win32con.VK_*)
            press_type (str): 'click', 'down', 'up' 중 하나
            
        Returns:
            bool: 성공 여부
        """
        if not hwnd or not win32gui.IsWindow(hwnd):
            return False
            
        if press_type == 'click':
            win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, key, 0)
            time.sleep(0.05)
            win32api.SendMessage(hwnd, win32con.WM_KEYUP, key, 0)
        elif press_type == 'down':
            win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, key, 0)
        elif press_type == 'up':
            win32api.SendMessage(hwnd, win32con.WM_KEYUP, key, 0)
        else:
            return False
            
        return True
    
    @staticmethod
    def screen_to_client(hwnd, x, y):
        """
        스크린 좌표를 클라이언트 좌표로 변환
        
        Args:
            hwnd (int): 윈도우 핸들
            x (int): 스크린 X 좌표
            y (int): 스크린 Y 좌표
            
        Returns:
            tuple: (client_x, client_y)
        """
        point = win32api.POINT(x, y)
        win32gui.ScreenToClient(hwnd, point)
        return (point.x, point.y)
    
    @staticmethod
    def client_to_screen(hwnd, x, y):
        """
        클라이언트 좌표를 스크린 좌표로 변환
        
        Args:
            hwnd (int): 윈도우 핸들
            x (int): 클라이언트 X 좌표
            y (int): 클라이언트 Y 좌표
            
        Returns:
            tuple: (screen_x, screen_y)
        """
        point = win32api.POINT(x, y)
        win32gui.ClientToScreen(hwnd, point)
        return (point.x, point.y)