#!/usr/bin/env python3
"""
main13a K_repair 계산을 위한 거리 기반 가중치 방식 비교 시각화

세 가지 가중치 방식을 비교:
1. Linear (선형 감소)
2. Inverse Distance (역거리)  
3. Gaussian (가우시안)
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager
import platform

# 한글 폰트 설정
def setup_korean_font():
    """한글 폰트 설정"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        font_prop = font_manager.FontProperties(fname=font_path)
        plt.rc('font', family=font_prop.get_name())
    elif system == "Windows":
        plt.rc('font', family='Malgun Gothic')
    else:  # Linux
        plt.rc('font', family='DejaVu Sans')
    
    # 마이너스 부호 깨짐 방지
    plt.rc('axes', unicode_minus=False)

def linear_weight(distance, max_distance=30):
    """선형 가중치: 거리가 증가할수록 선형적으로 감소"""
    return np.maximum(0, 1 - (distance / max_distance))

def inverse_distance_weight(distance, alpha=1.0):
    """역거리 가중치: 거리에 반비례"""
    return 1 / (1 + alpha * distance)

def gaussian_weight(distance, sigma=10):
    """가우시안 가중치: 정규분포 형태로 감소"""
    return np.exp(-(distance**2) / (2 * sigma**2))

def plot_weight_comparison():
    """세 가지 가중치 방식 비교 그래프"""
    setup_korean_font()
    
    # 거리 범위 설정 (0-40m)
    distances = np.linspace(0, 40, 400)
    max_distance = 30  # 기본 버퍼 크기
    
    # 각 방식별 가중치 계산
    weights_linear = linear_weight(distances, max_distance)
    weights_inverse = inverse_distance_weight(distances, alpha=0.1)  # alpha 조정으로 감소율 제어
    weights_gaussian = gaussian_weight(distances, sigma=max_distance/3)
    
    # 그래프 생성
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('main13a K_repair 거리 기반 가중치 방식 비교', fontsize=16, fontweight='bold')
    
    # 1. 개별 가중치 곡선
    ax1 = axes[0, 0]
    ax1.plot(distances, weights_linear, 'b-', linewidth=2, label='선형 (Linear)')
    ax1.plot(distances, weights_inverse, 'g-', linewidth=2, label='역거리 (Inverse Distance)')
    ax1.plot(distances, weights_gaussian, 'r-', linewidth=2, label='가우시안 (Gaussian)')
    ax1.axvline(x=30, color='gray', linestyle='--', alpha=0.5, label='현재 버퍼 (30m)')
    ax1.set_xlabel('파이프로부터의 거리 (m)')
    ax1.set_ylabel('가중치')
    ax1.set_title('가중치 함수 비교')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right')
    ax1.set_xlim(0, 40)
    ax1.set_ylim(-0.05, 1.05)
    
    # 2. 30m 이내 확대
    ax2 = axes[0, 1]
    mask = distances <= 30
    ax2.plot(distances[mask], weights_linear[mask], 'b-', linewidth=2, label='선형')
    ax2.plot(distances[mask], weights_inverse[mask], 'g-', linewidth=2, label='역거리')
    ax2.plot(distances[mask], weights_gaussian[mask], 'r-', linewidth=2, label='가우시안')
    ax2.fill_between(distances[mask], 0, weights_linear[mask], alpha=0.2, color='blue')
    ax2.fill_between(distances[mask], 0, weights_inverse[mask], alpha=0.2, color='green')
    ax2.fill_between(distances[mask], 0, weights_gaussian[mask], alpha=0.2, color='red')
    ax2.set_xlabel('거리 (m)')
    ax2.set_ylabel('가중치')
    ax2.set_title('30m 버퍼 내 가중치 분포')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    ax2.set_xlim(0, 30)
    ax2.set_ylim(0, 1.05)
    
    # 3. 특정 거리에서의 가중치 비교 (막대 그래프)
    ax3 = axes[1, 0]
    sample_distances = [0, 5, 10, 15, 20, 25, 30]
    linear_values = [linear_weight(d, max_distance) for d in sample_distances]
    inverse_values = [inverse_distance_weight(d, 0.1) for d in sample_distances]
    gaussian_values = [gaussian_weight(d, max_distance/3) for d in sample_distances]
    
    x = np.arange(len(sample_distances))
    width = 0.25
    
    bars1 = ax3.bar(x - width, linear_values, width, label='선형', color='blue', alpha=0.7)
    bars2 = ax3.bar(x, inverse_values, width, label='역거리', color='green', alpha=0.7)
    bars3 = ax3.bar(x + width, gaussian_values, width, label='가우시안', color='red', alpha=0.7)
    
    ax3.set_xlabel('거리 (m)')
    ax3.set_ylabel('가중치')
    ax3.set_title('주요 거리별 가중치 값')
    ax3.set_xticks(x)
    ax3.set_xticklabels(sample_distances)
    ax3.legend()
    ax3.grid(True, axis='y', alpha=0.3)
    
    # 막대 위에 값 표시
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0.01:  # 너무 작은 값은 표시하지 않음
                ax3.annotate(f'{height:.2f}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),  # 3 points vertical offset
                           textcoords="offset points",
                           ha='center', va='bottom',
                           fontsize=8)
    
    # 4. 실제 적용 예시
    ax4 = axes[1, 1]
    
    # 파이프 위치 (중앙)
    pipe_x = 20
    pipe_y = 20
    
    # 재작업 위치들 (다양한 거리)
    repairs = [
        (20, 22, 2),    # 2m 거리
        (25, 20, 5),    # 5m 거리
        (20, 30, 10),   # 10m 거리
        (35, 20, 15),   # 15m 거리
        (20, 0, 20),    # 20m 거리
        (45, 20, 25),   # 25m 거리
    ]
    
    # 시각화를 위한 그리드
    ax4.set_xlim(-5, 50)
    ax4.set_ylim(-5, 45)
    ax4.set_aspect('equal')
    
    # 파이프 그리기
    ax4.plot(pipe_x, pipe_y, 'ko', markersize=10, label='파이프')
    
    # 30m 버퍼 원 그리기
    circle = plt.Circle((pipe_x, pipe_y), 30, color='gray', fill=False, 
                        linestyle='--', linewidth=1, alpha=0.5)
    ax4.add_patch(circle)
    
    # 재작업 점들과 가중치 표시
    for x, y, dist in repairs:
        # 각 방식별 가중치 계산
        w_linear = linear_weight(dist, max_distance)
        w_inverse = inverse_distance_weight(dist, 0.1)
        w_gaussian = gaussian_weight(dist, max_distance/3)
        
        # 점 그리기
        ax4.plot(x, y, 'ro', markersize=8)
        
        # 거리 선 그리기
        ax4.plot([pipe_x, x], [pipe_y, y], 'k--', alpha=0.2)
        
        # 가중치 정보 표시
        text = f'{dist}m\nL:{w_linear:.2f}\nI:{w_inverse:.2f}\nG:{w_gaussian:.2f}'
        ax4.annotate(text, xy=(x, y), xytext=(3, 3), 
                    textcoords='offset points', fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
    
    ax4.set_xlabel('X 좌표 (m)')
    ax4.set_ylabel('Y 좌표 (m)')
    ax4.set_title('실제 적용 예시 (L:선형, I:역거리, G:가우시안)')
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc='upper left')
    
    plt.tight_layout()
    
    # 결과 저장
    output_path = 'results/tmp/weight_methods_comparison.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"그래프 저장 완료: {output_path}")
    
    # plt.show() 제거 - 창을 띄우지 않음
    plt.close()  # 메모리 정리

