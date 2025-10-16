# monitoring/program_monitor.py

import threading
import time
import cv2
import os
import yaml
import win32gui  # 이 라인 추가
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
            
            # 이미지 인식
            threshold = rule.get('threshold', 0.8)
            found, position, confidence = self.image_recognition.find_template(
                screenshot, template_name, threshold)
            
            # 템플릿 발견 시 액션 실행
            if found:
                self.execute_actions(actions, position)
    
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
                
                # 상대 좌표 처리 (템플릿 위치 기준)
                if position and action_type == 'click':
                    # 상대 좌표가 사용된 경우
                    if params.get('relative', False):
                        x_rel = params.get('x', 0)
                        y_rel = params.get('y', 0)
                        
                        # 상대 위치 계산
                        params['x'] = position[0] + int(position[2] * x_rel)
                        params['y'] = position[1] + int(position[3] * y_rel)
                
                # 액션 실행
                success = self.action_executor.execute_action(action_type, **params)
                
                # 실패 처리 (옵션)
                if not success and action.get('required', False):
                    break  # 필수 액션이 실패하면 중단
                
                # 액션 후 대기
                if 'delay' in action:
                    time.sleep(action['delay'])
        
    def pause(self):
        """모니터링 일시 정지"""
        self.paused = True
    
    def resume(self):
        """모니터링 재개"""
        self.paused = False
    
    def stop(self):
        """모니터링 중지"""
        self.running = False