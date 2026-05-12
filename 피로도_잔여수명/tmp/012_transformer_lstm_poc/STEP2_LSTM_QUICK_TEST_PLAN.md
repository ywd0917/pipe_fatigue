# Step 2: Simple LSTM Quick Test 상세 계획

**작성일**: 2025-12-11
**예상 시간**: 4-6시간
**목적**: 최소 구현으로 LSTM 가능성 빠르게 검증

---

## 📋 배경

**Step 1 결과**: 70점 - GO 판정
- PACF: **89개 유의 lag** (Phase 4의 past_60은 매우 부족!)
- 권장 Sequence Length: **300**
- LSTM ✅ 적합, Transformer ⚠️ 신중

**핵심 질문**: LSTM이 정말 Recursive prediction 문제를 해결하는가?

---

## 🎯 테스트 3가지

### Test A: 1-step-ahead 예측 (Baseline)

#### 목적
XGBoost Phase 4와 비교 - LSTM이 기본적으로 작동하는지 확인

#### 방법
```python
# 과거 300개 → 다음 1개 예측
X = data[i-300:i]
y = data[i]

# Validation set에서 평가
```

#### 기대 성과
- R² > 0.99 (Phase 4 XGBoost: 0.9984)
- MAE < 0.001

#### 의미
- ✅ R² > 0.99: LSTM이 기본적으로 작동
- ❌ R² < 0.95: LSTM 구현 문제

---

### Test B: 10-step 비재귀 예측 ⭐ **핵심**

#### 목적
**Recursive prediction 회피** 효과 검증 - 가장 중요한 테스트!

#### 방법
```python
# 과거 300개 → 미래 10개를 한 번에 예측
X = data[i-300:i]         # (batch, 300, 1)
y = data[i:i+10]          # (batch, 10)

# Multi-output LSTM
model = Sequential([
    LSTM(256, input_shape=(300, 1), return_sequences=False),
    Dropout(0.2),
    Dense(128, activation='relu'),
    Dense(10)  # 10개 출력
])
```

#### 기대 성과
| 결과 | R² | 의미 | 판정 |
|------|-----|------|------|
| 🎯 **최고** | > 0.5 | Recursive 회피 성공 | ✅ **Phase 5 진행** |
| ⚠️ **보통** | 0.1 - 0.5 | 효과 있지만 제한적 | △ Step 3 확인 |
| ❌ **실패** | < 0.1 | Recursive 회피 못함 | ❌ **포기** |

**Phase 4와 비교**:
- Phase 4 Recursive (865 step): R² -0.016
- Step 2 Non-recursive (10 step): R² 0.5? ← **이게 핵심!**

#### 의미
- **R² > 0.5**: Transformer/LSTM 진행 가치 있음
- **R² < 0.1**: Recursive prediction 문제가 아니라 **데이터 자체가 예측 불가능**

---

### Test C: 고주파 예측 가능성

#### 목적
주파수 분리 유지 여부 결정

#### 방법
```python
# Phase 1 주파수 분리
low_freq, high_freq = pass_filter(data)

# 고주파만 LSTM 학습 (10-step)
X_high = high_freq[i-300:i]
y_high = high_freq[i:i+10]
```

#### 기대 성과
| 결과 | R² | 의미 | 판정 |
|------|-----|------|------|
| 🎯 **가능** | > 0.1 | 고주파 패턴 학습 가능 | ✅ 주파수 분리 유지 |
| ⚠️ **보통** | 0.05 - 0.1 | 약한 효과 | △ 원본 데이터 직접 사용 |
| ❌ **불가** | < 0.05 | 고주파 예측 불가 | ❌ 주파수 분리 포기 |

**Phase 4와 비교**:
- Phase 4 고주파 Validation R²: 0.0216
- Phase 4 고주파 Gap R²: 0.0002
- Step 2 고주파 10-step R²: 0.1? ← **개선 여부 확인**

#### 의미
- **R² > 0.1**: LSTM이 고주파 패턴을 일부 학습 가능
- **R² < 0.05**: 고주파는 여전히 예측 불가 → 원본 데이터 직접 사용

---

## 🔧 구현 세부사항

