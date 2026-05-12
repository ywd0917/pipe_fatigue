#!/usr/bin/env python3
"""
Analyze remaining_life_years distribution for color mapping
목적: remaining_life_years 값의 분포를 분석하고 최적의 색상 매핑 공식 결정
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from typing import Tuple
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = ['AppleGothic', 'Malgun Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def load_data_with_remaining_life():
    """remaining_life_years 컬럼이 있는 데이터 로드"""

    # 가능한 파일 경로들
    file_paths = [
        "results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv",
        "results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv",
        "results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv",
        "results/main57_merge_fatigue/merged_fatigue_analysis.csv"
    ]

    all_data = []

    for file_path in file_paths:
        path = Path(file_path)
        if path.exists():
            try:
                df = pd.read_csv(path, encoding='utf-8-sig', low_memory=False)
                if 'remaining_life_years' in df.columns:
                    print(f"✓ {path.name}: {len(df):,}행 로드")
                    all_data.append(df[['remaining_life_years']].copy())
            except Exception as e:
                print(f"⚠️  {path.name} 로드 실패: {e}")

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        # NaN 값 제거
        combined_df = combined_df.dropna(subset=['remaining_life_years'])
        print(f"\n총 {len(combined_df):,}개 데이터 로드 완료")
        return combined_df
    else:
        raise FileNotFoundError("remaining_life_years 컬럼이 있는 파일을 찾을 수 없습니다.")


def analyze_distribution(df):
    """분포 통계 분석"""

    values = df['remaining_life_years'].values

    # 기본 통계
    stats_dict = {
        '개수': len(values),
        '최소값': np.min(values),
        '최대값': np.max(values),
        '평균': np.mean(values),
        '중앙값': np.median(values),
        '표준편차': np.std(values),
        '25분위수': np.percentile(values, 25),
        '75분위수': np.percentile(values, 75),
        '왜도(Skewness)': stats.skew(values),
        '첨도(Kurtosis)': stats.kurtosis(values)
    }

    # 특별한 값들의 비율
    stats_dict['0 이하 비율'] = (values <= 0).sum() / len(values) * 100
    stats_dict['10년 미만 비율'] = (values < 10).sum() / len(values) * 100
    stats_dict['50년 이상 비율'] = (values >= 50).sum() / len(values) * 100
    stats_dict['100년 이상 비율'] = (values >= 100).sum() / len(values) * 100

    print("\n" + "="*60)
    print("📊 Remaining Life Years 분포 통계")
    print("="*60)

    for key, value in stats_dict.items():
        if '비율' in key:
            print(f"{key:15s}: {value:8.2f}%")
        elif key == '개수':
            print(f"{key:15s}: {value:8,}")
        else:
            print(f"{key:15s}: {value:8.2f}")

    return stats_dict


def visualize_distributions(df):
    """다양한 분포 시각화"""

    values = df['remaining_life_years'].values

    # 이상치 제거를 위한 IQR 방법
    Q1 = np.percentile(values, 25)
    Q3 = np.percentile(values, 75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # 시각화용 데이터 준비
    values_clipped = np.clip(values, 0, np.percentile(values, 99))  # 99분위수로 클리핑

    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    fig.suptitle('Remaining Life Years 분포 분석', fontsize=16, fontweight='bold')

    # 1. 원본 히스토그램
    ax = axes[0, 0]
    ax.hist(values, bins=50, edgecolor='black', alpha=0.7)
    ax.set_title('원본 분포')
    ax.set_xlabel('Remaining Life (years)')
    ax.set_ylabel('빈도')
    ax.axvline(0, color='red', linestyle='--', label='0년')
    ax.legend()

    # 2. 클리핑된 히스토그램
    ax = axes[0, 1]
    ax.hist(values_clipped, bins=50, edgecolor='black', alpha=0.7, color='green')
    ax.set_title('99분위수 클리핑 분포')
    ax.set_xlabel('Remaining Life (years)')
    ax.set_ylabel('빈도')

    # 3. 로그 스케일 히스토그램
    ax = axes[0, 2]
    positive_values = values[values > 0]
    if len(positive_values) > 0:
        ax.hist(positive_values, bins=50, edgecolor='black', alpha=0.7, color='orange')
        ax.set_xscale('log')
        ax.set_title('로그 스케일 분포 (양수값만)')
        ax.set_xlabel('Remaining Life (log scale)')

    # 4. 박스플롯
    ax = axes[1, 0]
    ax.boxplot(values_clipped, vert=False)
    ax.set_title('박스플롯 (99분위수 클리핑)')
    ax.set_xlabel('Remaining Life (years)')

    # 5. 바이올린 플롯
    ax = axes[1, 1]
    ax.violinplot(values_clipped, vert=False, showmeans=True, showmedians=True)
    ax.set_title('바이올린 플롯')
    ax.set_xlabel('Remaining Life (years)')

    # 6. CDF (누적분포함수)
    ax = axes[1, 2]
    sorted_values = np.sort(values)
    cdf = np.arange(1, len(sorted_values) + 1) / len(sorted_values)
    ax.plot(sorted_values, cdf)
    ax.set_title('누적분포함수 (CDF)')
    ax.set_xlabel('Remaining Life (years)')
    ax.set_ylabel('누적 확률')
    ax.grid(True, alpha=0.3)
    ax.axvline(0, color='red', linestyle='--', alpha=0.5)
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5)

    # 7. Q-Q Plot (정규분포 검정)
    ax = axes[2, 0]
    stats.probplot(values_clipped, dist="norm", plot=ax)
    ax.set_title('Q-Q Plot (정규분포 검정)')

    # 8. 로그 변환 후 분포
    ax = axes[2, 1]
    log_values = np.log1p(np.maximum(values, 0))  # log(1+x) 변환
    ax.hist(log_values, bins=50, edgecolor='black', alpha=0.7, color='purple')
    ax.set_title('Log(1+x) 변환 분포')
    ax.set_xlabel('Log(1 + Remaining Life)')

    # 9. 구간별 비율
    ax = axes[2, 2]
    bins = [0, 5, 10, 20, 30, 50, 100, np.inf]
    labels = ['0-5', '5-10', '10-20', '20-30', '30-50', '50-100', '100+']
    counts, _ = np.histogram(values, bins=bins)
    ax.bar(labels, counts / len(values) * 100)
    ax.set_title('구간별 비율')
    ax.set_xlabel('Remaining Life 구간 (years)')
    ax.set_ylabel('비율 (%)')
    ax.tick_params(axis='x', rotation=45)

    plt.tight_layout()

    # 결과 저장
    output_path = Path("results/result_analysis11_remaining_life/remaining_life_distribution.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n📊 분포 시각화 저장: {output_path}")

    # plt.show()  # 대화형 모드 비활성화


def test_color_mappings(df):
    """다양한 색상 매핑 공식 테스트"""

    values = df['remaining_life_years'].values

    # 양수값만 추출 (색상 매핑용)
    positive_values = values[values > 0]

    # 색상 매핑 함수들
    def linear_mapping(x, vmin=0, vmax=100):
        """선형 매핑"""
        return np.clip((x - vmin) / (vmax - vmin), 0, 1)

    def log_mapping(x, vmin=0.1, vmax=100):
        """로그 매핑"""
        x_safe = np.maximum(x, vmin)
        return np.clip((np.log10(x_safe) - np.log10(vmin)) /
                      (np.log10(vmax) - np.log10(vmin)), 0, 1)

    def sqrt_mapping(x, vmin=0, vmax=100):
        """제곱근 매핑"""
        x_safe = np.maximum(x, 0)
        return np.clip(np.sqrt(x_safe / vmax), 0, 1)

    def sigmoid_mapping(x, center=30, scale=10):
        """시그모이드 매핑"""
        return 1 / (1 + np.exp(-(x - center) / scale))

    def piecewise_mapping(x):
        """구간별 매핑"""
        conditions = [
            x <= 0,
            (x > 0) & (x <= 5),
            (x > 5) & (x <= 10),
            (x > 10) & (x <= 20),
            (x > 20) & (x <= 50),
            x > 50
        ]
        choices = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        return np.select(conditions, choices)

    # 샘플 값들로 테스트
    test_values = np.array([0, 1, 5, 10, 20, 30, 50, 75, 100, 150])

    print("\n" + "="*80)
    print("🎨 색상 매핑 공식 비교")
    print("="*80)
    print(f"{'값(년)':<10} {'선형':<10} {'로그':<10} {'제곱근':<10} {'시그모이드':<10} {'구간별':<10}")
    print("-"*60)

    for val in test_values:
        linear = linear_mapping(val)
        log = log_mapping(val) if val > 0 else 0
        sqrt = sqrt_mapping(val)
        sigmoid = sigmoid_mapping(val)
        piecewise = piecewise_mapping(val)

        print(f"{val:<10.0f} {linear:<10.3f} {log:<10.3f} {sqrt:<10.3f} "
              f"{sigmoid:<10.3f} {piecewise:<10.3f}")

    # 매핑 시각화
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('색상 매핑 함수 비교', fontsize=16, fontweight='bold')

    x_range = np.linspace(0, 100, 1000)

    # 1. 선형 매핑
    ax = axes[0, 0]
    y = linear_mapping(x_range)
    ax.plot(x_range, y, 'b-', linewidth=2)
    ax.set_title('선형 매핑')
    ax.set_xlabel('Remaining Life (years)')
    ax.set_ylabel('색상 값 (0=빨강, 1=초록)')
    ax.grid(True, alpha=0.3)
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5)

    # 2. 로그 매핑
    ax = axes[0, 1]
    y = log_mapping(x_range)
    ax.plot(x_range, y, 'g-', linewidth=2)
    ax.set_title('로그 매핑')
    ax.set_xlabel('Remaining Life (years)')
    ax.set_ylabel('색상 값')
    ax.grid(True, alpha=0.3)
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5)

    # 3. 제곱근 매핑
    ax = axes[0, 2]
    y = sqrt_mapping(x_range)
    ax.plot(x_range, y, 'orange', linewidth=2)
    ax.set_title('제곱근 매핑')
    ax.set_xlabel('Remaining Life (years)')
    ax.set_ylabel('색상 값')
    ax.grid(True, alpha=0.3)
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5)

    # 4. 시그모이드 매핑
    ax = axes[1, 0]
    y = sigmoid_mapping(x_range)
    ax.plot(x_range, y, 'purple', linewidth=2)
    ax.set_title('시그모이드 매핑 (center=30)')
    ax.set_xlabel('Remaining Life (years)')
    ax.set_ylabel('색상 값')
    ax.grid(True, alpha=0.3)
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(30, color='red', linestyle='--', alpha=0.5, label='center')
    ax.legend()

    # 5. 구간별 매핑
    ax = axes[1, 1]
    y = piecewise_mapping(x_range)
    ax.plot(x_range, y, 'red', linewidth=2)
    ax.set_title('구간별 매핑')
    ax.set_xlabel('Remaining Life (years)')
    ax.set_ylabel('색상 값')
    ax.grid(True, alpha=0.3)

    # 6. 실제 데이터 분포와 매핑 비교
    ax = axes[1, 2]
    sample = np.random.choice(positive_values, min(1000, len(positive_values)), replace=False)
    sample_clipped = np.clip(sample, 0, 100)

    # 각 매핑 적용
    colors = {
        '선형': linear_mapping(sample_clipped),
        '로그': log_mapping(sample_clipped),
        '제곱근': sqrt_mapping(sample_clipped),
        '시그모이드': sigmoid_mapping(sample_clipped)
    }

    positions = np.arange(len(colors))
    for i, (name, color_values) in enumerate(colors.items()):
        ax.violinplot([color_values], positions=[i], showmeans=True)

    ax.set_xticks(positions)
    ax.set_xticklabels(colors.keys())
    ax.set_title('실제 데이터에 대한 색상 값 분포')
    ax.set_ylabel('색상 값 분포')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # 결과 저장
    output_path = Path("results/result_analysis11_remaining_life/color_mapping_comparison.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n📊 색상 매핑 비교 저장: {output_path}")

    # plt.show()  # 대화형 모드 비활성화


def recommend_mapping(stats_dict):
    """데이터 특성에 따른 최적 매핑 추천"""

    print("\n" + "="*80)
    print("💡 추천 색상 매핑 공식")
    print("="*80)

    skewness = stats_dict['왜도(Skewness)']
    zero_ratio = stats_dict['0 이하 비율']
    median = stats_dict['중앙값']
    q75 = stats_dict['75분위수']

    recommendations = []

    # 1. 왜도가 높은 경우 (오른쪽 꼬리가 긴 분포)
    if skewness > 2:
        recommendations.append({
            'method': '로그 매핑',
            'reason': f'왜도가 {skewness:.2f}로 매우 높음 (긴 꼬리 분포)',
            'formula': 'color = log10(max(x, 0.1)) / log10(100)',
            'pros': '극단값의 영향 감소, 낮은 값 구간 세분화',
            'cons': '0 이하 값 처리 필요'
        })

    # 2. 0 이하 값이 많은 경우
    if zero_ratio > 10:
        recommendations.append({
            'method': '구간별 매핑',
            'reason': f'0 이하 비율이 {zero_ratio:.1f}%로 높음',
            'formula': '0이하: 빨강(0), 0-10: 주황(0.3), 10-30: 노랑(0.6), 30+: 초록(1.0)',
            'pros': '명확한 위험도 구분, 직관적',
            'cons': '연속성 부족'
        })

    # 3. 중앙값 기준 시그모이드
    recommendations.append({
        'method': '시그모이드 매핑',
        'reason': f'중앙값({median:.1f}년) 중심의 부드러운 전환',
        'formula': f'color = 1 / (1 + exp(-(x - {median:.0f}) / {median/3:.0f}))',
        'pros': '부드러운 색상 전환, 중앙값 근처 세분화',
        'cons': '극단값 구분 어려움'
    })

    # 4. 제곱근 매핑 (균형잡힌 경우)
    if 1 < skewness < 3:
        recommendations.append({
            'method': '제곱근 매핑',
            'reason': '적당한 비선형성으로 균형잡힌 표현',
            'formula': 'color = sqrt(max(x, 0) / 75)',
            'pros': '낮은 값 강조, 계산 단순',
            'cons': '높은 값 구분 약함'
        })

    # 최종 추천
    print("\n🏆 최종 추천:")

    if skewness > 3 and zero_ratio > 5:
        print("""
