# STEP 2: IAAFT Test Results

**Date**: 2025-12-12
**Area**: 0243
**Method**: ARMA + IAAFT

## Summary

### IAAFT vs Random Phase (Baseline)

| Gap | Component | Baseline CCR | IAAFT CCR | Improvement |
|-----|-----------|-------------|-----------|-------------|
| 7days | low | 0.800 | 0.889 | +11.1% |
| 7days | high | 0.793 | 0.795 | +0.2% |
| 14days | low | 0.829 | 0.944 | +13.9% |
| 14days | high | 0.786 | 0.793 | +0.9% |
| 24days | low | 0.868 | 0.819 | -5.6% |
| 24days | high | 0.781 | 0.781 | +0.0% |

## Detailed Results

### 7days Gap

**High Frequency (IAAFT)**:
- Cycles: 2714 → 3415
- CCR: 0.7947 ✗
- ADS: 0.9683 ✓
- FDR: 0.9991 ✓

### 14days Gap

**High Frequency (IAAFT)**:
- Cycles: 5350 → 6749
- CCR: 0.7927 ✗
- ADS: 0.9716 ✓
- FDR: 1.2671 ✗

### 24days Gap

**High Frequency (IAAFT)**:
- Cycles: 9175 → 11743
- CCR: 0.7813 ✗
- ADS: 0.9713 ✓
- FDR: 1.2761 ✗

## Conclusion

❌ **LIMITED IMPROVEMENT**

IAAFT only achieved CCR 0.795
May need alternative approaches (GARCH/SV).