### 1. 데이터 준비

#### a) 데이터 로드 및 정규화
```python
# 로드
df = data_loader.load_pressure_data('0243')
data = df['wtrprsr'].values

# 정규화 (MinMax or StandardScaler)
from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()
data_scaled = scaler.fit_transform(data.reshape(-1, 1)).flatten()
```

#### b) 시퀀스 생성
```python
def create_sequences(data, seq_len=300, pred_len=1):
    """
    시퀀스 생성

    Args:
        data: 1D array
        seq_len: 입력 시퀀스 길이
        pred_len: 예측 길이 (1 or 10)

    Returns:
        X: (N, seq_len, 1)
        y: (N, pred_len)
    """
    X, y = [], []
    for i in range(seq_len, len(data) - pred_len + 1):
        X.append(data[i-seq_len:i])
        y.append(data[i:i+pred_len])

    return np.array(X).reshape(-1, seq_len, 1), np.array(y)
```

#### c) Train/Validation/Test 분할
```python
# 시간 순서 유지
train_size = int(len(X) * 0.7)
val_size = int(len(X) * 0.15)

X_train, y_train = X[:train_size], y[:train_size]
X_val, y_val = X[train_size:train_size+val_size], y[train_size:train_size+val_size]
X_test, y_test = X[train_size+val_size:], y[train_size+val_size:]
```

### 2. 모델 아키텍처

#### Test A/B용: Simple LSTM
```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

def build_lstm_model(seq_len=300, pred_len=1, hidden_dim=256):
    """
    간단한 LSTM 모델

    Args:
        seq_len: 입력 길이
        pred_len: 출력 길이 (1 or 10)
        hidden_dim: LSTM hidden dimension

    Returns:
        Keras model
    """
    model = Sequential([
        LSTM(hidden_dim, input_shape=(seq_len, 1), return_sequences=False),
        Dropout(0.2),
        Dense(128, activation='relu'),
        Dropout(0.2),
        Dense(pred_len)
    ])

    model.compile(
        optimizer='adam',
        loss='mse',
        metrics=['mae']
    )

    return model
```

**파라미터 수**:
- LSTM(256): ~265K parameters
- Dense layers: ~33K
- **Total: ~300K** (학습 가능)

#### Test C용: 주파수 분리 LSTM
```python
# 동일한 아키텍처, 데이터만 다름
model_low = build_lstm_model(seq_len=300, pred_len=10, hidden_dim=256)
model_high = build_lstm_model(seq_len=300, pred_len=10, hidden_dim=128)
```

### 3. 학습 설정

#### 하이퍼파라미터
```python
BATCH_SIZE = 64
EPOCHS = 50  # Early stopping 사용
LEARNING_RATE = 0.001
```

#### Early Stopping & Callbacks
```python
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

callbacks = [
    EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    ),
    ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        min_lr=1e-6
    )
]
```

#### 학습
```python
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    batch_size=BATCH_SIZE,
    epochs=EPOCHS,
    callbacks=callbacks,
    verbose=1
)
```

### 4. 평가 지표

```python
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

def evaluate_model(model, X, y, scaler):
    """
    모델 평가

    Returns:
        dict with r2, mae, mse, predictions
    """
    # 예측
    y_pred = model.predict(X)

    # 역정규화
    if y.ndim == 2 and y.shape[1] > 1:
        # Multi-output (10-step)
        y_true_orig = scaler.inverse_transform(y)
        y_pred_orig = scaler.inverse_transform(y_pred)
    else:
        # Single output (1-step)
        y_true_orig = scaler.inverse_transform(y.reshape(-1, 1)).flatten()
        y_pred_orig = scaler.inverse_transform(y_pred.reshape(-1, 1)).flatten()

    # 지표 계산
    r2 = r2_score(y_true_orig.flatten(), y_pred_orig.flatten())
    mae = mean_absolute_error(y_true_orig.flatten(), y_pred_orig.flatten())
    mse = mean_squared_error(y_true_orig.flatten(), y_pred_orig.flatten())

    return {
        'r2': r2,
        'mae': mae,
        'mse': mse,
        'y_true': y_true_orig,
        'y_pred': y_pred_orig
    }
```