def print_weight_table():
    """주요 거리에서의 가중치 값 테이블 출력"""
    print("\n" + "="*70)
    print("거리별 가중치 비교 테이블")
    print("="*70)
    
    distances = [0, 5, 10, 15, 20, 25, 30, 35]
    max_distance = 30
    
    # 헤더
    print(f"{'거리(m)':>8} | {'단순카운트':>10} | {'선형':>10} | {'역거리':>10} | {'가우시안':>10}")
    print("-"*70)
    
    # 각 거리별 값 출력
    for d in distances:
        simple = 1.0 if d <= 30 else 0.0
        linear = linear_weight(d, max_distance)
        inverse = inverse_distance_weight(d, 0.1)
        gaussian = gaussian_weight(d, max_distance/3)
        
        print(f"{d:>8} | {simple:>10.2f} | {linear:>10.3f} | "
              f"{inverse:>10.3f} | {gaussian:>10.3f}")
    
    print("\n" + "="*70)
    print("가중치 방식별 특징:")
    print("-"*70)
    print("1. 단순 카운트: 30m 이내 모두 1, 이외 0 (현재 방식)")
    print("2. 선형: 거리에 비례하여 선형적으로 감소")
    print("3. 역거리: 가까운 거리에서 급격히 감소, 먼 거리에서 완만")
    print("4. 가우시안: 자연스러운 종 모양 감소 곡선")
    print("="*70)
    
    # 각 방식의 30m 누적 가중치 계산
    print("\n30m 내 총 가중치 (1m 간격 재작업 가정):")
    print("-"*70)
    
    total_simple = sum(1.0 for d in range(0, 31))
    total_linear = sum(linear_weight(d, max_distance) for d in range(0, 31))
    total_inverse = sum(inverse_distance_weight(d, 0.1) for d in range(0, 31))
    total_gaussian = sum(gaussian_weight(d, max_distance/3) for d in range(0, 31))
    
    print(f"단순 카운트: {total_simple:.1f}")
    print(f"선형: {total_linear:.1f}")
    print(f"역거리: {total_inverse:.1f}")
    print(f"가우시안: {total_gaussian:.1f}")
    print("="*70)

if __name__ == "__main__":
    import os
    
    # 결과 디렉토리 생성
    os.makedirs('results/tmp', exist_ok=True)
    
    # 테이블 출력
    print_weight_table()
    
    # 그래프 생성
    print("\n그래프 생성 중...")
    plot_weight_comparison()
    
    print("\n완료! results/tmp/weight_methods_comparison.png 파일을 확인하세요.")