# settings/config_manager.py

import os
import yaml
import shutil

class ConfigManager:
    """설정 파일 관리 클래스"""
    
    def __init__(self, config_dir):
        """
        설정 관리자 초기화
        
        Args:
            config_dir (str): 설정 파일 디렉토리
        """
        self.config_dir = config_dir
        self.system_config_path = os.path.join(config_dir, 'system_config.yaml')
        self.program_configs_dir = os.path.join(config_dir, 'program_configs')
        
        # 디렉토리 생성 (필요시)
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.program_configs_dir, exist_ok=True)
    
    def load_system_config(self):
        """
        시스템 설정 파일 로드
        
        Returns:
            dict: 시스템 설정
        """
        if os.path.exists(self.system_config_path):
            try:
                with open(self.system_config_path, 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file) or {}
            except Exception as e:
                print(f"시스템 설정 로드 오류: {e}")
                return {}
        else:
            return {}
    
    def save_system_config(self, config):
        """
        시스템 설정 파일 저장
        
        Args:
            config (dict): 시스템 설정
            
        Returns:
            bool: 성공 여부
        """
        try:
            with open(self.system_config_path, 'w', encoding='utf-8') as file:
                yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"시스템 설정 저장 오류: {e}")
            return False
    
    def load_program_config(self, program_name):
        """
        프로그램 설정 파일 로드
        
        Args:
            program_name (str): 프로그램 이름
            
        Returns:
            dict: 프로그램 설정
        """
        path = os.path.join(self.program_configs_dir, f"{program_name}.yaml")
        
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file) or {}
            except Exception as e:
                print(f"프로그램 설정 로드 오류 {program_name}: {e}")
                return {}
        else:
            return {}
    
    def save_program_config(self, program_name, config):
        """
        프로그램 설정 파일 저장
        
        Args:
            program_name (str): 프로그램 이름
            config (dict): 프로그램 설정
            
        Returns:
            bool: 성공 여부
        """
        path = os.path.join(self.program_configs_dir, f"{program_name}.yaml")
        
        try:
            with open(path, 'w', encoding='utf-8') as file:
                yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"프로그램 설정 저장 오류 {program_name}: {e}")
            return False
    
    def list_program_configs(self):
        """
        모든 프로그램 설정 파일 목록 반환
        
        Returns:
            list: 프로그램 이름 목록
        """
        configs = []
        
        if os.path.isdir(self.program_configs_dir):
            for filename in os.listdir(self.program_configs_dir):
                if filename.endswith('.yaml'):
                    # 확장자 제거
                    name = os.path.splitext(filename)[0]
                    configs.append(name)
        
        return configs
    
    def create_default_system_config(self):
        """
        기본 시스템 설정 생성
        
        Returns:
            bool: 성공 여부
        """
        default_config = {
            'monitoring_interval_default': 1.0,
            'enable_logging': True,
            'log_level': 'INFO',
            'startup_delay': 3.0,
            'max_monitors': 10
        }
        
        return self.save_system_config(default_config)
    
    def create_default_program_config(self, program_name, window_title=None):
        """
        기본 프로그램 설정 생성
        
        Args:
            program_name (str): 프로그램 이름
            window_title (str, optional): 윈도우 제목
            
        Returns:
            bool: 성공 여부
        """
        if not window_title:
            window_title = program_name
        
        default_config = {
            'name': program_name,
            'window_title': window_title,
            'window_class': None,
            'monitoring_interval': 1.0,
            'rules': [
                {
                    'template': 'sample_template',
                    'threshold': 0.8,
                    'actions': [
                        {
                            'type': 'click',
                            'params': {
                                'x': 100,
                                'y': 100,
                                'button': 'left'
                            },
                            'delay': 0.5
                        },
                        {
                            'type': 'wait',
                            'params': {
                                'seconds': 1.0
                            }
                        }
                    ]
                }
            ]
        }
        
        return self.save_program_config(program_name, default_config)