# core/action_executor.py

import time
import win32con
import win32gui  # 이 라인 추가
from .window_utils import WindowUtils

class ActionExecutor:
    """윈도우 프로그램에 대한 액션 실행기"""
    
    def __init__(self, hwnd=None):
        """
        액션 실행기 초기화
        
        Args:
            hwnd (int, optional): 윈도우 핸들
        """
        self.hwnd = hwnd
    
    def set_target_window(self, hwnd):
        """
        대상 윈도우 설정
        
        Args:
            hwnd (int): 윈도우 핸들
        """
        self.hwnd = hwnd
    
    def click(self, x, y, button='left', ensure_foreground=True):
        """
        지정된 위치 클릭
        
        Args:
            x (int): 윈도우 내 X 좌표
            y (int): 윈도우 내 Y 좌표
            button (str): 'left', 'right', 'middle' 중 하나
            ensure_foreground (bool): 클릭 전 윈도우를 전면으로 가져올지 여부
            
        Returns:
            bool: 성공 여부
        """
        if not self.hwnd:
            return False
        
        # 윈도우를 전면으로 가져오기 (옵션)
        if ensure_foreground:
            WindowUtils.set_foreground(self.hwnd)
            time.sleep(0.1)  # 전환 대기
        
        return WindowUtils.send_mouse_click(self.hwnd, x, y, button)
    
    def press_key(self, key, press_type='click'):
        """
        키 입력 전송
        
        Args:
            key (int): 가상 키 코드 (win32con.VK_*)
            press_type (str): 'click', 'down', 'up' 중 하나
            
        Returns:
            bool: 성공 여부
        """
        if not self.hwnd:
            return False
        
        return WindowUtils.send_key(self.hwnd, key, press_type)
    
    def send_text(self, text, delay=0.01):
        """
        텍스트 입력 전송
        
        Args:
            text (str): 전송할 텍스트
            delay (float): 키 간 지연 시간 (초)
            
        Returns:
            bool: 성공 여부
        """
        if not self.hwnd:
            return False
        
        # 간단한 구현 - 실제로는 더 복잡한 처리가 필요할 수 있음
        for char in text:
            # ASCII 문자인 경우
            key_code = ord(char.upper())
            if 32 <= key_code <= 126:  # 기본 ASCII 범위
                self.press_key(key_code)
            else:
                # 특수 키 처리
                pass  # 향후 확장
            
            if delay > 0:
                time.sleep(delay)
        
        return True
    
    def move_window(self, x, y, width=None, height=None):
        """
        윈도우 위치/크기 변경
        
        Args:
            x (int): 윈도우 X 위치
            y (int): 윈도우 Y 위치
            width (int, optional): 윈도우 너비
            height (int, optional): 윈도우 높이
            
        Returns:
            bool: 성공 여부
        """
        if not self.hwnd:
            return False
        
        try:
            if width is None or height is None:
                # 기존 크기 유지하고 위치만 변경
                left, top, right, bottom = WindowUtils.get_window_rect(self.hwnd)
                if width is None:
                    width = right - left
                if height is None:
                    height = bottom - top
            
            win32gui.MoveWindow(self.hwnd, x, y, width, height, True)
            return True
        except Exception:
            return False
    
    def execute_action(self, action_type, **params):
        """
        액션 타입에 따라 실행
        
        Args:
            action_type (str): 액션 타입 ('click', 'key', 'text', 'move', 'wait')
            **params: 액션에 필요한 파라미터
            
        Returns:
            bool: 성공 여부
        """
        if not self.hwnd:
            return False
        
        if action_type == 'click':
            return self.click(
                params.get('x', 0), 
                params.get('y', 0),
                params.get('button', 'left'),
                params.get('ensure_foreground', True)
            )
        elif action_type == 'key':
            return self.press_key(
                params.get('key', 0),
                params.get('press_type', 'click')
            )
        elif action_type == 'text':
            return self.send_text(
                params.get('text', ''),
                params.get('delay', 0.01)
            )
        elif action_type == 'move':
            return self.move_window(
                params.get('x', 0),
                params.get('y', 0),
                params.get('width', None),
                params.get('height', None)
            )
        elif action_type == 'wait':
            time.sleep(params.get('seconds', 1))
            return True
        else:
            # 알 수 없는 액션 타입
            return False