---

## 📊 성공 기준 및 의사결정

### Test A: 1-step-ahead

| 결과 | 조치 |
|------|------|
| R² > 0.99 | ✅ Test B 진행 |
| R² < 0.95 | ❌ LSTM 구현 점검 |

### Test B: 10-step ⭐ **핵심**

| R² 범위 | 판정 | Phase 5 진행 여부 | 예상 3일 gap 성능 |
|---------|------|-------------------|-------------------|
| **> 0.5** | ✅ **성공** | **GO - 전체 진행** | R² 0.3 - 0.5 |
| **0.3 - 0.5** | ⚠️ **보통** | **GO - 신중** | R² 0.1 - 0.3 |
| **0.1 - 0.3** | △ **약함** | Step 3 확인 후 결정 | R² 0 - 0.1 |
| **< 0.1** | ❌ **실패** | **NO-GO - 포기** | R² < 0 |

**판단 로직**:
```
IF Test B R² > 0.5:
    → Phase 5 전체 진행 (Bidirectional LSTM + Transformer)
    → 성공 확률: 60-70%

ELIF Test B R² > 0.3:
    → Step 3 (Bidirectional Interpolation) 확인
    → Phase 5 신중히 진행
    → 성공 확률: 40-60%

ELIF Test B R² > 0.1:
    → Step 3 반드시 확인
    → Phase 5 보류 고려
    → 성공 확률: 20-40%

ELSE:
    → Phase 5 포기
    → LSTM/Transformer는 해결책 아님
    → Gap 허용 정책 검토
```

### Test C: 고주파

| R² 범위 | 판정 | 전략 |
|---------|------|------|
| > 0.1 | ✅ 학습 가능 | 주파수 분리 유지 |
| 0.05 - 0.1 | △ 약한 효과 | 원본 데이터 직접 사용 |
| < 0.05 | ❌ 예측 불가 | 주파수 분리 포기 |

---

## 🕐 예상 시간

| 단계 | 시간 | 세부 |
|------|------|------|
| 데이터 준비 | 30분 | 시퀀스 생성, 분할 |
| Test A 구현 | 1시간 | 모델, 학습, 평가 |
| Test A 학습 | 30분 | 50 epochs (early stopping) |
| Test B 구현 | 1시간 | Multi-output 수정 |
| Test B 학습 | 1시간 | 50 epochs |
| Test C 구현 | 30분 | 주파수 분리 적용 |
| Test C 학습 | 1.5시간 | 저주파/고주파 각각 |
| 시각화 | 30분 | 3-4개 그래프 |
| 보고서 | 1시간 | Markdown |
| **총 예상** | **7-8시간** | (여유 포함 4-6시간 → 7-8시간) |

**Note**: Test B 결과에 따라 Test C 생략 가능 (R² < 0.1이면 중단)

---

## 📄 출력 형식

### 산출물 1: results/lstm_test_results.md

```markdown
# LSTM Quick Test 결과

**실행 일시**: 2025-12-11
**Sequence Length**: 300 (Step 1 권장)

---

## Test A: 1-step-ahead

- Validation R²: 0.9987
- MAE: 0.0008
- 판정: ✅ 기본 작동

## Test B: 10-step 비재귀 ⭐

- Validation R²: **0.45**
- MAE: 0.032
- 판정: ⚠️ 보통 (Step 3 확인 필요)

**Phase 4와 비교**:
| Method | Type | R² |
|--------|------|-----|
| Phase 4 XGBoost | Recursive (3일) | -0.016 |
| **Step 2 LSTM** | **Non-recursive (10-step)** | **0.45** |
| **개선**: +0.466

## Test C: 고주파

- 저주파 R²: 0.52
- 고주파 R²: 0.08
- 판정: △ 약한 효과 → 원본 데이터 직접 사용

---

## 최종 판정

### ✅ GO - Phase 5 신중히 진행

**이유**: 10-step R² 0.45로 Recursive 회피 효과 확인

**다음 단계**:
1. Step 3: Bidirectional Interpolation으로 추가 검증
2. 성공 시 Phase 5 진행

**예상 3일 gap 성능**: R² 0.1 - 0.3
```