╔══════════════════════════════════════════════════════════════╗
║ 하이브리드 접근법 (로그 + 구간별)                           ║
╠══════════════════════════════════════════════════════════════╣
║ def hybrid_color_mapping(x):                                ║
║     if x <= 0:                                              ║
║         return (1.0, 0.0, 0.0)  # 빨강                     ║
║     elif x < 5:                                             ║
║         return (1.0, 0.5, 0.0)  # 주황                     ║
║     elif x < 10:                                            ║
║         return (1.0, 1.0, 0.0)  # 노랑                     ║
║     else:                                                   ║
║         # 로그 스케일로 노랑→초록 그라데이션               ║
║         t = np.clip(np.log10(x/10) / np.log10(10), 0, 1)  ║
║         return (1-t, 1.0, 0.0)  # 노랑→초록               ║
╚══════════════════════════════════════════════════════════════╝
        """)
    else:
        print("""
╔══════════════════════════════════════════════════════════════╗
║ 조정된 로그 매핑                                            ║
╠══════════════════════════════════════════════════════════════╣
║ def adjusted_log_mapping(x):                                ║
║     if x <= 0:                                              ║
║         return (1.0, 0.0, 0.0)  # 빨강                     ║
║     else:                                                   ║
║         # log(1+x) 변환으로 0 근처 값도 부드럽게 처리      ║
║         t = np.clip(np.log1p(x) / np.log1p(50), 0, 1)     ║
║         # 빨강→노랑→초록 그라데이션                       ║
║         if t < 0.5:                                         ║
║             return (1.0, 2*t, 0.0)                         ║
║         else:                                               ║
║             return (2-2*t, 1.0, 0.0)                       ║
╚══════════════════════════════════════════════════════════════╝
        """)

    print("\n📌 추천 세부사항:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['method']}")
        print(f"   이유: {rec['reason']}")
        print(f"   공식: {rec['formula']}")
        print(f"   장점: {rec['pros']}")
        print(f"   단점: {rec['cons']}")


def create_color_map_functions():
    """실제 사용 가능한 색상 매핑 함수들 생성"""

    output_path = Path("src/analysis/analyze11_color_mapping_functions.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    code = '''"""
