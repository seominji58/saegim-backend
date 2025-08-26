#!/usr/bin/env python3
"""
이미지 썸네일 생성 스크립트
uploads/images 폴더의 이미지들을 썸네일로 변환하여 uploads/thumbnails 폴더에 저장
"""

import os
from PIL import Image
import glob

def create_thumbnail(input_path, output_path, size=(150, 150), quality=85):
    """
    이미지를 썸네일로 변환
    
    Args:
        input_path: 입력 이미지 경로
        output_path: 출력 썸네일 경로
        size: 썸네일 크기 (기본값: 150x150)
        quality: JPEG 품질 (기본값: 85)
    """
    try:
        # 이미지 열기
        with Image.open(input_path) as img:
            # RGB 모드로 변환 (RGBA 등 다른 모드 지원)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 원본 비율 유지하면서 리사이즈
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 출력 디렉토리 생성
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 파일 확장자에 따라 저장
            file_ext = os.path.splitext(output_path)[1].lower()
            if file_ext in ['.jpg', '.jpeg']:
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
            elif file_ext == '.png':
                img.save(output_path, 'PNG', optimize=True)
            else:
                # 기본적으로 JPEG로 저장
                output_path = os.path.splitext(output_path)[0] + '.jpg'
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
            print(f"✅ 썸네일 생성 완료: {os.path.basename(output_path)}")
            
    except Exception as e:
        print(f"❌ 썸네일 생성 실패 ({os.path.basename(input_path)}): {str(e)}")

def main():
    """메인 함수"""
    # 경로 설정
    images_dir = "uploads/images"
    thumbnails_dir = "uploads/thumbnails"
    
    # 썸네일 크기 설정
    thumbnail_size = (150, 150)
    
    print("🖼️  이미지 썸네일 생성 시작...")
    print(f"📁 이미지 폴더: {images_dir}")
    print(f"📁 썸네일 폴더: {thumbnails_dir}")
    print(f"📏 썸네일 크기: {thumbnail_size[0]}x{thumbnail_size[1]}")
    print("-" * 50)
    
    # 이미지 파일들 찾기
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(images_dir, ext)))
        image_files.extend(glob.glob(os.path.join(images_dir, ext.upper())))
    
    if not image_files:
        print("❌ 이미지 파일을 찾을 수 없습니다.")
        return
    
    print(f"📸 발견된 이미지: {len(image_files)}개")
    
    # 각 이미지에 대해 썸네일 생성
    for image_path in image_files:
        # 파일명과 확장자 분리
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        
        # 썸네일 파일명 생성 (원본 확장자 유지)
        thumbnail_filename = f"{name}_thumb{ext}"
        thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
        
        print(f"\n🔄 처리 중: {filename}")
        create_thumbnail(image_path, thumbnail_path, thumbnail_size)
    
    print("\n" + "=" * 50)
    print("🎉 모든 썸네일 생성 완료!")
    
    # 생성된 썸네일 목록 출력
    thumbnail_files = glob.glob(os.path.join(thumbnails_dir, "*_thumb.*"))
    if thumbnail_files:
        print(f"\n📋 생성된 썸네일 ({len(thumbnail_files)}개):")
        for thumb in thumbnail_files:
            print(f"  - {os.path.basename(thumb)}")
    else:
        print("\n⚠️  썸네일이 생성되지 않았습니다.")

if __name__ == "__main__":
    main()
