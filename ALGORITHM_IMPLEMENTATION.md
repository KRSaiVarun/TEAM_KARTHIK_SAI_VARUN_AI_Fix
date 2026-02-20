# 🔄 Scoring Algorithm Implementation Guide

## Quick Decision

**Current Algorithm:** ❌ Penalty-based (can go negative)

```
Score = 100 + 10 (speed) - 60 (commits) + 4 (quality) = 54 😭
```

**Pure Bonus Algorithm:** ✅ Reward-based (always positive)

```
Score = 100 + 10 (speed) + 0 (commit) + 16 (quality) = 126 😊
```

---

## Available Algorithms

### 1️⃣ CURRENT ALGORITHM (Hybrid Penalty)

**File:** `client/src/components/ScoreBreakdownPanel.tsx`

```typescript
// Current implementation in the component
const speedBonus = completionTime > 0 && completionTime < 300 ? 10 : 0;
const commitPenalty = Math.max(0, (commitCount - 20) * 2); // PENALTY!
const qualityBonus =
  totalBugsDetected > 0
    ? Math.round((totalBugsFixed / totalBugsDetected) * 5)
    : 0;

const finalScore = baseScore + speedBonus - commitPenalty + qualityBonus;
```

**Formula:** `100 + speedBonus - commitPenalty + qualityBonus`

**Characteristics:**

- ❌ Score can go negative
- ❌ Harsh penalty for commits
- ✅ Simple
- ✅ Penalizes inefficiency

---

### 2️⃣ PURE BONUS ALGORITHM (Simple Reward)

**Better for most hackathons!**

```typescript
const speedBonus =
  completionTime > 0 && completionTime < 180
    ? 15
    : completionTime < 300
      ? 10
      : completionTime < 600
        ? 5
        : 0;

const commitBonus = Math.max(0, 30 - commitCount); // BONUS not penalty!

const qualityBonus =
  totalBugsDetected > 0
    ? Math.round((totalBugsFixed / totalBugsDetected) * 20) // More rewarding
    : 0;

const finalScore = baseScore + speedBonus + commitBonus + qualityBonus;
```

**Formula:** `100 + speedBonus + commitBonus + qualityBonus`

**Characteristics:**

- ✅ Score always positive (min 100)
- ✅ Fair for large projects
- ✅ Everyone feels good
- ✅ Encourages participation

**Max Score:** 165 (100 + 15 + 30 + 20)
**Min Score:** 100

---

### 3️⃣ EXPONENTIAL ALGORITHM (Advanced Reward)

**Best for variable project sizes!**

```typescript
// Exponential decay for speed
const speedBonus =
  completionTime > 0 ? Math.round(20 * Math.exp(-completionTime / 300)) : 20;
// 0 sec → +20
// 300 sec → +7.4
// 600 sec → +2.7

// Logistic function for commits
const commitBonus = Math.round(100 / (1 + commitCount * 0.1));
// 0 commits → +100
// 10 commits → +50
// 100 commits → +9

// Better quality reward
const qualityBonus =
  totalBugsDetected > 0
    ? Math.round((totalBugsFixed / totalBugsDetected) * 50)
    : 0;

const finalScore = baseScore + speedBonus + commitBonus + qualityBonus;
```

**Formula:** `100 + exp(-t/300) × 20 + 100/(1+c×0.1) + (f/d) × 50`

**Characteristics:**

- ✅ Scales with effort
- ✅ Non-linear rewards
- ✅ Scientific approach
- ❌ More complex
- ❌ Less intuitive

**Max Score:** 200+ (unlimited potential)
**Min Score:** 100

---

## 📊 Scoring Comparison Examples

### Scenario: Small Fast Project

```
Bugs: 5 | Fixed: 5 | Time: 120s | Commits: 8

CURRENT:      100 + 10 - 0 + 5 = 115
PURE BONUS:   100 + 15 + 22 + 20 = 157
EXPONENTIAL:  100 + 20 + 91 + 50 = 261
```

### Scenario: Medium Normal Project

```
Bugs: 15 | Fixed: 12 | Time: 300s | Commits: 22

CURRENT:      100 + 10 - 4 + 4 = 110
PURE BONUS:   100 + 10 + 8 + 16 = 134
EXPONENTIAL:  100 + 7 + 47 + 40 = 194
```

### Scenario: Large Complex Project

```
Bugs: 50 | Fixed: 40 | Time: 900s | Commits: 45

CURRENT:      100 + 0 - 50 + 4 = 54 😭
PURE BONUS:   100 + 0 + 0 + 16 = 116 ✓
EXPONENTIAL:  100 + 1 + 18 + 40 = 159 🌟
```

---

## 🔧 How to Switch Algorithms

### Option A: Update the Component Directly

Edit `client/src/components/ScoreBreakdownPanel.tsx`:

**Step 1:** Find the scoring section (lines 20-30)

**Step 2:** Replace with your chosen algorithm

**Example - Switching to Pure Bonus:**

```diff
- const speedBonus = completionTime > 0 && completionTime < 300 ? 10 : 0;
- const commitPenalty = Math.max(0, (commitCount - 20) * 2);
- const qualityBonus = totalBugsDetected > 0
-   ? Math.round((totalBugsFixed / totalBugsDetected) * 5)
-   : 0;
-
- const finalScore = baseScore + speedBonus - commitPenalty + qualityBonus;

+ const speedBonus = completionTime > 0 && completionTime < 180 ? 15 :
+                    completionTime < 300 ? 10 :
+                    completionTime < 600 ? 5 : 0;
+ const commitBonus = Math.max(0, 30 - commitCount);
+ const qualityBonus = totalBugsDetected > 0
+   ? Math.round((totalBugsFixed / totalBugsDetected) * 20)
+   : 0;
+
+ const finalScore = baseScore + speedBonus + commitBonus + qualityBonus;
```

