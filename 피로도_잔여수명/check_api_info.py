#!/usr/bin/env python
"""
API 정보 상세 확인
"""

import os

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# API 설정
API_KEY_ID = os.getenv("NAVER_API_KEY_ID")
API_KEY = os.getenv("NAVER_API_KEY")

print("=== API 키 정보 ===")
# 보안상 API 키를 직접 출력하지 않음
if API_KEY_ID:
    # 처음 4자리만 보여주고 나머지는 마스킹
    masked_id = API_KEY_ID[:4] + "*" * (len(API_KEY_ID) - 4) if len(API_KEY_ID) > 4 else "*" * len(API_KEY_ID)
    print(f"API_KEY_ID: {masked_id} (길이: {len(API_KEY_ID)})")
else:
    print("API_KEY_ID: 설정되지 않음")

if API_KEY:
    # 처음 4자리만 보여주고 나머지는 마스킹
    masked_key = API_KEY[:4] + "*" * (len(API_KEY) - 4) if len(API_KEY) > 4 else "*" * len(API_KEY)
    print(f"API_KEY: {masked_key} (길이: {len(API_KEY)})")
else:
    print("API_KEY: 설정되지 않음")

print("\n=== 확인 사항 ===")
print("1. Naver Cloud Platform Console (https://console.ncloud.com)")
print("2. AI·Application Service > AI·NAVER API > Application")
print("3. 애플리케이션 목록에서 사용 중인 애플리케이션 확인")
print("4. 애플리케이션 이름 클릭하여 상세 페이지 진입")
print("5. '서비스 선택' 섹션에서 다음 항목들 확인:")
print("   - Maps (Geocoding 포함)")
print("   - 또는 개별 Geocoding 서비스")
print("6. 체크되어 있지 않다면 체크 후 저장")
print("\n7. 혹시 '이용 신청' 또는 '결제 정보' 관련 메시지가 있는지 확인")
print("8. 무료 이용 조건: Maps API를 처음 사용한 대표 계정만 가능")

print("\n=== 대안 ===")
print("만약 Naver API가 계속 안 된다면:")
print("1. Kakao 주소 검색 API 사용 고려")
print("2. Google Geocoding API 사용 고려")
print("3. 한국 주소 전용 무료 API 검색")
