# core/image_recognition.py

import cv2
import numpy as np
import os

class ImageRecognition:
    """이미지 인식 엔진"""
    
    def __init__(self, templates_dir=None):
        """
        이미지 인식 엔진 초기화
        
        Args:
            templates_dir (str, optional): 템플릿 이미지 디렉토리 경로
        """
        self.templates = {}
        self.templates_dir = templates_dir
        
        # 템플릿 디렉토리가 제공된 경우 이미지 로드
        if templates_dir and os.path.isdir(templates_dir):
            self.load_templates(templates_dir)
    
    def load_templates(self, directory):
        """
        디렉토리에서 모든 템플릿 이미지 로드
        
        Args:
            directory (str): 템플릿 이미지 디렉토리 경로
            
        Returns:
            int: 로드된 템플릿 수
        """
        count = 0
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                path = os.path.join(directory, filename)
                name = os.path.splitext(filename)[0]
                template = cv2.imread(path)
                
                if template is not None:
                    self.templates[name] = template
                    count += 1
        
        return count
    
    def add_template(self, name, image):
        """
        템플릿 이미지 추가
        
        Args:
            name (str): 템플릿 이름
            image (numpy.ndarray): 템플릿 이미지
        """
        self.templates[name] = image
    
    def find_template(self, image, template_name, threshold=0.5, method=cv2.TM_CCOEFF_NORMED):
        """
        이미지에서 템플릿 찾기 (유사 이미지 검색 개선 버전)
        
        Args:
            image (numpy.ndarray): 검색할 이미지
            template_name (str): 찾을 템플릿 이름
            threshold (float): 매칭 임계값 (0.0-1.0)
            method (int): 매칭 방법 (OpenCV 상수)
            
        Returns:
            tuple: (found, position, confidence)
                found (bool): 찾았는지 여부
                position (tuple): (x, y, w, h) 위치와 크기
                confidence (float): 매칭 신뢰도 (0.0-1.0)
        """
        # 템플릿이 존재하는지 확인
        if template_name not in self.templates:
            return False, (0, 0, 0, 0), 0.0
        
        template = self.templates[template_name]
        
        # 이미지와 템플릿이 유효한지 확인
        if image is None or template is None:
            return False, (0, 0, 0, 0), 0.0
        
        # 다양한 방법으로 매칭 시도
        best_confidence = 0
        best_position = (0, 0, 0, 0)
        
        # 1. 원본 이미지로 매칭 (기존 방식)
        h, w = template.shape[:2]
        
        # 이미지와 템플릿이 동일한 색상 채널을 가지고 있는지 확인
        img_to_use = image
        template_to_use = template
        if len(image.shape) != len(template.shape):
            if len(image.shape) == 3:
                template_to_use = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                img_to_use = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 템플릿 매칭 수행
        try:
            result = cv2.matchTemplate(img_to_use, template_to_use, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 매칭 방법에 따라 값 조정
            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                confidence = 1 - min_val
                top_left = min_loc
            else:
                confidence = max_val
                top_left = max_loc
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_position = (top_left[0], top_left[1], w, h)
        except:
            pass
        
        # 2. 그레이스케일로 변환하여 매칭 (색상 무시)
        try:
            if len(image.shape) == 3 and len(template.shape) == 3:
                img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                
                result = cv2.matchTemplate(img_gray, template_gray, method)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # 매칭 방법에 따라 값 조정
                if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                    confidence = 1 - min_val
                    top_left = min_loc
                else:
                    confidence = max_val
                    top_left = max_loc
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_position = (top_left[0], top_left[1], w, h)
        except:
            pass
        
        # 임계값과 비교
        if best_confidence >= threshold:
            return True, best_position, best_confidence
        else:
            return False, (0, 0, 0, 0), best_confidence
    
    def find_all_templates(self, image, template_name, threshold=0.8, method=cv2.TM_CCOEFF_NORMED):
        """
        이미지에서 모든 템플릿 매칭 찾기
        
        Args:
            image (numpy.ndarray): 검색할 이미지
            template_name (str): 찾을 템플릿 이름
            threshold (float): 매칭 임계값 (0.0-1.0)
            method (int): 매칭 방법 (OpenCV 상수)
            
        Returns:
            list: [(x, y, w, h, confidence), ...] 형태의 매칭 목록
        """
        # 템플릿이 존재하는지 확인
        if template_name not in self.templates:
            return []
        
        template = self.templates[template_name]
        
        # 이미지와 템플릿이 유효한지 확인
        if image is None or template is None:
            return []
        
        # 이미지와 템플릿이 동일한 색상 채널을 가지고 있는지 확인
        if len(image.shape) != len(template.shape):
            if len(image.shape) == 3:
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 템플릿 매칭 수행
        h, w = template.shape[:2]
        result = cv2.matchTemplate(image, template, method)
        
        # 임계값 이상의 모든 매칭 찾기
        matches = []
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            result = 1 - result
        
        # 임계값 이상인 위치 찾기
        locations = np.where(result >= threshold)
        
        # 모든 매칭을 목록에 추가
        for pt in zip(*locations[::-1]):
            confidence = result[pt[1], pt[0]]
            matches.append((pt[0], pt[1], w, h, float(confidence)))
        
        # 중복 제거 (거리 기준)
        filtered_matches = []
        for match in sorted(matches, key=lambda x: x[4], reverse=True):
            if not any(self._is_duplicate(match, existing, threshold=w//2) for existing in filtered_matches):
                filtered_matches.append(match)
        
        return filtered_matches
    
    def _is_duplicate(self, match1, match2, threshold=10):
        """
        두 매칭이 중복인지 확인 (내부 사용)
        
        Args:
            match1 (tuple): (x, y, w, h, confidence) 형태의 매칭1
            match2 (tuple): (x, y, w, h, confidence) 형태의 매칭2
            threshold (int): 중복으로 판단할 거리
            
        Returns:
            bool: 중복 여부
        """
        x1, y1 = match1[0], match1[1]
        x2, y2 = match2[0], match2[1]
        distance = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
        return distance < threshold
    
    def find_by_histogram(self, image, template_name, threshold=0.85):
        """
        색상 히스토그램을 사용하여 이미지 영역 찾기
        (회전, 반전에 강인함)
        
        Args:
            image: 검색할 이미지 (현재 캡처된 화면)
            template_name: 찾을 템플릿 이름 (사용자가 지정한 템플릿)
            threshold: 매칭 임계값 (0.0-1.0)
            
        Returns:
            tuple: (found, position, confidence)
        """
        # 템플릿이 존재하는지 확인
        if template_name not in self.templates:
            print(f"템플릿을 찾을 수 없음: {template_name}")
            return False, (0, 0, 0, 0), 0.0
        
        # 템플릿 이미지 가져오기
        template = self.templates[template_name]
        
        # 이미지 유효성 검사
        if image is None or template is None:
            print("이미지 또는 템플릿이 None입니다")
            return False, (0, 0, 0, 0), 0.0
        
        # 디버깅 정보
        print(f"템플릿 '{template_name}' 검색: 템플릿 크기={template.shape}, 이미지 크기={image.shape}")
        
        # 템플릿 크기
        template_h, template_w = template.shape[:2]
        
        # 먼저 일반 템플릿 매칭으로 후보 영역 찾기
        try:
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold * 0.7)  # 낮은 임계값 사용
            
            # 후보 위치가 없으면 실패
            if len(locations[0]) == 0:
                print(f"템플릿 매칭으로 후보 영역을 찾지 못함: {template_name}")
                return False, (0, 0, 0, 0), 0.0
        except Exception as e:
            print(f"템플릿 매칭 오류: {e}")
            return False, (0, 0, 0, 0), 0.0
        
        # 템플릿의 히스토그램 계산
        template_hist = self._calc_color_histogram(template)
        
        # 결과 저장용 변수
        best_match = {
            'position': (0, 0, 0, 0),
            'confidence': 0.0
        }
        
        # 각 후보 위치에 대해 히스토그램 비교
        for pt in zip(*locations[::-1]):  # [::-1] - (x,y) 순서로 변환
            x, y = pt
            
            # 영역이 이미지 밖으로 나가면 스킵
            if x + template_w > image.shape[1] or y + template_h > image.shape[0]:
                continue
            
            # 후보 영역 추출
            roi = image[y:y+template_h, x:x+template_w]
            
            # 후보 영역의 히스토그램 계산
            roi_hist = self._calc_color_histogram(roi)
            
            # 히스토그램 비교 (상관관계 방식 - 값이 높을수록 유사)
            hist_match = cv2.compareHist(template_hist, roi_hist, cv2.HISTCMP_CORREL)
            
            # 더 좋은 매칭 결과 저장
            if hist_match > best_match['confidence']:
                best_match['position'] = (x, y, template_w, template_h)
                best_match['confidence'] = hist_match
        
        # 결과 반환
        found = best_match['confidence'] >= threshold
        print(f"히스토그램 매칭 결과: 발견={found}, 신뢰도={best_match['confidence']:.4f}, 임계값={threshold}")
        return found, best_match['position'], best_match['confidence']

    def _calc_color_histogram(self, img):
        """
        이미지의 색상 히스토그램 계산
        
        Args:
            img: 이미지
            
        Returns:
            히스토그램
        """
        # 색상 공간을 HSV로 변환
        if len(img.shape) == 3:  # 컬러 이미지
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # H, S, V 각각 히스토그램 계산
            h_hist = cv2.calcHist([hsv], [0], None, [30], [0, 180])
            s_hist = cv2.calcHist([hsv], [1], None, [32], [0, 256])
            v_hist = cv2.calcHist([hsv], [2], None, [32], [0, 256])
            
            # 정규화
            h_hist = cv2.normalize(h_hist, h_hist, 0, 1, cv2.NORM_MINMAX)
            s_hist = cv2.normalize(s_hist, s_hist, 0, 1, cv2.NORM_MINMAX)
            v_hist = cv2.normalize(v_hist, v_hist, 0, 1, cv2.NORM_MINMAX)
            
            # 히스토그램 연결
            return np.concatenate((h_hist, s_hist, v_hist))
        else:  # 그레이스케일
            hist = cv2.calcHist([img], [0], None, [64], [0, 256])
            return cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)