**Step 3:** Update scoreBreakdown array (line 32)

Also update this part:

```typescript
const scoreBreakdown = [
  { label: "Base Score", value: baseScore, color: "bg-blue-500" },
  ...(speedBonus > 0
    ? [{ label: "Speed Bonus", value: speedBonus, color: "bg-green-500" }]
    : []),
  ...(commitBonus > 0
    ? [{ label: "Commit Bonus", value: commitBonus, color: "bg-purple-500" }]
    : []), // Changed!
  ...(qualityBonus > 0
    ? [{ label: "Quality Bonus", value: qualityBonus, color: "bg-purple-500" }]
    : []),
];
```

---

### Option B: Create Separate Utility Functions

Create `client/src/lib/scoring.ts`:

```typescript
// Scoring algorithms as separate functions

export function calculateScoreCurrent(
  baseScore: number,
  completionTime: number,
  commitCount: number,
  totalBugsDetected: number,
  totalBugsFixed: number,
) {
  const speedBonus = completionTime > 0 && completionTime < 300 ? 10 : 0;
  const commitPenalty = Math.max(0, (commitCount - 20) * 2);
  const qualityBonus =
    totalBugsDetected > 0
      ? Math.round((totalBugsFixed / totalBugsDetected) * 5)
      : 0;

  return {
    finalScore: baseScore + speedBonus - commitPenalty + qualityBonus,
    components: { baseScore, speedBonus, commitPenalty, qualityBonus },
  };
}

export function calculateScorePureBonus(
  baseScore: number,
  completionTime: number,
  commitCount: number,
  totalBugsDetected: number,
  totalBugsFixed: number,
) {
  const speedBonus =
    completionTime > 0 && completionTime < 180
      ? 15
      : completionTime < 300
        ? 10
        : completionTime < 600
          ? 5
          : 0;

  const commitBonus = Math.max(0, 30 - commitCount);

  const qualityBonus =
    totalBugsDetected > 0
      ? Math.round((totalBugsFixed / totalBugsDetected) * 20)
      : 0;

  return {
    finalScore: baseScore + speedBonus + commitBonus + qualityBonus,
    components: { baseScore, speedBonus, commitBonus, qualityBonus },
  };
}

export function calculateScoreExponential(
  baseScore: number,
  completionTime: number,
  commitCount: number,
  totalBugsDetected: number,
  totalBugsFixed: number,
) {
  const speedBonus =
    completionTime > 0 ? Math.round(20 * Math.exp(-completionTime / 300)) : 20;

  const commitBonus = Math.round(100 / (1 + commitCount * 0.1));

  const qualityBonus =
    totalBugsDetected > 0
      ? Math.round((totalBugsFixed / totalBugsDetected) * 50)
      : 0;

  return {
    finalScore: baseScore + speedBonus + commitBonus + qualityBonus,
    components: { baseScore, speedBonus, commitBonus, qualityBonus },
  };
}

// Type for algorithm selector
export type ScoringAlgorithm = "current" | "pureBonus" | "exponential";

export function calculateScore(
  algorithm: ScoringAlgorithm,
  baseScore: number,
  completionTime: number,
  commitCount: number,
  totalBugsDetected: number,
  totalBugsFixed: number,
): ReturnType<typeof calculateScoreCurrent> {
  switch (algorithm) {
    case "current":
      return calculateScoreCurrent(
        baseScore,
        completionTime,
        commitCount,
        totalBugsDetected,
        totalBugsFixed,
      );
    case "pureBonus":
      return calculateScorePureBonus(
        baseScore,
        completionTime,
        commitCount,
        totalBugsDetected,
        totalBugsFixed,
      );
    case "exponential":
      return calculateScoreExponential(
        baseScore,
        completionTime,
        commitCount,
        totalBugsDetected,
        totalBugsFixed,
      );
    default:
      return calculateScoreCurrent(
        baseScore,
        completionTime,
        commitCount,
        totalBugsDetected,
        totalBugsFixed,
      );
  }
}
```

Then use in component:

```typescript
import { calculateScore } from "@/lib/scoring";

// In component
const { finalScore, components } = calculateScore(
  "pureBonus", // or 'current' or 'exponential'
  100,
  completionTime,
  commitCount,
  totalBugsDetected,
  totalBugsFixed,
);
```

---

## 🎯 Recommendation for Your Hackathon

### Choose Pure Bonus Algorithm because:

1. **Fairness:** Doesn't punish hard workers with massive penalties
2. **Motivation:** Team morale stays high regardless of result
3. **Scalability:** Works for 5-minute to 2-hour projects
4. **Quality Focus:** Heavily rewards actual bug fixes
5. **Simplicity:** Still easy to understand

### Implementation Effort:

- ⏱️ **15 minutes** to update component
- ⏱️ **5 minutes** to test
- ⏱️ **Total: 20 minutes**

### Changes Required:

- ✏️ 1 file: `ScoreBreakdownPanel.tsx`
- 📝 ~8 lines to modify
- 🚀 0 database changes needed

---

## 🚀 Decision Menu

Pick one and I'll implement it for you right now:

```
[A] Keep CURRENT (penalty-based) ← Default now
[B] Switch to PURE BONUS (reward-based) ← Recommended ⭐
[C] Switch to EXPONENTIAL (adaptive scaling) ← Advanced
[D] Add ALL THREE with selector ← Let users choose
```

Just let me know and I'll make the change immediately!