Remaining Life Years 색상 매핑 함수들
생성일: 2025-01-16
"""

import numpy as np
from typing import Tuple, Union


def get_rgb_color_linear(remaining_life: float,
                         vmin: float = 0,
                         vmax: float = 50) -> Tuple[float, float, float]:
    """
    선형 색상 매핑
    0 -> 빨강 (1,0,0)
    vmax -> 초록 (0,1,0)
    """
    if remaining_life <= vmin:
        return (1.0, 0.0, 0.0)
    elif remaining_life >= vmax:
        return (0.0, 1.0, 0.0)
    else:
        t = (remaining_life - vmin) / (vmax - vmin)
        return (1-t, t, 0.0)


def get_rgb_color_log(remaining_life: float,
                      vmax: float = 50) -> Tuple[float, float, float]:
    """
    로그 색상 매핑 (추천)
    log(1+x) 변환으로 낮은 값 구간 세분화
    """
    if remaining_life <= 0:
        return (1.0, 0.0, 0.0)  # 빨강

    # log(1+x) 변환
    t = np.clip(np.log1p(remaining_life) / np.log1p(vmax), 0, 1)

    # 빨강 -> 노랑 -> 초록 그라데이션
    if t < 0.5:
        # 빨강(1,0,0) -> 노랑(1,1,0)
        return (1.0, 2*t, 0.0)
    else:
        # 노랑(1,1,0) -> 초록(0,1,0)
        return (2-2*t, 1.0, 0.0)


def get_rgb_color_hybrid(remaining_life: float) -> Tuple[float, float, float]:
    """
    하이브리드 색상 매핑 (가장 추천)
    위험 구간별 명확한 색상 + 그라데이션
    """
    if remaining_life <= 0:
        return (1.0, 0.0, 0.0)  # 빨강 (즉시 교체)
    elif remaining_life < 5:
        # 빨강 -> 주황 그라데이션
        t = remaining_life / 5
        return (1.0, 0.5 * t, 0.0)
    elif remaining_life < 10:
        # 주황 -> 노랑 그라데이션
        t = (remaining_life - 5) / 5
        return (1.0, 0.5 + 0.5 * t, 0.0)
    elif remaining_life < 30:
        # 노랑 -> 연두 그라데이션
        t = (remaining_life - 10) / 20
        return (1.0 - 0.5 * t, 1.0, 0.0)
    else:
        # 연두 -> 초록 (안전)
        t = np.clip((remaining_life - 30) / 20, 0, 1)
        return (0.5 - 0.5 * t, 1.0, 0.0)


def get_hex_color(rgb: Tuple[float, float, float]) -> str:
    """RGB (0-1) 값을 HEX 색상 코드로 변환"""
    r = int(rgb[0] * 255)
    g = int(rgb[1] * 255)
    b = int(rgb[2] * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def get_color_for_remaining_life(remaining_life: float,
                                 method: str = "hybrid") -> str:
    """
    Remaining life 값에 대한 HEX 색상 반환

    Parameters:
    -----------
    remaining_life: 잔존 수명 (년)
    method: "linear", "log", "hybrid" (기본값: hybrid)

    Returns:
    --------
    HEX 색상 코드 (예: "#FF0000")
    """
    if method == "linear":
        rgb = get_rgb_color_linear(remaining_life)
    elif method == "log":
        rgb = get_rgb_color_log(remaining_life)
    else:  # hybrid
        rgb = get_rgb_color_hybrid(remaining_life)

    return get_hex_color(rgb)


# 사용 예시
if __name__ == "__main__":
    test_values = [0, 1, 5, 10, 20, 30, 50, 100]

    print("Remaining Life -> Color Mapping")
    print("="*50)
    print(f"{'Years':<10} {'Linear':<10} {'Log':<10} {'Hybrid':<10}")
    print("-"*40)

    for val in test_values:
        linear = get_color_for_remaining_life(val, "linear")
        log = get_color_for_remaining_life(val, "log")
        hybrid = get_color_for_remaining_life(val, "hybrid")
        print(f"{val:<10} {linear:<10} {log:<10} {hybrid:<10}")
'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"\n✅ 색상 매핑 함수 저장: {output_path}")


def main():
    """메인 실행 함수"""

    print("="*80)
    print("Remaining Life Years 분포 분석 및 색상 매핑 최적화")
    print("="*80)

    try:
        # 1. 데이터 로드
        df = load_data_with_remaining_life()

        # 2. 분포 통계 분석
        stats_dict = analyze_distribution(df)

        # 3. 분포 시각화
        visualize_distributions(df)

        # 4. 색상 매핑 테스트
        test_color_mappings(df)

        # 5. 최적 매핑 추천
        recommend_mapping(stats_dict)

        # 6. 실제 사용 가능한 함수 생성
        create_color_map_functions()

        print("\n" + "="*80)
        print("✅ 분석 완료!")
        print("="*80)
        print("\n생성된 파일:")
        print("1. results/result_analysis11_remaining_life/remaining_life_distribution.png - 분포 시각화")
        print("2. results/result_analysis11_remaining_life/color_mapping_comparison.png - 색상 매핑 비교")
        print("3. src/analysis/analyze11_color_mapping_functions.py - 실제 사용 함수")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()