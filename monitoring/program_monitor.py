# monitoring/program_monitor.py

import threading
import time
import cv2
import os
import yaml
import win32gui  # 윈도우 핸들, 윈도우 관리 기능
import win32api  # 마우스, 키보드 이벤트, 커서 제어 등
import win32con  # Windows 상수 정의
import win32ui   # UI 관련 기능
from core.window_utils import WindowUtils
from core.image_recognition import ImageRecognition
from core.action_executor import ActionExecutor

class ProgramMonitor(threading.Thread):
    """개별 프로그램 모니터링 및 자동화 클래스"""
    
    def __init__(self, program_config, resources_dir=None):
        """
        프로그램 모니터 초기화
        
        Args:
            program_config (dict): 프로그램 설정 정보
            resources_dir (str, optional): 리소스 디렉토리 경로
        """
        super(ProgramMonitor, self).__init__()
        
        self.program_name = program_config.get('name', 'Unknown Program')
        self.window_title = program_config.get('window_title', '')
        self.window_class = program_config.get('window_class', None)
        self.monitoring_interval = program_config.get('monitoring_interval', 1.0)
        self.rules = program_config.get('rules', [])
        
        # 상태 플래그
        self.running = False
        self.paused = False
        self.hwnd = 0
        
        # 리소스 디렉토리
        self.resources_dir = resources_dir
        if resources_dir and os.path.isdir(resources_dir):
            self.templates_dir = os.path.join(resources_dir, 'images')
        else:
            self.templates_dir = None
        
        # 핵심 모듈 초기화
        self.image_recognition = ImageRecognition(self.templates_dir)
        self.action_executor = ActionExecutor()
    
    def find_window(self):
        """
        모니터링할 윈도우 찾기
        
        Returns:
            bool: 성공 여부
        """
        if self.window_title:
            # 제목으로 윈도우 찾기
            self.hwnd = WindowUtils.find_window(self.window_title, self.window_class)
            
            # 정확한 일치가 없으면 부분 일치 검색
            if not self.hwnd:
                windows = WindowUtils.find_windows_by_title(self.window_title)
                if windows:
                    self.hwnd = windows[0]
        
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            self.action_executor.set_target_window(self.hwnd)
            return True
        
        return False
    
    def run(self):
        """모니터링 메인 루프"""
        self.running = True
        
        while self.running:
            if self.paused:
                time.sleep(0.5)
                continue
            
            # 윈도우 찾기 또는 유효성 확인
            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                if not self.find_window():
                    # 윈도우를 찾을 수 없음, 재시도
                    time.sleep(self.monitoring_interval)
                    continue
            
            # 윈도우 캡처
            screenshot = WindowUtils.capture_window(self.hwnd)
            
            if screenshot is not None:
                # 모든 규칙 확인
                self.check_rules(screenshot)
            
            # 모니터링 간격 대기
            time.sleep(self.monitoring_interval)
    
    def check_rules(self, screenshot):
        """
        규칙 확인 및 액션 실행
        
        Args:
            screenshot (numpy.ndarray): 캡처된 윈도우 이미지
        """
        for rule in self.rules:
            # 규칙 구성 요소 확인
            template_name = rule.get('template')
            actions = rule.get('actions', [])
            
            if not template_name or not actions:
                continue
            
            # 매칭 방법 확인
            match_method = rule.get('match_method', 'template')  # 기본값은 일반 템플릿 매칭
            threshold = rule.get('threshold', 0.8)
            
            found = False
            position = None
            
            # 매칭 방법에 따른 처리
            if match_method == 'histogram':
                # 색상 히스토그램 매칭 (회전/반전에 강인함)
                found, position, confidence = self.image_recognition.find_by_histogram(
                    screenshot, template_name, threshold)
                if found:
                    print(f"히스토그램 매칭 성공: {template_name}, 신뢰도={confidence:.3f}")
            else:
                # 기본 템플릿 매칭
                found, position, confidence = self.image_recognition.find_template(
                    screenshot, template_name, threshold)
                if found:
                    print(f"템플릿 매칭 성공: {template_name}, 신뢰도={confidence:.3f}")
            
            # 이미지 발견 시 액션 실행
            if found:
                # 윈도우 활성화 및 액션 실행
                self._process_found_template(template_name, position, actions, rule)
    

    def execute_actions(self, actions, position=None):
        """
        액션 목록 실행
        
        Args:
            actions (list): 실행할 액션 목록
            position (tuple, optional): 발견된 템플릿 위치 (x, y, w, h)
        """
        for action in actions:
            action_type = action.get('type')
            params = action.get('params', {})
            
            try:
                # 윈도우 위치 가져오기
                left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
                
                # 윈도우 활성화
                win32gui.SetForegroundWindow(self.hwnd)
                time.sleep(0.5)
                
                import pydirectinput
                pydirectinput.PAUSE = 0.1
                
                if action_type == 'click':
                    # 좌표 계산
                    if position and params.get('relative', False):
                        # 상대 좌표 처리
                        x_rel = params.get('x', 0)
                        y_rel = params.get('y', 0)
                        
                        # 상대 위치 계산
                        x = position[0] + int(position[2] * x_rel)
                        y = position[1] + int(position[3] * y_rel)
                    else:
                        # 절대 좌표
                        x = params.get('x', 0)
                        y = params.get('y', 0)
                    
                    # 화면 좌표로 변환
                    screen_x = left + int(x)
                    screen_y = top + int(y)
                    
                    # 마우스 이동 및 클릭
                    pydirectinput.moveTo(screen_x, screen_y)
                    time.sleep(0.2)
                    pydirectinput.click(button=params.get('button', 'left').lower())
                    
                    success = True
                
                elif action_type == 'key':
                    # 키 입력
                    key = params.get('key', 0)
                    press_type = params.get('press_type', 'click')
                    
                    # 가상 키 코드를 문자로 변환
                    key_char = chr(key) if 32 <= key <= 126 else f"{{VK{key}}}"
                    
                    if press_type == 'click':
                        pydirectinput.press(key_char)
                    elif press_type == 'down':
                        pydirectinput.keyDown(key_char)
                    elif press_type == 'up':
                        pydirectinput.keyUp(key_char)
                    
                    success = True
                
                elif action_type == 'text':
                    # 텍스트 입력
                    text = params.get('text', '')
                    delay = params.get('delay', 0.01)
                    
                    pydirectinput.PAUSE = delay
                    pydirectinput.write(text)
                    
                    success = True
                
                elif action_type == 'wait':
                    # 대기
                    time.sleep(params.get('seconds', 1))
                    success = True
                
                else:
                    # 알 수 없는 액션 타입
                    success = False
                
                # 액션 후 대기
                if 'delay' in action:
                    time.sleep(action['delay'])
            
            except Exception as e:
                print(f"액션 실행 오류: {e}")
                success = False
                
                # 필수 액션이 실패하면 중단
                if action.get('required', False):
                    break
        

    def game_mode_enabled(self):
        """게임 모드 사용 여부 확인"""
        return self.program_config.get('game_mode', False)

    def execute_game_action(self, action_type, **params):
        """
        게임용 액션 실행
        """
        try:
            # 윈도우가 유효한지 확인
            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                return False
            
            # 윈도우 위치 가져오기
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            
            # 윈도우 활성화
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.3)
            
            if action_type == 'click':
                # 클릭 좌표 계산 (윈도우 내 좌표)
                x = params.get('x', 0)
                y = params.get('y', 0)
                button = params.get('button', 'left')
                
                # 화면 좌표로 변환
                screen_x = left + int(x)
                screen_y = top + int(y)
                
                # 마우스 이동
                win32api.SetCursorPos((screen_x, screen_y))
                time.sleep(0.1)
                
                # 마우스 클릭 (DirectX 게임용)
                if button.lower() == 'left':
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                elif button.lower() == 'right':
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                elif button.lower() == 'middle':
                    win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
                    time.sleep(0.05)
                    win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
                
                return True
                
            elif action_type == 'key':
                # 키 코드
                key = params.get('key', 0)
                press_type = params.get('press_type', 'click')
                
                # 하드웨어 키 입력 에뮬레이션
                if press_type == 'click':
                    win32api.keybd_event(key, 0, 0, 0)  # 키 다운
                    time.sleep(0.05)
                    win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)  # 키 업
                elif press_type == 'down':
                    win32api.keybd_event(key, 0, 0, 0)
                elif press_type == 'up':
                    win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
                
                return True
                
            elif action_type == 'text':
                # 텍스트와 지연 시간
                text = params.get('text', '')
                delay = params.get('delay', 0.01)
                
                # 문자 단위로 키 입력
                for char in text:
                    try:
                        # ASCII 코드로 변환
                        key_code = ord(char.upper())
                        win32api.keybd_event(key_code, 0, 0, 0)
                        time.sleep(0.05)
                        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
                        time.sleep(delay)
                    except:
                        # 특수 문자는 건너뛰기
                        pass
                
                return True
                
            elif action_type == 'wait':
                # 대기 시간
                seconds = params.get('seconds', 1)
                time.sleep(seconds)
                return True
                
            else:
                return False
        
        except Exception as e:
            print(f"게임 모드 액션 실행 오류: {e}")
            return False

    def _process_found_template(self, template_name, position, actions, rule):
        """
        템플릿이 발견되었을 때 액션 처리
        
        Args:
            template_name (str): 발견된 템플릿 이름
            position (tuple): 발견된 위치 (x, y, w, h)
            actions (list): 실행할 액션 목록
            rule (dict): 규칙 설정 정보
        """
        try:
            print(f"템플릿 '{template_name}' 발견: 위치={position}")
            
            # 윈도우 활성화 시도
            if self.hwnd and win32gui.IsWindow(self.hwnd):
                WindowUtils.set_foreground(self.hwnd)
                time.sleep(0.3)  # 윈도우 활성화 대기
            
            # 이미지 클릭 여부 확인 (규칙에 명시된 경우)
            if rule.get('click_on_image', False):
                try:
                    # 이미지 위치 계산
                    x, y, w, h = position
                    center_x = x + w // 2
                    center_y = y + h // 2
                    
                    # 클릭 실행 (현재 윈도우 내 좌표)
                    self.action_executor.execute_action('click', 
                                                    x=center_x, 
                                                    y=center_y, 
                                                    button='left',
                                                    ensure_foreground=True)
                    
                    # 클릭 후 약간의 지연
                    time.sleep(0.2)
                except Exception as e:
                    print(f"이미지 클릭 오류: {e}")
            
            # 정의된 액션 실행
            self.execute_actions(actions, position)
            
            return True
        except Exception as e:
            print(f"템플릿 처리 오류: {e}")
            return False

    def pause(self):
        """모니터링 일시 정지"""
        self.paused = True
    
    def resume(self):
        """모니터링 재개"""
        self.paused = False
    
    def stop(self):
        """모니터링 중지"""
        self.running = False