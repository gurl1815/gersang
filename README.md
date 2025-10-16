# 윈도우 멀티 프로그램 자동화 시스템

## 프로젝트 목적
여러 윈도우 프로그램을 동시에 모니터링하고, 이미지 인식을 통해 특정 상황을 감지하여 자동화 작업을 수행하는 시스템입니다. 윈도우 API를 활용해 직접 제어하는 방식으로 안정적이고 효율적인 자동화를 구현합니다.

## 시스템 구조

### 핵심 모듈
- **코어 모듈**: 윈도우 API 유틸리티, 이미지 인식 엔진, 액션 실행기
- **모니터 관리자**: 여러 프로그램 모니터 생성 및 관리
- **프로그램 모니터**: 개별 프로그램 모니터링 및 자동화 (동적 생성)
- **설정 관리**: YAML 기반 설정 파일 처리
- **GUI 인터페이스**: 사용자 편의성 강화를 위한 시각적 인터페이스

### 주요 기능
- 다중 프로그램 동시 모니터링 (스레드 기반)
- 이미지 인식을 통한 프로그램 상태 감지 (템플릿 매칭 및 히스토그램 비교)
- 윈도우 API 메시지 직접 전송으로 안정적 제어
- 설정 파일을 통한 프로그램 및 자동화 규칙 관리
- 템플릿 관리 및 테스트 기능
- 게임 모드 지원 (DirectX 게임 호환성)

## 기술 스택
- Python 3.8+
- pywin32 (윈도우 API)
- OpenCV (이미지 인식)
- YAML (설정 관리)
- Tkinter (GUI)
- PyDirectInput (게임 입력)
- PIL/Pillow (이미지 처리)

## 파일 구조
```
root/
├── core/                      # 코어 기능
│   ├── window_utils.py        # 윈도우 API 유틸리티
│   ├── image_recognition.py   # 이미지 인식 엔진
│   └── action_executor.py     # 액션 실행 유틸리티
├── monitoring/                # 모니터링 시스템
│   ├── monitor_manager.py     # 모니터 관리자
│   └── program_monitor.py     # 프로그램 모니터 클래스
├── settings/                  # 설정 파일
│   ├── config_manager.py      # 설정 관리자
│   ├── system_config.yaml     # 시스템 설정
│   └── program_configs/       # 프로그램별 설정
├── resources/                 # 리소스 파일
│   └── images/                # 인식 대상 이미지
├── gui.py                     # 그래픽 사용자 인터페이스
└── main.py                    # 메인 진입점
```

## 설치 방법
1. Python 3.8 이상 설치
2. 필요한 패키지 설치:
```
   pip install pywin32 opencv-python pyyaml pyautogui pydirectinput pillow
```
3. 프로그램 실행:
```
   python main.py
   # 또는 GUI 모드
   python gui.py
```

## 기본 사용법
- `python main.py --init`: 기본 설정 파일 생성
- `python main.py --add-program [이름]`: 새 프로그램 설정 추가
- `python gui.py`: GUI 모드로 시작

## 개발 현황
현재 개발 진행 상황은 [PROGRESS.md](PROGRESS.md) 파일에서 확인할 수 있습니다.