# Phase 11.1: Outcome-Aware Calibration Implementation

## Overview
Implemented learning system that tracks human plan selections and adjusts recommendation weighting without changing execution authority or silencing agent voices.

**Design Principle**: "A council that learns which voices the human trusts—without silencing any voice"

## Key Invariants Preserved
- ✅ HALT enforcement: All execution awaits human approval via `/internal/resume`
- ✅ No authority escalation: Preferences only affect *recommendation* weights, never override approval
- ✅ All voices surfaced: Minority agent perspectives always shown in meta-comparison
- ✅ Full auditability: All preferences logged to observer with decay/boost breakdown
- ✅ Human override: User can select any plan regardless of preference weights

## Implementation Details

### 1. Global State Tracking (Lines 50-51, 47-97)
```python
# Global preference weights—default 1.0 (neutral)
AGENT_PREFERENCE_WEIGHTS = {"A": 1.0, "B": 1.0, "C": 1.0}

# Track which agent produced which plan during delegation
LAST_DELEGATED_AGENTS = {}
```

### 2. Preference Learning Function (Lines 60-97)
```python
def update_agent_preference(selected_agent_id, policy):
    """
    Learn from human plan selection.
    - Decays all weights (prevents lock-in)
    - Boosts selected agent (learning signal)
    - Clips to min/max bounds (safety)
    - Emits preference_learning artifact (auditability)
    """
```

**Mechanism**:
1. Apply decay_rate (0.95): All preferences move toward neutral (1.0)
2. Apply learning_rate (0.15): Boost selected agent by 0.15
3. Clip to bounds: min_weight=0.5, max_weight=1.5 (prevents extremes)
4. Emit `preference_learning` artifact with before/after weights

**Example**:
```
Initial: A=1.0, B=1.2, C=0.8 (B preferred historically)
Human selects Agent C's plan

Decay: A=0.95, B=1.14, C=0.8 * 0.95 = 0.76
Boost C: C = 0.76 + 0.15 = 0.91
Result: A=0.95, B=1.14, C=0.91 (still respects B's history, but elevates C)
```

### 3. Selection Tracking at Resume (Lines 1644-1668)
When user resumes with `approve_plan_id`:
1. Look up plan_id in LAST_DELEGATED_AGENTS mapping
2. Extract which agent (A, B, or C) produced that plan
3. Call `update_agent_preference()` to record learning signal
4. Observable via `preference_learning` artifact emission

```json
// Emitted to observer
{
  "type": "preference_learning",
  "timestamp": 1234567890.5,
  "event": {
    "selected_agent_id": "C",
    "selected_plan_id": "p_003",
    "weights_before": {"A": 0.95, "B": 1.14, "C": 0.76},
    "weights_after": {"A": 0.95, "B": 1.14, "C": 0.91},
    "decay_applied": true,
    "boost_applied": 0.15
  }
}
```

### 4. Modified negotiate_plan_sets() (Lines 343-465)
Enhanced meta-negotiation to use learned preferences:

**Changes**:
1. Extract `learning_config` from policy
2. Include `preference_weight` in agent summaries (if learning enabled)
3. Inject preference context into LLM prompt
4. Attach weights + note to returned artifact
5. Emit enhanced `meta_plan_comparison` artifact

**LLM Prompt Addition** (only if learning enabled):
```
AGENT PREFERENCE WEIGHTS (from human selection history):
  Agent A: 0.95
  Agent B: 1.14
  Agent C: 0.91

These weights reflect which agent framings humans have selected historically.
Higher weight = human has previously preferred this agent's approach.
Use these weights to bias your recommendation, but continue to surface all perspectives.
```

**Artifact Enhancement**:
```json
{
  "type": "meta_plan_comparison",
  "summary": "...",
  "agent_preference_weights": {"A": 0.95, "B": 1.14, "C": 0.91},
  "preference_note": "Higher weight = human has historically preferred this agent's framing. All perspectives remain surfaced.",
  "meta_recommendation": "..."
}
```

### 5. Policy Configuration (ct-policy.json)
```json
{
  "learning_config": {
    "enabled": false,
    "decay_rate": 0.95,
    "learning_rate": 0.15,
    "min_weight": 0.5,
    "max_weight": 1.5
  }
}
```

**Default: `enabled: false`**—learning is opt-in. To enable:
```bash
# Modify ct-policy.json: "enabled": true
# Then restart orchestrator
```

## Observable Behavior

### With Learning Enabled:
1. **First delegation** (no history):
   - All agents weighted equally (1.0)
   - Meta-negotiation treats all voices equally
   - Plan shown with no bias

2. **After human selects Agent B's plan**:
   - Observer receives `preference_learning` artifact
   - AGENT_PREFERENCE_WEIGHTS updated: B → 1.15 (boost applied)
   - All others decay: A → 0.95, C → 0.95

3. **Next delegation**:
   - Meta-negotiation prompt includes preference context
   - LLM knows B's framing is historically favored
   - Recommendation may emphasize B's perspective
   - BUT all agent contributions still shown separately

4. **Over time**:
   - Weights oscillate (decay vs boost balance each other)
   - Lock-in prevented by decay (asymptotic to 1.0 if unused)
   - Human can override at any time

### With Learning Disabled (default):
- No preference tracking
- `preference_weight` field absent from negotiation
- Meta-negotiation prompt has no preference context
- All agents weighted equally (1.0)
- Behavior identical to Phase 11.0

## Authority Boundary (Hardened)

**✅ What Learning CAN do**:
- Recommend which agent's plan to read first (biased ordering)
- Provide context about historical preferences
- Suggest tradeoffs that align with past choices
- Increase confidence in decisions aligned with learning signal

**❌ What Learning CANNOT do**:
- Override pruning decisions (still enforced)
- Change HALT enforcement (still mandatory)
- Merge plans without human approval
- Silence dissenting agent voices
- Execute without human resume signal
- Change confidence thresholds (still in policy)

## Testing Verification

**Syntax Checks**:
- ✅ orchestrator.py: Valid Python syntax
- ✅ policy.json: Valid JSON structure

**Code Path Verification**:
1. `update_agent_preference()` called only at resume with valid agent_id
2. `negotiate_plan_sets()` uses learning_config from policy
3. Preference weights only affect recommendation bias, not execution gate
4. All artifacts emit via emit_event() for observer logging

## Integration with Existing Phases

**Phase 10**: Multi-plan negotiation
- ✅ Learning inactive by default, no impact

**Phase 10.1**: Policy-driven pruning
- ✅ Pruning still enforced, not affected by preferences
- ✅ min_plan_confidence still required

**Phase 10.2**: Confidence ranking
- ✅ Ranking scores unchanged
- ✅ Preferences applied after ranking

**Phase 11.0**: Delegated sub-agents
- ✅ Three agents still spawn independently
- ✅ Preferences used only for meta-recommendation, not plan generation

## Future Extensions (Not Implemented)

- Plan-specific learning (track which plan type humans prefer, not just agent framing)
- Temporal preferences (decay based on time, not iteration)
- Confidence calibration per agent (Agent A more accurate in certain domains)
- User-explicit override (human can reset preferences or set targets)

## Commits

```
Phase 11.1: Outcome-Aware Calibration
- Added AGENT_PREFERENCE_WEIGHTS global state
- Implemented update_agent_preference() with decay/boost
- Added LAST_DELEGATED_AGENTS tracking for agent-to-plan mapping
- Modified negotiate_plan_sets() to inject preference context
- Extended ct-policy.json with learning_config
- All changes preserve HALT and approval semantics
```
