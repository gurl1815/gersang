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
    
    def find_template(self, image, template_name, threshold=0.8, method=cv2.TM_CCOEFF_NORMED):
        """
        이미지에서 템플릿 찾기
        
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
        
        # 이미지와 템플릿이 동일한 색상 채널을 가지고 있는지 확인
        if len(image.shape) != len(template.shape):
            if len(image.shape) == 3:
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 템플릿 매칭 수행
        h, w = template.shape[:2]
        result = cv2.matchTemplate(image, template, method)
        
        # 최대 매칭 위치 찾기
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # 매칭 방법에 따라 값 조정
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            confidence = 1 - min_val
            top_left = min_loc
        else:
            confidence = max_val
            top_left = max_loc
        
        # 임계값과 비교
        if confidence >= threshold:
            position = (top_left[0], top_left[1], w, h)
            return True, position, confidence
        else:
            return False, (0, 0, 0, 0), confidence
    
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