### 산출물 2: 시각화

1. **Test A: 1-step 예측 vs 실제** (시계열 그래프)
2. **Test B: 10-step 예측 vs 실제** (다중 그래프, 각 step별)
3. **Test B: R² by step** (1-step ~ 10-step 성능 변화)
4. **Test C: 주파수별 성능** (저주파 vs 고주파)
5. **Loss curves** (Train/Validation)

### 산출물 3: JSON

```json
{
  "timestamp": "2025-12-11 ...",
  "sequence_length": 300,
  "test_a": {
    "r2": 0.9987,
    "mae": 0.0008,
    "judgment": "success"
  },
  "test_b": {
    "r2": 0.45,
    "mae": 0.032,
    "judgment": "fair",
    "comparison_phase4": {
      "phase4_r2": -0.016,
      "improvement": 0.466
    }
  },
  "test_c": {
    "low_freq_r2": 0.52,
    "high_freq_r2": 0.08,
    "judgment": "use_original"
  },
  "final_decision": {
    "decision": "GO - cautious",
    "next_step": "Step 3 required",
    "expected_3day_gap_r2": "0.1 - 0.3"
  }
}
```

---

## 🚦 GO/NO-GO 결정

### GO 조건 (Phase 5 진행)

✅ **다음 중 하나**:
1. Test B R² > 0.5 → **즉시 Phase 5 진행**
2. Test B R² > 0.3 → **Step 3 확인 후 진행**
3. Test B R² > 0.1 **AND** Test C R² > 0.1 → **신중히 진행**

### NO-GO 조건 (중단)

❌ **다음 중 하나**:
1. Test A R² < 0.95 → **LSTM 구현 문제**
2. Test B R² < 0.1 → **Recursive prediction이 문제가 아님, 데이터 자체가 예측 불가능**
3. Test B R² < 0 → **완전 실패**

---

## 💡 핵심 통찰

### Test B가 가장 중요한 이유

**Phase 4 실패**:
```
Validation (1-step): R² 0.9984 ✅
Gap (865-step recursive): R² -0.016 ❌

문제: Recursive prediction 오류 누적
```

**Step 2 검증**:
```
Test A (1-step): R² 0.99? ✅
Test B (10-step non-recursive): R² 0.5? ✅

검증: Non-recursive가 효과 있는가?
```

**만약 Test B R² > 0.5**:
→ **Recursive prediction이 진짜 문제였음!**
→ Transformer/Bidirectional LSTM으로 해결 가능
→ Phase 5 진행 정당화

**만약 Test B R² < 0.1**:
→ **Recursive prediction이 문제가 아님**
→ 데이터 자체가 10-step 예측도 못함
→ Phase 5 진행해도 실패 가능성 높음
→ 포기 고려

---

## 📚 참고: Phase 4와 비교

| 항목 | Phase 4 XGBoost | Step 2 LSTM |
|------|-----------------|-------------|
| Sequence Length | 60 | **300** (5배) |
| Method | Recursive | **Non-recursive** |
| 1-step Val R² | 0.9984 | 0.99? |
| Gap/10-step R² | -0.016 (recursive) | **0.5?** (non-recursive) |
| 고주파 Val R² | 0.0216 | **0.08?** |

**핵심 차이**:
1. **Sequence Length**: 60 → 300 (PACF 89개 lag 반영)
2. **Prediction Type**: Recursive → Non-recursive

---

## 🚀 다음 단계

### Test B R² > 0.5 시
→ **Step 3 (Bidirectional Interpolation) 진행**
→ Phase 5 준비

### Test B R² 0.1-0.5 시
→ **Step 3 필수 확인**
→ Step 3 성공 시 Phase 5 신중히 진행

### Test B R² < 0.1 시
→ **DECISION_REPORT 작성**
→ Phase 5 포기 → Gap 허용 정책

---

**작성일**: 2025-12-11
**예상 시간**: 7-8시간 (실제 4-6시간)
**핵심 질문**: 10-step 비재귀 예측이 가능한가?
**답**: 실험으로 확인! 🔬
