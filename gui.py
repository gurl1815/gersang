# gui.py

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import cv2
import numpy as np
import yaml
import pyautogui
import threading
import time
import win32gui  # 윈도우 핸들, 윈도우 관리 기능
import win32api  # 마우스, 키보드 이벤트, 커서 제어 등
import win32con  # Windows 상수 정의
import win32ui   # UI 관련 기능
from PIL import Image, ImageTk

from core.window_utils import WindowUtils
from core.image_recognition import ImageRecognition
from core.action_executor import ActionExecutor
from monitoring.program_monitor import ProgramMonitor
from monitoring.monitor_manager import MonitorManager
from settings.config_manager import ConfigManager

class AutomationGUI(tk.Tk):
    """윈도우 멀티 프로그램 자동화 GUI"""
    
    def __init__(self):
        super().__init__()
        
        # 기본 설정
        self.title("윈도우 멀티 프로그램 자동화")
        self.geometry("900x600")
        
        # 디렉토리 설정
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_dir = os.path.join(self.base_dir, 'settings')
        self.resources_dir = os.path.join(self.base_dir, 'resources')
        self.templates_dir = os.path.join(self.resources_dir, 'images')
        
        # 디렉토리 생성
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(os.path.join(self.config_dir, 'program_configs'), exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # 컴포넌트 초기화
        self.config_manager = ConfigManager(self.config_dir)
        self.monitor_manager = MonitorManager(self.config_dir, self.resources_dir)
        self.image_recognition = ImageRecognition(self.templates_dir)
        
        # 데이터
        self.active_programs = {}  # 프로그램 이름 -> ProgramMonitor 객체
        self.window_handles = []   # 감지된 윈도우 핸들 목록
        self.current_program = None  # 현재 선택된 프로그램
        self.current_rules = []    # 현재 프로그램의 규칙
        
        # 스크린샷 데이터
        self.screenshot = None
        self.screenshot_hwnd = None
        
        # GUI 초기화
        self.create_widgets()
        self.update_window_list()
        self.load_programs()
    
    def create_widgets(self):
        """GUI 위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 좌측 패널 (윈도우 목록, 프로그램 관리)
        left_frame = ttk.LabelFrame(main_frame, text="프로그램")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # 윈도우 목록
        ttk.Label(left_frame, text="감지된 윈도우:").pack(anchor=tk.W, padx=5, pady=2)
        self.window_listbox = tk.Listbox(left_frame, width=30, height=10)
        self.window_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.window_listbox.bind('<<ListboxSelect>>', self.on_window_select)
        
        # 윈도우 목록 새로고침 버튼
        ttk.Button(left_frame, text="새로고침", command=self.update_window_list).pack(fill=tk.X, padx=5, pady=2)
        
        # 프로그램 목록
        ttk.Label(left_frame, text="등록된 프로그램:").pack(anchor=tk.W, padx=5, pady=2)
        self.program_listbox = tk.Listbox(left_frame, width=30, height=10)
        self.program_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.program_listbox.bind('<<ListboxSelect>>', self.on_program_select)
        
        # 프로그램 관리 버튼
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="추가", command=self.add_program).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_frame, text="제거", command=self.remove_program).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 모니터링 제어
        monitor_frame = ttk.Frame(left_frame)
        monitor_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(monitor_frame, text="시작", command=self.start_monitoring).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(monitor_frame, text="중지", command=self.stop_monitoring).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 중앙 패널 (스크린샷, 템플릿 관리)
        center_frame = ttk.LabelFrame(main_frame, text="화면 캡처 및 템플릿")
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 스크린샷 영역
        self.screenshot_frame = ttk.Frame(center_frame)
        self.screenshot_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.screenshot_canvas = tk.Canvas(self.screenshot_frame, bg="lightgray")
        self.screenshot_canvas.pack(fill=tk.BOTH, expand=True)
        self.screenshot_canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.screenshot_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.screenshot_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # 템플릿 컨트롤
        template_frame = ttk.Frame(center_frame)
        template_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(template_frame, text="화면 캡처", command=self.capture_screenshot).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_frame, text="영역 저장", command=self.save_template).pack(side=tk.LEFT, padx=2)

        self.template_name_var = tk.StringVar()
        ttk.Entry(template_frame, textvariable=self.template_name_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 템플릿 목록
        ttk.Label(center_frame, text="템플릿 목록:").pack(anchor=tk.W, padx=5, pady=2)
        self.template_listbox = tk.Listbox(center_frame, height=5)
        self.template_listbox.pack(fill=tk.X, padx=5, pady=2)
        self.template_listbox.bind('<<ListboxSelect>>', self.on_template_select)
        
        # 템플릿 관리 버튼
        template_btn_frame = ttk.Frame(center_frame)
        template_btn_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(template_btn_frame, text="제거", command=self.remove_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_btn_frame, text="테스트", command=self.test_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_btn_frame, text="검색 및 클릭", command=self.find_and_click_selected_template).pack(side=tk.LEFT, padx=2)

        # 우측 패널 (규칙 및 액션)
        right_frame = ttk.LabelFrame(main_frame, text="규칙 및 액션")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5, ipadx=5, ipady=5)
        
        # 규칙 목록
        ttk.Label(right_frame, text="규칙 목록:").pack(anchor=tk.W, padx=5, pady=2)
        self.rule_listbox = tk.Listbox(right_frame, width=30, height=10)
        self.rule_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.rule_listbox.bind('<<ListboxSelect>>', self.on_rule_select)
        
        # 규칙 관리 버튼
        rule_btn_frame = ttk.Frame(right_frame)
        rule_btn_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(rule_btn_frame, text="추가", command=self.add_rule).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(rule_btn_frame, text="제거", command=self.remove_rule).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 액션 영역
        action_frame = ttk.LabelFrame(right_frame, text="액션")
        action_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 액션 타입 선택
        action_type_frame = ttk.Frame(action_frame)
        action_type_frame.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(action_type_frame, text="타입:").pack(side=tk.LEFT)
        
        self.action_type_var = tk.StringVar()
        action_types = ["클릭", "키 입력", "텍스트 입력", "대기"]
        self.action_type_combo = ttk.Combobox(action_type_frame, textvariable=self.action_type_var, values=action_types, state="readonly")
        self.action_type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.action_type_combo.current(0)
        self.action_type_combo.bind("<<ComboboxSelected>>", self.on_action_type_change)
        
        # 액션 파라미터 영역 (동적으로 변경)
        self.action_params_frame = ttk.Frame(action_frame)
        self.action_params_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 기본 액션 파라미터 (클릭)
        self.show_click_params()
        
        # 액션 관리 버튼
        action_btn_frame = ttk.Frame(action_frame)
        action_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(action_btn_frame, text="추가", command=self.add_action).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(action_btn_frame, text="테스트", command=self.test_action).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # 상태 바
        self.status_var = tk.StringVar()
        self.status_var.set("준비")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 캔버스 선택 영역 변수
        self.select_rect = None
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        
        # 템플릿 목록 업데이트
        self.update_template_list()
    
    # 함수 추가
    def find_and_click_selected_template(self):
        """선택된 템플릿을 찾아서 클릭"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "템플릿을 선택하세요.")
            return
        
        template_name = self.template_listbox.get(selection[0])
        self.find_and_click_image(template_name)
        
    def update_window_list(self):
        """감지된 윈도우 목록 업데이트"""
        self.window_listbox.delete(0, tk.END)
        self.window_handles = []
        
        def enum_windows_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                title = win32gui.GetWindowText(hwnd)
                self.window_listbox.insert(tk.END, title)
                self.window_handles.append(hwnd)
        
        win32gui.EnumWindows(enum_windows_callback, None)
        self.status_var.set(f"윈도우 목록 업데이트 완료: {len(self.window_handles)}개 발견")
    
    def load_programs(self):
        """등록된 프로그램 목록 로드"""
        self.program_listbox.delete(0, tk.END)
        
        program_names = self.config_manager.list_program_configs()
        for name in program_names:
            self.program_listbox.insert(tk.END, name)
        
        self.status_var.set(f"프로그램 목록 로드 완료: {len(program_names)}개")
    
    def update_template_list(self):
        """템플릿 이미지 목록 업데이트"""
        self.template_listbox.delete(0, tk.END)
        
        if not os.path.exists(self.templates_dir):
            return
        
        for filename in os.listdir(self.templates_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                name = os.path.splitext(filename)[0]
                self.template_listbox.insert(tk.END, name)
    
    def update_rule_list(self):
        """규칙 목록 업데이트"""
        self.rule_listbox.delete(0, tk.END)
        
        if not self.current_program:
            return
        
        for i, rule in enumerate(self.current_rules):
            template = rule.get('template', '?')
            self.rule_listbox.insert(tk.END, f"{i+1}. {template}")
    
    def on_window_select(self, event):
        """윈도우 목록에서 선택 시 이벤트"""
        selection = self.window_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        hwnd = self.window_handles[index]
        title = self.window_listbox.get(index)
        
        self.status_var.set(f"선택된 윈도우: {title}")
        self.screenshot_hwnd = hwnd
    
    def on_program_select(self, event):
        """프로그램 목록에서 선택 시 이벤트"""
        selection = self.program_listbox.curselection()
        if not selection:
            return
        
        program_name = self.program_listbox.get(selection[0])
        self.current_program = program_name
        
        # 프로그램 설정 로드
        config = self.config_manager.load_program_config(program_name)
        self.current_rules = config.get('rules', [])
        
        # UI 업데이트
        self.update_rule_list()
        self.status_var.set(f"프로그램 선택: {program_name}")
    
    def on_template_select(self, event):
        """템플릿 목록에서 선택 시 이벤트"""
        selection = self.template_listbox.curselection()
        if not selection:
            return
        
        template_name = self.template_listbox.get(selection[0])
        self.template_name_var.set(template_name)
        
        # 이미지 표시
        image_path = os.path.join(self.templates_dir, f"{template_name}.png")
        if os.path.exists(image_path):
            img = Image.open(image_path)
            img = ImageTk.PhotoImage(img)
            
            self.screenshot_canvas.delete("all")
            self.screenshot_canvas.create_image(0, 0, anchor=tk.NW, image=img)
            self.screenshot_canvas.image = img  # 참조 유지
            
            self.status_var.set(f"템플릿 선택: {template_name}")
    
    def on_rule_select(self, event):
        """규칙 목록에서 선택 시 이벤트"""
        selection = self.rule_listbox.curselection()
        if not selection:
            return
        
        rule_index = selection[0]
        if rule_index < len(self.current_rules):
            rule = self.current_rules[rule_index]
            template = rule.get('template', '')
            self.template_name_var.set(template)
            
            self.status_var.set(f"규칙 선택: {template}")
    
    def on_action_type_change(self, event):
        """액션 타입 변경 시 UI 업데이트"""
        action_type = self.action_type_var.get()
        
        # 기존 위젯 제거
        for widget in self.action_params_frame.winfo_children():
            widget.destroy()
        
        # 타입에 따라 파라미터 UI 표시
        if action_type == "클릭":
            self.show_click_params()
        elif action_type == "키 입력":
            self.show_key_params()
        elif action_type == "텍스트 입력":
            self.show_text_params()
        elif action_type == "대기":
            self.show_wait_params()
    
    def show_click_params(self):
        """클릭 액션 파라미터 UI"""
        # X 좌표
        x_frame = ttk.Frame(self.action_params_frame)
        x_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(x_frame, text="X:").pack(side=tk.LEFT)
        self.click_x_var = tk.StringVar(value="0")
        ttk.Entry(x_frame, textvariable=self.click_x_var, width=8).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(x_frame, text="Y:").pack(side=tk.LEFT, padx=(10, 0))
        self.click_y_var = tk.StringVar(value="0")
        ttk.Entry(x_frame, textvariable=self.click_y_var, width=8).pack(side=tk.LEFT, padx=2)
        
        # 버튼 타입
        button_frame = ttk.Frame(self.action_params_frame)
        button_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(button_frame, text="버튼:").pack(side=tk.LEFT)
        self.click_button_var = tk.StringVar(value="left")
        button_combo = ttk.Combobox(button_frame, textvariable=self.click_button_var, 
                                     values=["left", "right", "middle"], state="readonly", width=10)
        button_combo.pack(side=tk.LEFT, padx=2)
        
        # 상대 좌표 여부
        self.click_relative_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.action_params_frame, text="템플릿 기준 상대 좌표", 
                        variable=self.click_relative_var).pack(anchor=tk.W, padx=2, pady=2)
        
        # 지연 시간
        delay_frame = ttk.Frame(self.action_params_frame)
        delay_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(delay_frame, text="지연(초):").pack(side=tk.LEFT)
        self.action_delay_var = tk.StringVar(value="0.5")
        ttk.Entry(delay_frame, textvariable=self.action_delay_var, width=6).pack(side=tk.LEFT, padx=2)
    
    def show_key_params(self):
        """키 입력 액션 파라미터 UI"""
        # 키 코드
        key_frame = ttk.Frame(self.action_params_frame)
        key_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(key_frame, text="키:").pack(side=tk.LEFT)
        
        self.key_var = tk.StringVar()
        key_entry = ttk.Entry(key_frame, textvariable=self.key_var, width=15)
        key_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        key_entry.bind("<KeyPress>", self.on_key_press)
        
        # 입력 타입
        press_frame = ttk.Frame(self.action_params_frame)
        press_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(press_frame, text="입력 타입:").pack(side=tk.LEFT)
        self.key_press_type_var = tk.StringVar(value="click")
        press_combo = ttk.Combobox(press_frame, textvariable=self.key_press_type_var, 
                                   values=["click", "down", "up"], state="readonly", width=10)
        press_combo.pack(side=tk.LEFT, padx=2)
        
        # 지연 시간
        delay_frame = ttk.Frame(self.action_params_frame)
        delay_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(delay_frame, text="지연(초):").pack(side=tk.LEFT)
        self.action_delay_var = tk.StringVar(value="0.5")
        ttk.Entry(delay_frame, textvariable=self.action_delay_var, width=6).pack(side=tk.LEFT, padx=2)
    
    def on_key_press(self, event):
        """키 입력 감지"""
        key_code = event.keycode
        self.key_var.set(str(key_code))
        return "break"  # 이벤트 전파 중단
    
    def show_text_params(self):
        """텍스트 입력 액션 파라미터 UI"""
        # 텍스트
        text_frame = ttk.Frame(self.action_params_frame)
        text_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(text_frame, text="텍스트:").pack(anchor=tk.W)
        
        self.text_var = tk.StringVar()
        ttk.Entry(text_frame, textvariable=self.text_var).pack(fill=tk.X, padx=2, pady=2)
        
        # 입력 지연
        delay_frame = ttk.Frame(self.action_params_frame)
        delay_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(delay_frame, text="키 간격(초):").pack(side=tk.LEFT)
        self.text_delay_var = tk.StringVar(value="0.01")
        ttk.Entry(delay_frame, textvariable=self.text_delay_var, width=6).pack(side=tk.LEFT, padx=2)
        
        # 액션 지연
        action_delay_frame = ttk.Frame(self.action_params_frame)
        action_delay_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(action_delay_frame, text="지연(초):").pack(side=tk.LEFT)
        self.action_delay_var = tk.StringVar(value="0.5")
        ttk.Entry(action_delay_frame, textvariable=self.action_delay_var, width=6).pack(side=tk.LEFT, padx=2)
    
    def show_wait_params(self):
        """대기 액션 파라미터 UI"""
        wait_frame = ttk.Frame(self.action_params_frame)
        wait_frame.pack(fill=tk.X, padx=2, pady=2)
        
        ttk.Label(wait_frame, text="대기 시간(초):").pack(side=tk.LEFT)
        self.wait_seconds_var = tk.StringVar(value="1.0")
        ttk.Entry(wait_frame, textvariable=self.wait_seconds_var, width=6).pack(side=tk.LEFT, padx=2)
    
    def capture_screenshot(self):
        """선택된 윈도우의 클라이언트 영역 스크린샷 캡처"""
        if not self.screenshot_hwnd:
            messagebox.showwarning("경고", "캡처할 윈도우를 먼저 선택하세요.")
            return
        
        try:
            # 상태 표시
            self.status_var.set(f"캡처 중... 윈도우 핸들: {self.screenshot_hwnd}")
            self.update()  # GUI 업데이트
            
            # 클라이언트 영역 가져오기
            client_left, client_top, client_right, client_bottom = self.get_client_rect(self.screenshot_hwnd)
            client_width = client_right - client_left
            client_height = client_bottom - client_top
            
            # 윈도우 활성화
            win32gui.SetForegroundWindow(self.screenshot_hwnd)
            time.sleep(0.5)  # 전환 대기
            
            # 클라이언트 영역 캡처
            import pyautogui
            screenshot = pyautogui.screenshot(region=(client_left, client_top, client_width, client_height))
            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            
            if screenshot is None or screenshot.size == 0:
                messagebox.showerror("오류", "스크린샷 캡처에 실패했습니다.")
                return
            
            # OpenCV 이미지를 PIL 이미지로 변환
            screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(screenshot_rgb)
            
            # 캔버스 크기 조정
            width, height = pil_img.size
            self.screenshot_canvas.config(width=width, height=height)
            
            # 이미지 표시
            img_tk = ImageTk.PhotoImage(pil_img)
            self.screenshot_canvas.delete("all")
            self.screenshot_canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.screenshot_canvas.image = img_tk  # 참조 유지
            
            # 스크린샷 저장
            self.screenshot = screenshot
            
            self.status_var.set(f"클라이언트 영역 캡처 완료: {width}x{height}")
        
        except Exception as e:
            self.status_var.set(f"캡처 오류: {str(e)}")
            messagebox.showerror("오류", f"스크린샷 캡처 중 오류 발생: {str(e)}")
    
    def on_canvas_press(self, event):
        """캔버스 마우스 누르기 이벤트"""
        if not self.screenshot is None:
            # 이전 선택 영역 제거
            if self.select_rect:
                self.screenshot_canvas.delete(self.select_rect)
            
            # 시작 위치 저장
            self.start_x = event.x
            self.start_y = event.y
            
            # 선택 영역 생성
            self.select_rect = self.screenshot_canvas.create_rectangle(
                self.start_x, self.start_y, self.start_x, self.start_y,
                outline="red", width=2
            )
    
    def on_canvas_drag(self, event):
        """캔버스 마우스 드래그 이벤트"""
        if not self.screenshot is None and self.select_rect:
            # 현재 위치 업데이트
            self.end_x = event.x
            self.end_y = event.y
            
            # 선택 영역 업데이트
            self.screenshot_canvas.coords(
                self.select_rect,
                self.start_x, self.start_y, self.end_x, self.end_y
            )
    
    def on_canvas_release(self, event):
        """캔버스 마우스 릴리스 이벤트"""
        if not self.screenshot is None and self.select_rect:
            # 최종 위치 저장
            self.end_x = event.x
            self.end_y = event.y
            
            # 좌표 정규화 (시작이 항상 좌상단)
            x1 = min(self.start_x, self.end_x)
            y1 = min(self.start_y, self.end_y)
            x2 = max(self.start_x, self.end_x)
            y2 = max(self.start_y, self.end_y)
            
            # 선택 영역 크기
            width = x2 - x1
            height = y2 - y1
            
            self.status_var.set(f"영역 선택: ({x1}, {y1}) - ({x2}, {y2}), 크기: {width}x{height}")
            
            # 클릭 좌표를 중앙으로 설정 (상대적)
            if width > 0 and height > 0:
                self.click_x_var.set("0.5")
                self.click_y_var.set("0.5")
    
    def save_template(self):
        """선택된 영역을 템플릿으로 저장"""
        if not self.screenshot is None and self.select_rect:
            # 템플릿 이름 확인
            template_name = self.template_name_var.get().strip()
            if not template_name:
                messagebox.showwarning("경고", "템플릿 이름을 입력하세요.")
                return
            
            # 좌표 정규화
            x1 = min(self.start_x, self.end_x)
            y1 = min(self.start_y, self.end_y)
            x2 = max(self.start_x, self.end_x)
            y2 = max(self.start_y, self.end_y)
            
            # 선택 영역이 너무 작으면 경고
            if x2 - x1 < 10 or y2 - y1 < 10:
                messagebox.showwarning("경고", "선택 영역이 너무 작습니다.")
                return
            
            # 템플릿 이미지 추출
            template = self.screenshot[y1:y2, x1:x2]
            
            # 파일 저장
            template_path = os.path.join(self.templates_dir, f"{template_name}.png")
            cv2.imwrite(template_path, template)
            
            # 템플릿 목록 업데이트
            self.update_template_list()
            
            # 상태 업데이트
            self.status_var.set(f"템플릿 저장 완료: {template_name}.png")
        else:
            messagebox.showwarning("경고", "영역을 선택하세요.")
    
    def remove_template(self):
        """선택된 템플릿 제거"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "제거할 템플릿을 선택하세요.")
            return
        
        template_name = self.template_listbox.get(selection[0])
        
        # 확인 대화상자
        confirm = messagebox.askyesno("확인", f"템플릿 '{template_name}'을(를) 삭제할까요?")
        if not confirm:
            return
        
        # 파일 삭제
        template_path = os.path.join(self.templates_dir, f"{template_name}.png")
        if os.path.exists(template_path):
            os.remove(template_path)
            
            # 템플릿 목록 업데이트
            self.update_template_list()
            
            self.status_var.set(f"템플릿 제거 완료: {template_name}")
    
    def test_template(self):
        """선택된 템플릿 테스트"""
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "테스트할 템플릿을 선택하세요.")
            return
        
        if not self.screenshot_hwnd:
            messagebox.showwarning("경고", "테스트할 윈도우를 선택하세요.")
            return
        
        template_name = self.template_listbox.get(selection[0])
        
        # 스크린샷 캡처
        screenshot = WindowUtils.capture_window(self.screenshot_hwnd)
        if screenshot is None:
            messagebox.showerror("오류", "스크린샷 캡처에 실패했습니다.")
            return
        
        # 이미지 인식 테스트 (낮은 임계값 사용)
        found, position, confidence = self.image_recognition.find_template(
            screenshot, template_name, threshold=0.5)  # 임계값 낮춤
        
        # OpenCV 이미지를 PIL 이미지로 변환
        screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(screenshot_rgb)
        
        # 이미지 표시
        width, height = pil_img.size
        self.screenshot_canvas.config(width=width, height=height)
        
        img_tk = ImageTk.PhotoImage(pil_img)
        self.screenshot_canvas.delete("all")
        self.screenshot_canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        self.screenshot_canvas.image = img_tk  # 참조 유지
        
        # 스크린샷 저장
        self.screenshot = screenshot
        
        # 인식 결과 표시
        if found:
            x, y, w, h = position
            self.screenshot_canvas.create_rectangle(
                x, y, x + w, y + h,
                outline="green", width=2
            )
            
            # 중앙점 계산 및 표시
            center_x = x + w // 2
            center_y = y + h // 2
            self.screenshot_canvas.create_oval(
                center_x - 5, center_y - 5, center_x + 5, center_y + 5,
                fill="red", outline="red"
            )
            
            self.status_var.set(f"템플릿 인식 성공: {template_name}, 신뢰도: {confidence:.2f}")
            
            # 인식된 위치 클릭 (선택 사항)
            if messagebox.askyesno("클릭", "인식된 위치를 클릭하시겠습니까?"):
                try:
                    # 윈도우 위치
                    left, top, right, bottom = win32gui.GetWindowRect(self.screenshot_hwnd)
                    
                    # 화면 좌표 계산
                    screen_x = left + center_x
                    screen_y = top + center_y
                    
                    # 윈도우 활성화
                    win32gui.SetForegroundWindow(self.screenshot_hwnd)
                    time.sleep(0.5)
                    
                    # 클릭
                    import pydirectinput
                    pydirectinput.moveTo(screen_x, screen_y)
                    time.sleep(0.2)
                    pydirectinput.click()
                except Exception as e:
                    self.status_var.set(f"클릭 오류: {e}")
        else:
            self.status_var.set(f"템플릿 인식 실패: {template_name}, 신뢰도: {confidence:.2f}")
            
            # 더 낮은 임계값으로 재시도
            found, position, confidence = self.image_recognition.find_template(
                screenshot, template_name, threshold=0.3)  # 매우 낮은 임계값
                
            if found:
                x, y, w, h = position
                self.screenshot_canvas.create_rectangle(
                    x, y, x + w, y + h,
                    outline="yellow", width=2  # 노란색으로 표시 (낮은 신뢰도)
                )
                
                self.status_var.set(f"낮은 신뢰도로 발견: {template_name}, 신뢰도: {confidence:.2f}")
    
    def add_program(self):
        """새 프로그램 추가"""
        # 윈도우 선택 확인
        selection = self.window_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "추가할 윈도우를 선택하세요.")
            return
        
        window_title = self.window_listbox.get(selection[0])
        
        # 프로그램 이름 입력
        program_name = simpledialog.askstring("프로그램 추가", "프로그램 이름:", initialvalue=window_title)
        if not program_name:
            return
        
        # 게임 모드 설정
        game_mode = messagebox.askyesno("게임 모드", "이 프로그램을 게임 모드로 설정하시겠습니까?\n(게임 및 특수 애플리케이션용)")
        
        # 기본 설정 생성
        success = self.config_manager.create_default_program_config(program_name, window_title)
        
        if success:
            # 설정 로드 후 게임 모드 추가
            config = self.config_manager.load_program_config(program_name)
            config['game_mode'] = game_mode
            self.config_manager.save_program_config(program_name, config)
            
            # 프로그램 목록 업데이트
            self.load_programs()
            
            self.status_var.set(f"프로그램 추가 완료: {program_name} (게임 모드: {'예' if game_mode else '아니오'})")
        else:
            messagebox.showerror("오류", f"프로그램 설정 생성에 실패했습니다: {program_name}")
    
    def remove_program(self):
        """선택된 프로그램 제거"""
        selection = self.program_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "제거할 프로그램을 선택하세요.")
            return
        
        program_name = self.program_listbox.get(selection[0])
        
        # 확인 대화상자
        confirm = messagebox.askyesno("확인", f"프로그램 '{program_name}'을(를) 삭제할까요?")
        if not confirm:
            return
        
        # 파일 삭제
        config_path = os.path.join(self.config_dir, 'program_configs', f"{program_name}.yaml")
        if os.path.exists(config_path):
            os.remove(config_path)
            
            # 프로그램 목록 업데이트
            self.load_programs()
            
            # 현재 선택된 프로그램이 삭제되었으면 초기화
            if self.current_program == program_name:
                self.current_program = None
                self.current_rules = []
                self.update_rule_list()
            
            self.status_var.set(f"프로그램 제거 완료: {program_name}")
    
    def add_rule(self):
        """새 규칙 추가"""
        if not self.current_program:
            messagebox.showwarning("경고", "먼저 프로그램을 선택하세요.")
            return
        
        # 템플릿 선택 확인
        selection = self.template_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "규칙에 사용할 템플릿을 선택하세요.")
            return
        
        template_name = self.template_listbox.get(selection[0])
        
        # 규칙 생성
        new_rule = {
            'template': template_name,
            'threshold': 0.5,
            'actions': []
        }
        
        self.current_rules.append(new_rule)
        
        # 설정 저장
        config = self.config_manager.load_program_config(self.current_program)
        config['rules'] = self.current_rules
        self.config_manager.save_program_config(self.current_program, config)
        
        # 규칙 목록 업데이트
        self.update_rule_list()
        
        self.status_var.set(f"규칙 추가 완료: {template_name}")
    
    def remove_rule(self):
        """선택된 규칙 제거"""
        if not self.current_program:
            return
        
        selection = self.rule_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "제거할 규칙을 선택하세요.")
            return
        
        rule_index = selection[0]
        
        if rule_index < len(self.current_rules):
            # 규칙 제거
            rule = self.current_rules.pop(rule_index)
            
            # 설정 저장
            config = self.config_manager.load_program_config(self.current_program)
            config['rules'] = self.current_rules
            self.config_manager.save_program_config(self.current_program, config)
            
            # 규칙 목록 업데이트
            self.update_rule_list()
            
            self.status_var.set(f"규칙 제거 완료")
    
    def add_action(self):
        """현재 규칙에 액션 추가"""
        if not self.current_program:
            messagebox.showwarning("경고", "먼저 프로그램을 선택하세요.")
            return
        
        # 규칙 선택 확인
        selection = self.rule_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "액션을 추가할 규칙을 선택하세요.")
            return
        
        rule_index = selection[0]
        
        if rule_index >= len(self.current_rules):
            return
        
        # 액션 타입 확인
        action_type = self.action_type_var.get()
        
        # 액션 파라미터 생성
        action = {}
        
        if action_type == "클릭":
            action = {
                'type': 'click',
                'params': {
                    'x': float(self.click_x_var.get()),
                    'y': float(self.click_y_var.get()),
                    'button': self.click_button_var.get(),
                    'relative': self.click_relative_var.get()
                },
                'delay': float(self.action_delay_var.get())
            }
        elif action_type == "키 입력":
            action = {
                'type': 'key',
                'params': {
                    'key': int(self.key_var.get()),
                    'press_type': self.key_press_type_var.get()
                },
                'delay': float(self.action_delay_var.get())
            }
        elif action_type == "텍스트 입력":
            action = {
                'type': 'text',
                'params': {
                    'text': self.text_var.get(),
                    'delay': float(self.text_delay_var.get())
                },
                'delay': float(self.action_delay_var.get())
            }
        elif action_type == "대기":
            action = {
                'type': 'wait',
                'params': {
                    'seconds': float(self.wait_seconds_var.get())
                }
            }
        
        # 규칙에 액션 추가
        self.current_rules[rule_index]['actions'].append(action)
        
        # 설정 저장
        config = self.config_manager.load_program_config(self.current_program)
        config['rules'] = self.current_rules
        self.config_manager.save_program_config(self.current_program, config)
        
        self.status_var.set(f"액션 추가 완료: {action_type}")
    

    def test_action(self):
        """현재 설정된 액션 테스트 (게임용 버전)"""
        if not self.screenshot_hwnd:
            messagebox.showwarning("경고", "테스트할 윈도우를 선택하세요.")
            return
        
        # 액션 타입 확인
        action_type = self.action_type_var.get()
        
        # 상태 업데이트
        self.status_var.set(f"{action_type} 액션 테스트 중...")
        self.update()  # GUI 업데이트
        
        try:
            if action_type == "클릭":
                # 윈도우 정보 얻기
                left, top, right, bottom = win32gui.GetWindowRect(self.screenshot_hwnd)
                
                # 좌표 계산
                try:
                    x = int(float(self.click_x_var.get()))
                    y = int(float(self.click_y_var.get()))
                    
                    # 화면 좌표로 변환
                    screen_x = left + x
                    screen_y = top + y
                except ValueError:
                    messagebox.showerror("오류", "유효한 좌표 값을 입력하세요.")
                    return
                
                # 디버그 정보 표시
                self.status_var.set(f"클릭 좌표: 윈도우 내({x}, {y}) -> 화면({screen_x}, {screen_y})")
                self.update()
                
                # 윈도우 활성화
                win32gui.SetForegroundWindow(self.screenshot_hwnd)
                time.sleep(1)  # 충분한 대기 시간
                
                # pydirectinput으로 클릭
                import pydirectinput
                pydirectinput.PAUSE = 0.1  # 명령 간 지연 설정
                
                # 화면 좌표로 이동 후 클릭
                pydirectinput.moveTo(screen_x, screen_y)
                time.sleep(0.2)
                
                button = self.click_button_var.get().lower()
                pydirectinput.click(button=button)
                
                self.status_var.set(f"클릭 완료: {button} 버튼 ({screen_x}, {screen_y})")
            
            elif action_type == "키 입력":
                # 윈도우 활성화
                win32gui.SetForegroundWindow(self.screenshot_hwnd)
                time.sleep(0.5)
                
                # pydirectinput으로 키 입력
                try:
                    import pydirectinput
                    key = int(self.key_var.get())
                    
                    # 가상 키 코드를 문자로 변환
                    key_char = chr(key) if 32 <= key <= 126 else f"{{VK{key}}}"
                    
                    if self.key_press_type_var.get() == "click":
                        pydirectinput.press(key_char)
                    elif self.key_press_type_var.get() == "down":
                        pydirectinput.keyDown(key_char)
                    elif self.key_press_type_var.get() == "up":
                        pydirectinput.keyUp(key_char)
                    
                    self.status_var.set(f"키 입력 완료: {key_char}")
                except Exception as e:
                    self.status_var.set(f"키 입력 오류: {str(e)}")
            
            elif action_type == "텍스트 입력":
                # 윈도우 활성화
                win32gui.SetForegroundWindow(self.screenshot_hwnd)
                time.sleep(0.5)
                
                # pydirectinput으로 텍스트 입력
                try:
                    import pydirectinput
                    text = self.text_var.get()
                    delay = float(self.text_delay_var.get())
                    
                    pydirectinput.PAUSE = delay
                    pydirectinput.write(text)
                    
                    self.status_var.set(f"텍스트 입력 완료: {text}")
                except Exception as e:
                    self.status_var.set(f"텍스트 입력 오류: {str(e)}")
            
            elif action_type == "대기":
                seconds = float(self.wait_seconds_var.get())
                self.status_var.set(f"{seconds}초 대기 중...")
                self.update()
                time.sleep(seconds)
                self.status_var.set(f"대기 완료")
        
        except Exception as e:
            self.status_var.set(f"액션 테스트 오류: {str(e)}")
            messagebox.showerror("오류", f"액션 테스트 중 오류 발생: {str(e)}")
        
    def start_monitoring(self):
        """선택된 프로그램 모니터링 시작"""
        selection = self.program_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "시작할 프로그램을 선택하세요.")
            return
        
        program_name = self.program_listbox.get(selection[0])
        
        # 이미 실행 중인지 확인
        if program_name in self.active_programs and self.active_programs[program_name].is_alive():
            messagebox.showinfo("정보", f"프로그램 '{program_name}'은(는) 이미 모니터링 중입니다.")
            return
        
        # 설정 로드
        config = self.config_manager.load_program_config(program_name)
        
        # 모니터 생성 및 시작
        monitor = ProgramMonitor(config, self.resources_dir)
        monitor.start()
        
        # 활성 목록에 추가
        self.active_programs[program_name] = monitor
        
        self.status_var.set(f"모니터링 시작: {program_name}")
    
    def stop_monitoring(self):
        """선택된 프로그램 모니터링 중지"""
        selection = self.program_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "중지할 프로그램을 선택하세요.")
            return
        
        program_name = self.program_listbox.get(selection[0])
        
        # 실행 중인지 확인
        if program_name in self.active_programs and self.active_programs[program_name].is_alive():
            # 모니터 중지
            self.active_programs[program_name].stop()
            
            # 잠시 대기
            time.sleep(0.5)
            
            self.status_var.set(f"모니터링 중지: {program_name}")
        else:
            messagebox.showinfo("정보", f"프로그램 '{program_name}'은(는) 모니터링 중이 아닙니다.")

    def get_client_rect(self, hwnd):
        """윈도우의 클라이언트 영역 가져오기"""
        import ctypes
        from ctypes.wintypes import RECT
        
        # 윈도우 전체 영역
        window_rect = win32gui.GetWindowRect(hwnd)
        
        # 클라이언트 영역
        client_rect = RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        
        # 클라이언트 영역의 좌상단 좌표 (화면 기준)
        point = ctypes.wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
        client_left, client_top = point.x, point.y
        
        # 클라이언트 영역 계산
        client_width = client_rect.right - client_rect.left
        client_height = client_rect.bottom - client_rect.top
        
        return (client_left, client_top, client_left + client_width, client_top + client_height)

 
            
    def find_and_click_image(self, template_name, threshold=0.5):
        """템플릿 이미지를 찾아 클릭 (디버깅 강화 버전)"""
        if not self.screenshot_hwnd:
            messagebox.showwarning("경고", "대상 윈도우를 선택하세요.")
            return False
        
        try:
            # 상태 표시
            self.status_var.set(f"이미지 검색 시작: {template_name}")
            self.update()
            
            # 윈도우 활성화
            win32gui.SetForegroundWindow(self.screenshot_hwnd)
            time.sleep(0.5)
            
            # 윈도우 정보 가져오기 및 표시
            left, top, right, bottom = win32gui.GetWindowRect(self.screenshot_hwnd)
            width, height = right - left, bottom - top
            
            window_title = win32gui.GetWindowText(self.screenshot_hwnd)
            print(f"타겟 윈도우: '{window_title}' (핸들: {self.screenshot_hwnd})")
            print(f"윈도우 위치: ({left}, {top}, {right}, {bottom}), 크기: {width}x{height}")
            
            # 템플릿 이미지 정보 확인
            template_path = os.path.join(self.templates_dir, f"{template_name}.png")
            if not os.path.exists(template_path):
                self.status_var.set(f"템플릿 이미지 파일 없음: {template_path}")
                messagebox.showerror("오류", f"템플릿 이미지를 찾을 수 없습니다: {template_name}")
                return False
            
            # 템플릿 이미지 크기 확인
            template = cv2.imread(template_path)
            if template is None:
                self.status_var.set(f"템플릿 이미지 로드 실패: {template_path}")
                messagebox.showerror("오류", f"템플릿 이미지 로드에 실패했습니다: {template_name}")
                return False
            
            template_h, template_w = template.shape[:2]
            print(f"템플릿 이미지: {template_name}.png (크기: {template_w}x{template_h})")
            
            # 스크린샷 캡처
            import pyautogui
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            screenshot = np.array(screenshot)
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            
            # 캡처 이미지 임시 저장 (디버깅용)
            debug_dir = os.path.join(self.base_dir, 'debug')
            os.makedirs(debug_dir, exist_ok=True)
            debug_path = os.path.join(debug_dir, 'last_capture.png')
            cv2.imwrite(debug_path, screenshot)
            print(f"디버깅용 캡처 저장: {debug_path}")
            
            # 이미지 인식
            self.status_var.set(f"이미지 인식 수행 중...")
            self.update()
            
            # 인식 결과
            found, position, confidence = self.image_recognition.find_template(
                screenshot, template_name, threshold=threshold
            )
            
            if found:
                # 이미지 발견, 위치 정보
                x, y, w, h = position
                center_x = x + w // 2
                center_y = y + h // 2
                
                print(f"이미지 발견: 위치=({x}, {y}), 크기={w}x{h}, 중심=({center_x}, {center_y}), 신뢰도={confidence:.4f}")
                self.status_var.set(f"이미지 발견: 위치=({x}, {y}), 신뢰도={confidence:.4f}")
                self.update()
                
                # 디버깅용: 발견된 위치 표시
                debug_img = screenshot.copy()
                cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(debug_img, (center_x, center_y), 5, (0, 0, 255), -1)
                
                debug_result_path = os.path.join(debug_dir, 'found_result.png')
                cv2.imwrite(debug_result_path, debug_img)
                print(f"인식 결과 이미지 저장: {debug_result_path}")
                
                # 캔버스에 표시 (발견 위치 보여주기)
                try:
                    # 캡처 이미지를 캔버스에 표시
                    self.screenshot = screenshot
                    screenshot_rgb = cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(screenshot_rgb)
                    
                    # 캔버스 크기 조정
                    self.screenshot_canvas.config(width=width, height=height)
                    
                    # 이미지 표시
                    img_tk = ImageTk.PhotoImage(pil_img)
                    self.screenshot_canvas.delete("all")
                    self.screenshot_canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
                    self.screenshot_canvas.image = img_tk  # 참조 유지
                    
                    # 발견 위치 표시
                    self.screenshot_canvas.create_rectangle(
                        x, y, x + w, y + h, outline="green", width=2, tags="found"
                    )
                    self.screenshot_canvas.create_oval(
                        center_x - 5, center_y - 5, center_x + 5, center_y + 5,
                        fill="red", outline="red", tags="center"
                    )
                    
                    self.update()
                except Exception as e:
                    print(f"결과 표시 오류: {e}")
                
                # 화면 좌표로 변환
                screen_x = left + center_x
                screen_y = top + center_y
                print(f"클릭 좌표 (화면 기준): ({screen_x}, {screen_y})")
                
                # 클릭 시도
                try:
                    # 1. 기존 방식
                    import pydirectinput
                    pydirectinput.PAUSE = 0.1
                    
                    # 현재 마우스 위치 저장
                    old_pos = pyautogui.position()
                    print(f"현재 마우스 위치: {old_pos}")
                    
                    # 좌표로 이동
                    print(f"마우스 이동 시도: ({screen_x}, {screen_y})")
                    pydirectinput.moveTo(screen_x, screen_y)
                    time.sleep(0.5)
                    
                    # 이동 후 위치 확인
                    new_pos = pyautogui.position()
                    print(f"이동 후 마우스 위치: {new_pos}")
                    
                    # 클릭
                    print("클릭 시도...")
                    pydirectinput.click(button="left")
                    time.sleep(0.2)
                    
                    print("클릭 완료")
                    
                    # 2. 대체 방식 (첫 번째가 실패한 경우)
                    if new_pos.x != screen_x or new_pos.y != screen_y:
                        print("첫 번째 방식 실패, 대체 방식 시도...")
                        
                        # Win32API 직접 사용
                        import win32api
                        import win32con
                        
                        # 마우스 이동
                        win32api.SetCursorPos((screen_x, screen_y))
                        time.sleep(0.5)
                        
                        # 클릭
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        time.sleep(0.1)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        
                        # 위치 확인
                        final_pos = pyautogui.position()
                        print(f"대체 방식 후 마우스 위치: {final_pos}")
                    
                    self.status_var.set(f"이미지 클릭 완료: {template_name}")
                    return True
                except Exception as e:
                    print(f"클릭 실패: {e}")
                    self.status_var.set(f"클릭 실패: {str(e)}")
                    return False
            else:
                print(f"이미지를 찾을 수 없음: 최대 신뢰도={confidence:.4f}, 임계값={threshold}")
                self.status_var.set(f"이미지를 찾을 수 없음: 신뢰도 {confidence:.4f} < 임계값 {threshold}")
                
                # 디버깅용: 최대 매칭 위치 표시
                try:
                    # 최대 매칭 위치 찾기 (threshold와 무관하게)
                    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    top_left = max_loc
                    bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
                    
                    debug_img = screenshot.copy()
                    cv2.rectangle(debug_img, top_left, bottom_right, (0, 0, 255), 2)
                    
                    debug_result_path = os.path.join(debug_dir, 'best_match.png')
                    cv2.imwrite(debug_result_path, debug_img)
                    print(f"최대 매칭 위치 이미지 저장: {debug_result_path} (신뢰도: {max_val:.4f})")
                except Exception as e:
                    print(f"디버깅 이미지 저장 오류: {e}")
                
                return False
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.status_var.set(f"이미지 검색 오류: {str(e)}")
            messagebox.showerror("오류", f"이미지 검색 중 오류 발생: {str(e)}")
            return False
    

if __name__ == "__main__":
    app = AutomationGUI()
    app.mainloop()