# main.py

import os
import sys
import time
import argparse
from settings.config_manager import ConfigManager
from monitoring.monitor_manager import MonitorManager

def parse_arguments():
    """
    명령줄 인수 파싱
    
    Returns:
        argparse.Namespace: 파싱된 인수
    """
    parser = argparse.ArgumentParser(description='윈도우 멀티 프로그램 자동화 시스템')
    
    parser.add_argument('--config-dir', dest='config_dir', default='./settings',
                        help='설정 파일 디렉토리 경로 (기본: ./settings)')
    
    parser.add_argument('--resources-dir', dest='resources_dir', default='./resources',
                        help='리소스 파일 디렉토리 경로 (기본: ./resources)')
    
    parser.add_argument('--init', action='store_true',
                        help='기본 설정 파일 생성')
    
    parser.add_argument('--add-program', dest='new_program',
                        help='새 프로그램 설정 추가')
    
    return parser.parse_args()

def initialize_config(config_dir):
    """
    기본 설정 파일 초기화
    
    Args:
        config_dir (str): 설정 디렉토리 경로
        
    Returns:
        bool: 성공 여부
    """
    config_manager = ConfigManager(config_dir)
    
    # 시스템 설정 생성
    success_sys = config_manager.create_default_system_config()
    
    # 샘플 프로그램 설정 생성
    success_prog = config_manager.create_default_program_config('sample_program', 'Sample Window')
    
    if success_sys and success_prog:
        print(f"기본 설정 파일이 생성되었습니다: {config_dir}")
        return True
    else:
        print("기본 설정 파일 생성 중 오류가 발생했습니다.")
        return False

def add_program_config(config_dir, program_name):
    """
    새 프로그램 설정 추가
    
    Args:
        config_dir (str): 설정 디렉토리 경로
        program_name (str): 프로그램 이름
        
    Returns:
        bool: 성공 여부
    """
    config_manager = ConfigManager(config_dir)
    
    window_title = input(f"윈도우 제목 (기본값: {program_name}): ").strip()
    if not window_title:
        window_title = program_name
    
    success = config_manager.create_default_program_config(program_name, window_title)
    
    if success:
        print(f"프로그램 설정이 추가되었습니다: {program_name}")
        return True
    else:
        print(f"프로그램 설정 추가 중 오류가 발생했습니다: {program_name}")
        return False

def main():
    """메인 함수"""
    args = parse_arguments()
    
    # 경로 설정
    config_dir = os.path.abspath(args.config_dir)
    resources_dir = os.path.abspath(args.resources_dir)
    
    # 기본 설정 초기화 모드
    if args.init:
        initialize_config(config_dir)
        return
    
    # 새 프로그램 설정 추가 모드
    if args.new_program:
        add_program_config(config_dir, args.new_program)
        return
    
    print("윈도우 멀티 프로그램 자동화 시스템 시작...")
    print(f"설정 디렉토리: {config_dir}")
    print(f"리소스 디렉토리: {resources_dir}")
    
    # 설정 확인
    config_manager = ConfigManager(config_dir)
    system_config = config_manager.load_system_config()
    
    if not system_config:
        print("시스템 설정을 찾을 수 없습니다. --init 옵션으로 기본 설정을 생성하세요.")
        return
    
    # 시작 지연 (설정에 따라)
    startup_delay = system_config.get('startup_delay', 0.0)
    if startup_delay > 0:
        print(f"{startup_delay}초 후 시작합니다...")
        time.sleep(startup_delay)
    
    # 모니터 관리자 초기화
    monitor_manager = MonitorManager(config_dir, resources_dir)
    
    # 모니터 생성 및 시작
    num_monitors = monitor_manager.create_monitors()
    print(f"생성된 모니터 수: {num_monitors}")
    
    if num_monitors > 0:
        num_started = monitor_manager.start_all_monitors()
        print(f"시작된 모니터 수: {num_started}")
    else:
        print("시작할 모니터가 없습니다. 프로그램 설정을 추가하세요.")
        return
    
    try:
        # 메인 루프
        while True:
            # 모니터 상태 표시
            status = monitor_manager.get_monitor_status()
            print("\n모니터 상태:")
            for name, info in status.items():
                state = "실행 중" if info['alive'] else "중지됨"
                if info['alive'] and info['paused']:
                    state = "일시 정지"
                print(f"  {name}: {state}")
            
            # 명령 입력
            print("\n명령:")
            print("  1. 모두 일시 정지")
            print("  2. 모두 재개")
            print("  3. 모두 중지")
            print("  4. 상태 업데이트")
            print("  0. 종료")
            
            cmd = input("\n선택: ").strip()
            
            if cmd == '1':
                monitor_manager.pause_all_monitors()
            elif cmd == '2':
                monitor_manager.resume_all_monitors()
            elif cmd == '3':
                monitor_manager.stop_all_monitors()
            elif cmd == '4':
                # 상태 업데이트만 (다음 루프에서 표시)
                pass
            elif cmd == '0':
                break
            else:
                print("알 수 없는 명령입니다.")
            
            time.sleep(0.5)  # 짧은 지연
    
    except KeyboardInterrupt:
        print("\n프로그램 종료 중...")
    finally:
        # 모든 모니터 중지
        monitor_manager.stop_all_monitors()
        print("모든 모니터가 중지되었습니다.")

if __name__ == "__main__":
    main()