# monitoring/monitor_manager.py

import os
import yaml
import time
from .program_monitor import ProgramMonitor

class MonitorManager:
    """여러 프로그램 모니터 생성 및 관리"""
    
    def __init__(self, config_dir, resources_dir=None):
        """
        모니터 관리자 초기화
        
        Args:
            config_dir (str): 설정 파일 디렉토리
            resources_dir (str, optional): 리소스 디렉토리
        """
        self.config_dir = config_dir
        self.resources_dir = resources_dir
        self.monitors = {}  # 이름 -> 모니터 객체
        self.system_config = None
        
        # 시스템 설정 로드
        self.load_system_config()
    
    def load_system_config(self):
        """시스템 설정 파일 로드"""
        system_config_path = os.path.join(self.config_dir, 'system_config.yaml')
        
        if os.path.exists(system_config_path):
            try:
                with open(system_config_path, 'r', encoding='utf-8') as file:
                    self.system_config = yaml.safe_load(file)
            except Exception as e:
                print(f"시스템 설정 로드 오류: {e}")
                self.system_config = {}
        else:
            print("시스템 설정 파일을 찾을 수 없습니다.")
            self.system_config = {}
    
    def load_program_configs(self):
        """
        모든 프로그램 설정 로드
        
        Returns:
            list: 프로그램 설정 목록
        """
        configs = []
        program_configs_dir = os.path.join(self.config_dir, 'program_configs')
        
        if not os.path.isdir(program_configs_dir):
            print(f"프로그램 설정 디렉토리를 찾을 수 없습니다: {program_configs_dir}")
            return configs
        
        for filename in os.listdir(program_configs_dir):
            if filename.endswith('.yaml'):
                path = os.path.join(program_configs_dir, filename)
                try:
                    with open(path, 'r', encoding='utf-8') as file:
                        config = yaml.safe_load(file)
                        if config:
                            configs.append(config)
                except Exception as e:
                    print(f"설정 파일 로드 오류 {filename}: {e}")
        
        return configs
    
    def create_monitors(self):
        """
        프로그램 모니터 생성
        
        Returns:
            int: 생성된 모니터 수
        """
        program_configs = self.load_program_configs()
        count = 0
        
        for config in program_configs:
            name = config.get('name')
            if not name:
                continue
            
            try:
                # 이미 존재하는 모니터인지 확인
                if name in self.monitors and self.monitors[name].is_alive():
                    print(f"모니터가 이미 실행 중입니다: {name}")
                    continue
                
                # 새 모니터 생성
                monitor = ProgramMonitor(config, self.resources_dir)
                self.monitors[name] = monitor
                count += 1
            except Exception as e:
                print(f"모니터 생성 오류 {name}: {e}")
        
        return count
    
    def start_all_monitors(self):
        """
        모든 모니터 시작
        
        Returns:
            int: 시작된 모니터 수
        """
        count = 0
        
        for name, monitor in self.monitors.items():
            if not monitor.is_alive():
                try:
                    monitor.start()
                    count += 1
                    print(f"모니터 시작: {name}")
                except Exception as e:
                    print(f"모니터 시작 오류 {name}: {e}")
        
        return count
    
    def stop_all_monitors(self):
        """
        모든 모니터 중지
        
        Returns:
            int: 중지된 모니터 수
        """
        count = 0
        
        for name, monitor in self.monitors.items():
            if monitor.is_alive():
                try:
                    monitor.stop()
                    # 스레드 종료 대기 (옵션, 필요시)
                    monitor.join(1.0)
                    count += 1
                    print(f"모니터 중지: {name}")
                except Exception as e:
                    print(f"모니터 중지 오류 {name}: {e}")
        
        return count
    
    def pause_all_monitors(self):
        """
        모든 모니터 일시 정지
        
        Returns:
            int: 일시 정지된 모니터 수
        """
        count = 0
        
        for name, monitor in self.monitors.items():
            if monitor.is_alive() and not monitor.paused:
                try:
                    monitor.pause()
                    count += 1
                    print(f"모니터 일시 정지: {name}")
                except Exception as e:
                    print(f"모니터 일시 정지 오류 {name}: {e}")
        
        return count
    
    def resume_all_monitors(self):
        """
        모든 모니터 재개
        
        Returns:
            int: 재개된 모니터 수
        """
        count = 0
        
        for name, monitor in self.monitors.items():
            if monitor.is_alive() and monitor.paused:
                try:
                    monitor.resume()
                    count += 1
                    print(f"모니터 재개: {name}")
                except Exception as e:
                    print(f"모니터 재개 오류 {name}: {e}")
        
        return count
    
    def get_monitor_status(self):
        """
        모든 모니터 상태 확인
        
        Returns:
            dict: 모니터 상태 정보
        """
        status = {}
        
        for name, monitor in self.monitors.items():
            status[name] = {
                'alive': monitor.is_alive(),
                'paused': monitor.paused if monitor.is_alive() else None,
                'hwnd': monitor.hwnd if monitor.is_alive() else None,
                'window_title': monitor.window_title
            }
        
        return status