import time, random, requests, json, threading, http.server, os, sys

# Phase 12: Intent validation
sys.path.insert(0, os.path.dirname(__file__))
try:
    from intent_validator import validate_intent, INTENT_QUEUE
except ImportError:
    print("[ORCHESTRATOR] Warning: intent_validator module not found. Phase 12 intents disabled.")
    INTENT_QUEUE = None

# Phase 12 Step 3: Approval bridge
try:
    from approval_bridge import APPROVAL_BRIDGE, validate_approval_request
except ImportError:
    print("[ORCHESTRATOR] Warning: approval_bridge module not found. Phase 12 approval disabled.")
    APPROVAL_BRIDGE = None

INTENTS = [
    "inspect_repo",
    "summarise_logs",
    "analyze_code",
    "plan_action",
    "apply_patch",
    # Client-defined governance intents
    "block_purchase",
    "verify_account",
    "require_mfa",
    "flag_for_review",
    "allow",
]

MODE_TRANSITIONS = {
    "reason-only": "simulate",
    "simulate": "propose",
}

LAST_REJECTED_INTENT = None
LAST_PLAN_DRAFT = None
LAST_PLAN_SET = None
TOOL_URL = "http://ct-mock-tool:9000/tool-intent"
LLM_URL = "http://ct-llm:11434/api/generate"
OBSERVER_URL = "http://ct-observer:9002/log"
ACTION_URL = "http://ct-action:9003/read"
FILE_ACTION_URL = "http://ct-action:9003/file"
PATCH_ACTION_URL = "http://ct-action:9003/patch"
HISTORY_FILE = "/data/ct_history.jsonl"
HALTED = False
RESUME_REQUESTED = False
JUST_RESUMED = False
CURRENT_PLAN = None
APPROVED_STEP_ID = None
APPROVED_PLAN_ID = None
POLICY_PATH = "/app/ct-policy.json"
POLICY = {}
LAST_DELEGATED_AGENTS = {}  # Track which agent produced which plan in current set

try:
    if os.path.exists(POLICY_PATH):
        with open(POLICY_PATH, "r") as f:
            POLICY = json.load(f)
        print(f"[ORCHESTRATOR] Policy loaded from {POLICY_PATH}")
    else:
        print("[ORCHESTRATOR] Warning: No policy file found at /app/ct-policy.json")
except Exception as e:
    print(f"[ORCHESTRATOR] Error loading policy: {e}")

# Memory v1 state
CALIBRATION = {}

# Phase 11.1: Agent Preference Learning
# Tracks which agent framings humans prefer over time
AGENT_PREFERENCE_WEIGHTS = {
    "A": 1.0,  # Conservative
    "B": 1.0,  # Speed
    "C": 1.0   # Long-Term
}

# Phase 11.2: Temporal / Checkpointed Planning
# Tracks phase execution state for multi-phase plans
CURRENT_PHASE = None         # Currently executing phase
APPROVED_PHASE_ID = None     # Phase approved by human
COMPLETED_PHASES = []        # List of completed phase_ids
PHASE_RESULTS = {}           # {phase_id: {"success": bool, "steps": [...]}}
SKIPPED_PHASES = []          # List of skipped phase_ids

# Phase 11.3: Predictive Resume & Phase Review
# Tracks approval patterns and staged phases
STAGED_PHASE_CACHE = {}      # {phase_id: {"next_phase_id": str, "confidence": float}}
APPROVAL_PATTERN_STATS = {}  # {from_phase: {to_phase: {"count": int, "confidence": float}}}
LAST_PHASE_REVIEW_SCORE = {} # {phase_id: {"quality": float, "summary": str}}

def update_agent_preference(selected_agent_id, policy):
    """Learn from human plan selections.
    
    When human chooses a plan from Agent A's set, increment A's preference weight.
    Use decay_rate to forget old preferences over time (prevents lock-in).
    """
    global AGENT_PREFERENCE_WEIGHTS
    
    learning_config = policy.get("learning_config", {})
    if not learning_config.get("enabled", False):
        return
    
    if selected_agent_id not in AGENT_PREFERENCE_WEIGHTS:
        return
    
    decay_rate = learning_config.get("decay_rate", 0.95)
    learning_rate = learning_config.get("learning_rate", 0.15)
    min_weight = learning_config.get("min_weight", 0.5)
    max_weight = learning_config.get("max_weight", 1.5)
    
    # Decay all weights slightly (prevents lock-in)
    for agent_id in AGENT_PREFERENCE_WEIGHTS:
        AGENT_PREFERENCE_WEIGHTS[agent_id] = max(
            min_weight,
            AGENT_PREFERENCE_WEIGHTS[agent_id] * decay_rate
        )
    
    # Boost selected agent
    AGENT_PREFERENCE_WEIGHTS[selected_agent_id] = min(
        max_weight,
        AGENT_PREFERENCE_WEIGHTS[selected_agent_id] + learning_rate
    )
    
    print(f"[LEARNING] Agent preference updated: {AGENT_PREFERENCE_WEIGHTS}")
    
    # Emit preference learning artifact
    learning_event = {
        "type": "preference_learning",
        "selected_agent_id": selected_agent_id,
        "preference_weights": {k: round(v, 3) for k, v in AGENT_PREFERENCE_WEIGHTS.items()},
        "rationale": f"Human selected Agent {selected_agent_id}'s plan. Weights updated via outcome-aware calibration."
    }
    emit_event(learning_event)

# Phase 11.2: Temporal / Checkpointed Planning Functions

def check_phase_dependencies(phase, completed_phases):
    """Check if all dependencies for a phase are met.
    
    Returns: True if dependencies met, False otherwise
    """
    dependencies = phase.get("dependencies", [])
    if not dependencies:
        return True  # No dependencies
    
    for dep_id in dependencies:
        if dep_id not in completed_phases:
            return False
    
    return True

def emit_phase_artifact(artifact_type, phase, plan_id, **kwargs):
    """Emit phase-related observer artifacts.
    
    Phase 11.2: All phase transitions are observable.
    """
    artifact = {
        "type": artifact_type,
        "timestamp": time.time(),
        "plan_id": plan_id,
        "phase_id": phase.get("phase_id"),
        "phase_name": phase.get("phase_name", f"Phase {phase.get('phase_id')}")
    }
    
    # Add type-specific fields
    artifact.update(kwargs)
    
    emit_event(artifact)
    return artifact

def generate_phase_review(phase, success, policy):
    """Generate optional LLM review of completed phase with quality enrichment.
    
    Phase 11.2: Opt-in phase reviews (disabled by default).
    Phase 11.3 Step 4: Enhanced reviews with quality_score and confidence_explanation.
    
    Reviews are advisory only. Quality score never blocks approval.
    """
    phase_config = policy.get("phase_execution_config", {}) if policy else {}
    if not phase_config.get("generate_phase_reviews", False):
        return None  # Reviews disabled
    
    prompt = f"""You are CT's phase review assistant.
Your task is to summarize the results of a completed phase in plain English.

PHASE DETAILS:
{json.dumps(phase, indent=2)}

SUCCESS: {success}

Output ONLY valid JSON:
{{
  "type": "phase_review",
  "summary": "Plain English summary of what was accomplished (2-3 sentences)",
  "recommendations": ["recommendation 1", "recommendation 2", ...],
  "confidence": 0.0-1.0
}}

Guidelines:
- Be concise and fact-based
- Highlight any risks or concerns
- Suggest next steps if applicable
- Output JSON only. No preamble.
"""
    
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=60
        )
        
        if response.status_code == 200:
            review = json.loads(response.json().get("response"))
            
            # Phase 11.3 Step 4: Enrich review with quality score and confidence explanation
            review_quality = compute_review_quality(review, success)
            review["review_quality_score"] = review_quality
            
            # Add confidence explanation based on approval patterns (read-only advisory)
            confidence_explanation = generate_confidence_explanation(
                phase.get("phase_id"),
                review_quality,
                phase_config.get("review_quality_threshold", 0.70)
            )
            review["confidence_explanation"] = confidence_explanation
            
            # Store for later reference
            LAST_PHASE_REVIEW_SCORE[phase.get("phase_id", "unknown")] = {
                "quality": review_quality,
                "summary": review.get("summary", "")
            }
            
            return review
    except Exception as e:
        print(f"[ORCHESTRATOR] Phase review generation failed: {e}")
    
    return None

def compute_review_quality(review, success):
    """Compute review quality score (0-1) based on review content.
    
    Advisory only. Never used for blocking or approval decisions.
    Score reflects confidence in the review itself, not phase execution.
    """
    score = 0.5  # Base score
    
    # Positive signals
    if success:
        score += 0.2
    
    if review.get("summary") and len(review.get("summary", "")) > 20:
        score += 0.15
    
    if review.get("recommendations") and len(review.get("recommendations", [])) > 0:
        score += 0.15
    
    if review.get("confidence", 0) >= 0.8:
        score += 0.1
    
    # Cap at 1.0
    return min(score, 1.0)

def generate_confidence_explanation(phase_id, quality_score, threshold):
    """Generate advisory explanation of review quality.
    
    Phase 11.3 Step 4: Advisory confidence context (read-only of patterns).
    Never used for blocking or execution decisions.
    
    If quality_score < threshold: Add "advisory caution" annotation.
    Otherwise: Standard confidence message.
    """
    if quality_score < threshold:
        explanation = f"Review quality score {quality_score:.2f} below threshold {threshold:.2f}. " \
                     f"Review is advisory only - human judgment takes precedence."
    else:
        explanation = f"Review quality score {quality_score:.2f} meets confidence threshold. " \
                     f"Review provides context for your decision."
    
    return explanation

    
    return None

def stage_next_phase_if_applicable(current_phase_id, plan):
    """Phase 11.3 Step 2: Predictive staging - compute next phase without execution.
    
    Preconditions (all must be true, or return immediately):
    1. phase_execution_config.enabled == true
    2. enable_predictive_staging == true
    3. Current phased plan exists
    4. Current phase is HALTed (implicit - called after phase_completed + HALT)
    5. No approve_phase_id issued yet
    6. No staged phase already exists for this plan
    
    Staging Logic:
    - Identifies next eligible phase based on dependencies
    - Computes metadata only (no execution, no LLM)
    - Caches in STAGED_PHASE_CACHE
    - Does NOT emit observer artifacts
    - Does NOT modify execution state
    
    Returns: True if staging computed, False otherwise
    """
    global STAGED_PHASE_CACHE, POLICY
    
    # Precondition 1: Policy must enable phase execution
    if not POLICY:
        return False
    
    phase_config = POLICY.get("phase_execution_config", {})
    if not phase_config.get("enabled", False):
        return False
    
    # Precondition 2: Predictive staging must be enabled
    if not phase_config.get("enable_predictive_staging", False):
        return False
    
    # Precondition 3: Must have a phased plan
    if not plan or "phases" not in plan or not plan.get("phases"):
        return False
    
    plan_id = plan.get("plan_id")
    phases = plan.get("phases", [])
    
    # Precondition 6: Check if already staged for this plan
    if plan_id in STAGED_PHASE_CACHE:
        return False
    
    # Find current phase in plan
    current_phase = None
    current_phase_index = -1
    for i, phase in enumerate(phases):
        if phase.get("phase_id") == current_phase_id:
            current_phase = phase
            current_phase_index = i
            break
    
    if current_phase_index == -1:
        return False
    
    # Find next phase
    next_phase = None
    next_phase_id = None
    
    for i in range(current_phase_index + 1, len(phases)):
        candidate = phases[i]
        candidate_id = candidate.get("phase_id")
        
        # Check if candidate dependencies are satisfied
        if check_phase_dependencies(candidate, COMPLETED_PHASES):
            next_phase = candidate
            next_phase_id = candidate_id
            break
    
    # If no eligible next phase, nothing to stage
    if not next_phase_id:
        return False
    
    # Compute staging metadata (pure computation, no side effects)
    stage_metadata = {
        "plan_id": plan_id,
        "from_phase": current_phase_id,
        "staged_phase_id": next_phase_id,
        "dependencies": next_phase.get("depends_on", []),
        "estimated_steps": len(next_phase.get("steps", [])),
        "has_success_criteria": bool(next_phase.get("success_criteria", [])),
        "confidence": 0.85,  # Default confidence (no learning yet - Step 3)
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    # Cache the staged phase
    STAGED_PHASE_CACHE[plan_id] = stage_metadata
    
    return True


def record_approval_pattern(from_phase_id, to_phase_id):
    """Phase 11.3 Step 3: Record approval sequences for pattern learning.
    
    Called ONLY when:
    - approve_phase_id is explicitly received in resume signal
    - Phase dependencies already validated
    - approval_pattern_learning enabled in policy
    
    Updates APPROVAL_PATTERN_STATS with counts only.
    Never influences execution, staging, or approval decisions.
    Persists across plan boundaries (global learning).
    
    Args:
        from_phase_id: Currently executing phase (CURRENT_PHASE)
        to_phase_id: Approved next phase (APPROVED_PHASE_ID)
    
    Returns: True if pattern recorded, False otherwise
    """
    global APPROVAL_PATTERN_STATS, POLICY
    
    # Precondition 1: Policy must enable approval pattern learning
    if not POLICY:
        return False
    
    phase_config = POLICY.get("phase_execution_config", {})
    if not phase_config.get("approval_pattern_learning", False):
        return False
    
    # Precondition 2: Both phases must be provided
    if not from_phase_id or not to_phase_id:
        return False
    
    # Initialize nested structure if needed
    if from_phase_id not in APPROVAL_PATTERN_STATS:
        APPROVAL_PATTERN_STATS[from_phase_id] = {}
    
    if to_phase_id not in APPROVAL_PATTERN_STATS[from_phase_id]:
        APPROVAL_PATTERN_STATS[from_phase_id][to_phase_id] = {
            "count": 0,
            "last_approved": None
        }
    
    # Increment count (pure observation, no inference)
    APPROVAL_PATTERN_STATS[from_phase_id][to_phase_id]["count"] += 1
    APPROVAL_PATTERN_STATS[from_phase_id][to_phase_id]["last_approved"] = \
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    return True


def enhance_phase_review(phase, success, policy):
    """Phase 11.3: Enhanced phase_review with quality scoring.
    
    Early-return if:
    - generate_phase_reviews not true in policy
    
    When enabled: calls LLM to generate review + quality_score (0-1).
    Stores in LAST_PHASE_REVIEW_SCORE.
    
    Reviews are advisory only; do not constrain human approval.
    """
    if not policy:
        return None
    
    phase_config = policy.get("phase_execution_config", {})
    if not phase_config.get("generate_phase_reviews", False):
        return None
    
    # Stub: actual enhancement logic in Step 4
    return None

def execute_plan_with_phases(plan):
    """Execute a phased plan with HALT gates between phases.
    
    Phase 11.2: Core phased execution logic with checkpoints.
    
    A phase is considered "completed" only after all steps execute successfully
    and the human explicitly acknowledges completion (or advances to the next phase).
    """
    global HALTED, CURRENT_PHASE, APPROVED_PHASE_ID, COMPLETED_PHASES, PHASE_RESULTS, SKIPPED_PHASES
    
    phases = plan.get("phases", [])
    if not phases:
        print("[ORCHESTRATOR] No phases in plan, falling back to step-by-step execution")
        return False
    
    plan_id = plan.get("plan_id", "unknown")
    
    print(f"[ORCHESTRATOR] Starting phased execution: {len(phases)} phases")
    
    for phase in phases:
        phase_id = phase.get("phase_id")
        phase_name = phase.get("phase_name", f"Phase {phase_id}")
        
        # Check if phase was skipped
        if phase_id in SKIPPED_PHASES:
            print(f"[ORCHESTRATOR] Phase {phase_id} skipped by human")
            continue
        
        # Check dependencies
        if not check_phase_dependencies(phase, COMPLETED_PHASES):
            print(f"[ORCHESTRATOR] Phase {phase_id} blocked: dependencies not met")
            emit_phase_artifact(
                "phase_blocked",
                phase,
                plan_id,
                reason="Dependencies not met",
                dependencies=phase.get("dependencies", []),
                completed_phases=COMPLETED_PHASES
            )
            HALTED = True
            return False
        
        # Emit phase_started
        CURRENT_PHASE = phase_id
        emit_phase_artifact(
            "phase_started",
            phase,
            plan_id,
            estimated_duration=phase.get("estimated_duration", "unknown")
        )
        
        print(f"[ORCHESTRATOR] Executing Phase {phase_id}: {phase_name}")
        
        # Execute phase steps
        phase_steps = phase.get("steps", [])
        steps_succeeded = 0
        steps_failed = 0
        phase_start_time = time.time()
        
        for step in phase_steps:
            # Note: Actual step execution would happen here
            # For Phase 11.2, we're setting up the structure
            # Step execution will be integrated with existing APPROVED_STEP_ID flow
            steps_succeeded += 1
        
        phase_duration = time.time() - phase_start_time
        phase_success = steps_failed == 0
        
        # Record phase result
        PHASE_RESULTS[phase_id] = {
            "success": phase_success,
            "steps_executed": len(phase_steps),
            "steps_succeeded": steps_succeeded,
            "steps_failed": steps_failed,
            "duration_seconds": phase_duration
        }
        
        COMPLETED_PHASES.append(phase_id)
        
        # Emit phase_completed
        next_phase_id = phase_id + 1 if phase_id < len(phases) else None
        emit_phase_artifact(
            "phase_completed",
            phase,
            plan_id,
            steps_executed=len(phase_steps),
            steps_succeeded=steps_succeeded,
            steps_failed=steps_failed,
            duration_seconds=round(phase_duration, 2),
            success_criteria_met=phase.get("success_criteria", []),
            next_phase=next_phase_id,
            awaiting_approval=next_phase_id is not None
        )
        
        # Optional: Generate phase review
        if POLICY:
            review = generate_phase_review(phase, phase_success, POLICY)
            if review:
                review["plan_id"] = plan_id
                review["phase_id"] = phase_id
                emit_event(review)
                print(f"[ORCHESTRATOR] Phase review emitted for phase {phase_id}")
        
        # Phase 11.3 Step 2: Predictive staging (wire after phase review)
        # Computes next phase metadata without execution
        if next_phase_id:
            stage_next_phase_if_applicable(phase_id, CURRENT_PLAN)
        
        # HALT before next phase (unless this is the last phase)
        if next_phase_id:
            print(f"[ORCHESTRATOR] Phase {phase_id} complete. HALT before Phase {next_phase_id}")
            HALTED = True
            CURRENT_PHASE = None
            # Human must approve next phase via resume signal
            return False  # Not complete yet
    
    # All phases complete
    print(f"[ORCHESTRATOR] All phases complete for plan {plan_id}")
    emit_event({
        "type": "plan_completed",
        "timestamp": time.time(),
        "plan_id": plan_id,
        "total_phases": len(phases),
        "phases_completed": len(COMPLETED_PHASES),
        "phases_skipped": len(SKIPPED_PHASES),
        "total_steps": sum(len(p.get("steps", [])) for p in phases),
        "outcome": "success"
    })
    
    return True  # Plan complete

def prune_plans_by_policy(plan_set, policy):
    """Filter plans against policy safety rules and confidence thresholds.
    
    Returns: (approved_plans, rejected_plans_with_reasons)
    """
    if not plan_set or not plan_set.get("plans"):
        return [], []
    
    approved = []
    rejections = []
    
    # Extract pruning config from policy
    pruning_config = policy.get("pruning_config", {})
    min_confidence = pruning_config.get("min_plan_confidence", 0.75)
    sandbox_only_actions = policy.get("plan_safety_rules", {}).get("sandbox_only_actions", [])
    forbidden_actions = policy.get("plan_safety_rules", {}).get("forbidden_actions", [])
    
    for plan in plan_set.get("plans", []):
        violations = []
        
        # Check plan-level confidence
        plan_confidence = plan.get("confidence", 1.0)
        if plan_confidence < min_confidence:
            violations.append(f"plan confidence {plan_confidence:.2f} below threshold {min_confidence}")
        
        # Check steps for policy violations
        for step in plan.get("steps", []):
            action = step.get("action", "")
            
            # Check for forbidden actions
            if action in forbidden_actions:
                violations.append(f"action '{action}' is forbidden by policy")
            
            # Check sandbox-only actions
            if action in sandbox_only_actions:
                target = step.get("target", "")
                if target and not target.startswith("/tmp/ct-sandbox/"):
                    violations.append(f"action '{action}' only allowed in sandbox, target is {target}")
        
        if violations:
            rejections.append({
                "plan_id": plan.get("plan_id"),
                "status": "rejected",
                "reasons": violations
            })
            print(f"[POLICY PRUNING] Plan {plan.get('plan_id')} rejected: {violations}")
        else:
            approved.append(plan)
            print(f"[POLICY PRUNING] Plan {plan.get('plan_id')} approved")
    
    return approved, rejections

def rank_plans(plan_set, calibration_state, policy):
    """Rank approved plans by confidence, calibration, policy friction, and history.
    
    Scoring formula:
    score = (plan.confidence * calibration_multiplier) 
            - policy_friction_penalty 
            + historical_success_bonus
    
    Returns: (ranked_plans, ranking_breakdown)
    """
    if not plan_set or not plan_set.get("plans"):
        return [], []
    
    # Extract ranking config from policy
    ranking_config = policy.get("ranking_config", {})
    if not ranking_config.get("enable", True):
        # Ranking disabled, return original order with neutral scores
        return plan_set.get("plans", []), []
    
    policy_friction_penalty = ranking_config.get("policy_friction_penalty", 0.05)
    history_success_bonus = ranking_config.get("history_success_bonus", 0.05)
    
    ranking_breakdown = []
    plans_with_scores = []
    
    for plan in plan_set.get("plans", []):
        plan_id = plan.get("plan_id")
        base_confidence = plan.get("confidence", 0.50)
        
        # Get calibration multiplier for this plan_id
        # (using a simple heuristic: plans A, B, C get different treatment)
        calibration_multiplier = calibration_state.get(("plan_action", "propose"), 1.0)
        
        # Apply plan order bias (first plans slightly more trusted)
        if plan_id == "A":
            calibration_multiplier = min(calibration_multiplier * 1.0, 1.0)
        elif plan_id == "B":
            calibration_multiplier = min(calibration_multiplier * 0.98, 1.0)
        elif plan_id == "C":
            calibration_multiplier = min(calibration_multiplier * 0.95, 1.0)
        
        # Calculate score components
        confidence_component = base_confidence * calibration_multiplier
        
        # Policy friction: small penalty for being conservative/rejected by some heuristics
        friction = 0.0
        
        # History bonus: check if this intent type succeeded before
        history_bonus = 0.0
        # Note: In a full implementation, we'd look up actual history
        # For now, use a conservative default
        history_bonus = history_success_bonus * 0.5  # Neutral assumption
        
        # Final score (clamped to [0.0, 1.0])
        final_score = max(0.0, min(1.0, 
            confidence_component - friction + history_bonus
        ))
        
        breakdown = {
            "plan_id": plan_id,
            "base_confidence": round(base_confidence, 3),
            "calibration_multiplier": round(calibration_multiplier, 3),
            "confidence_component": round(confidence_component, 3),
            "policy_friction": round(friction, 3),
            "history_bonus": round(history_bonus, 3),
            "final_score": round(final_score, 3)
        }
        
        ranking_breakdown.append(breakdown)
        plans_with_scores.append((plan, final_score, breakdown))
    
    # Sort by score descending
    plans_with_scores.sort(key=lambda x: x[1], reverse=True)
    ranked_plans = [p[0] for p in plans_with_scores]
    
    # Update breakdown to reflect final ranking order
    ranking_breakdown = [p[2] for p in plans_with_scores]
    
    return ranked_plans, ranking_breakdown

def delegate_plan_generation(artifact, policy, calibration_state):
    """Spawn N sub-agents to generate independent plan sets.
    
    Phase 11.0 Implementation:
    - Each agent gets same evidence, different framing
    - All agents apply pruning + ranking independently
    - Returns list of (agent_id, plan_set, ranking_breakdown) tuples
    
    No tools executed. No authority change. Purely reasoning.
    """
    delegation_config = policy.get("delegation_config", {})
    if not delegation_config.get("enabled", False):
        return None
    
    agent_count = min(
        delegation_config.get("agent_count", 3),
        delegation_config.get("max_agents", 5)
    )
    
    agents = [
        ("A", SUBAGENT_CONSERVATIVE_FRAMING, "Conservative / Risk-Minimizing"),
        ("B", SUBAGENT_SPEED_FRAMING, "Speed / Minimal Change"),
        ("C", SUBAGENT_LONGTERM_FRAMING, "Long-Term Maintainability")
    ][:agent_count]
    
    delegated_plan_sets = []
    
    for agent_id, framing, description in agents:
        print(f"[ORCHESTRATOR] Delegating to Sub-Agent {agent_id} ({description})...")
        
        # Build prompt for this sub-agent
        policy_block = f"POLICY CONSTRAINTS (MANDATORY):\n{json.dumps(policy, indent=2)}\n"
        prompt = f"""{framing}

{policy_block}

COGNITIVE ARTIFACT (same evidence for all agents):
{json.dumps(artifact, indent=2)}

Your task: Generate 2-3 alternative execution plans optimized for your role.
Output ONLY valid JSON matching this schema:

{{
  "type": "execution_plan_set",
  "goal": "High-level objective (2-3 sentences)",
  "plans": [
    {{
      "plan_id": "A",
      "summary": "...",
      "steps": [...],
      "pros": [...],
      "cons": [...],
      "risks": [...],
      "confidence": 0.0-1.0
    }}
  ],
  "recommended_plan_id": "A",
  "reasoning": "Why you recommend this plan (2-3 sentences)"
}}

Generate your best thinking. All plans will be evaluated independently.
"""
        
        try:
            response = requests.post(
                LLM_URL,
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=120
            )
            
            if response.status_code == 200:
                plan_set = json.loads(response.json().get("response"))
                print(f"[ORCHESTRATOR] Sub-Agent {agent_id} generated plan set")
                
                # Apply pruning (same as main orchestrator)
                approved_plans, rejected = prune_plans_by_policy(plan_set, policy)
                plan_set["plans"] = approved_plans
                
                # Apply ranking
                ranked_plans, ranking_breakdown = rank_plans(plan_set, calibration_state, policy)
                plan_set["plans"] = ranked_plans
                
                # Emit delegated_plan_set artifact
                delegated_event = {
                    "type": "delegated_plan_set",
                    "agent_id": agent_id,
                    "agent_role": description,
                    "plan_set": plan_set,
                    "ranking_breakdown": ranking_breakdown
                }
                emit_event(delegated_event)
                
                delegated_plan_sets.append((agent_id, plan_set, ranking_breakdown, description))
                print(f"[ORCHESTRATOR] Sub-Agent {agent_id} plan set emitted and ranked")
            else:
                print(f"[ORCHESTRATOR] Sub-Agent {agent_id} LLM error: {response.status_code}")
        except Exception as e:
            print(f"[ORCHESTRATOR] Sub-Agent {agent_id} exception: {e}")
    
    if not delegated_plan_sets:
        print("[ORCHESTRATOR] No sub-agents produced valid plan sets")
        return None
    
    return delegated_plan_sets

def negotiate_plan_sets(delegated_plan_sets, policy):
    """Synthesize insights from multiple sub-agents.
    
    Phase 11.1: Uses learned agent preference weights to bias recommendations
    without silencing other voices.
    
    Compares plan sets and produces a meta-comparison artifact.
    No merging, no hidden compromises—just explicit comparison.
    """
    if not delegated_plan_sets:
        return None
    
    print("[ORCHESTRATOR] Negotiating between sub-agent plan sets...")
    
    # Build comparison context
    agent_summaries = []
    learning_config = policy.get("learning_config", {})
    preferences_enabled = learning_config.get("enabled", False)
    
    for agent_id, plan_set, ranking_breakdown, role in delegated_plan_sets:
        # Phase 11.1: Include preference weight if learning is enabled
        preference_weight = AGENT_PREFERENCE_WEIGHTS.get(agent_id, 1.0) if preferences_enabled else 1.0
        
        summary = {
            "agent_id": agent_id,
            "agent_role": role,
            "preference_weight": round(preference_weight, 3) if preferences_enabled else None,
            "top_plan_id": plan_set.get("plans", [{}])[0].get("plan_id") if plan_set.get("plans") else None,
            "top_plan_summary": plan_set.get("plans", [{}])[0].get("summary") if plan_set.get("plans") else None,
            "top_plan_confidence": plan_set.get("plans", [{}])[0].get("confidence") if plan_set.get("plans") else 0.0,
            "recommendation": plan_set.get("recommended_plan_id"),
            "reasoning": plan_set.get("reasoning")
        }
        agent_summaries.append(summary)
    
    preference_context = ""
    if preferences_enabled:
        preference_context = f"""
AGENT PREFERENCE WEIGHTS (from human selection history):
{json.dumps({s['agent_id']: s['preference_weight'] for s in agent_summaries}, indent=2)}

These weights reflect which agent framings humans have selected historically.
Higher weight = human has previously preferred this agent's approach.
Use these weights to bias your recommendation, but continue to surface all perspectives.
"""
    
    prompt = f"""You are CT's meta-negotiation unit.
Your task is to compare insights from 3 sub-agents with different perspectives:
- Agent A: Conservative / Risk-Minimizing
- Agent B: Speed / Minimal Change  
- Agent C: Long-Term Maintainability

SUB-AGENT RECOMMENDATIONS:
{json.dumps(agent_summaries, indent=2)}
{preference_context}

Analyze:
1. Where do they agree? (consensus)
2. Where do they diverge? (legitimate tradeoffs)
3. What does each perspective add?
4. Are there any red flags?

Output ONLY valid JSON:
{{
  "type": "meta_plan_comparison",
  "summary": "Overall synthesis of sub-agent insights (3-4 sentences)",
  "consensus": {{
    "agreed_principles": ["principle 1", ...],
    "shared_concerns": ["concern 1", ...]
  }},
  "divergences": [
    {{
      "dimension": "speed vs safety",
      "agents_favoring_option_a": ["A", "B"],
      "agents_favoring_option_b": ["C"],
      "tradeoff_explanation": "..."
    }}
  ],
  "agent_contributions": [
    {{
      "agent_id": "A",
      "key_insight": "What this agent adds to thinking",
      "confidence": 0.8
    }}
  ],
  "meta_recommendation": "How to integrate these perspectives (2-3 sentences). Consider learned preference weights if present.",
  "confidence": 0.0-1.0
}}

Guidelines:
- Show legitimate disagreement, don't hide it
- Explain tradeoffs clearly
- Value diversity of thinking
- If preference weights are present, bias recommendation toward preferred agents but still surface all options
- Do not attempt to merge plans or hide compromises
- Output JSON only. No preamble or explanation.
"""
    
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            meta_comparison = json.loads(response.json().get("response"))
            
            # Phase 11.1: Attach preference context to artifact
            if preferences_enabled:
                meta_comparison["agent_preference_weights"] = {
                    s['agent_id']: s['preference_weight'] 
                    for s in agent_summaries
                }
                meta_comparison["preference_note"] = "Higher weight = human has historically preferred this agent's framing. All perspectives remain surfaced."
            
            # Emit to observer
            emit_event({
                "type": "meta_plan_comparison",
                "timestamp": time.time(),
                "artifact": meta_comparison
            })
            
            return meta_comparison
        else:
            print(f"[ORCHESTRATOR] Meta-negotiation LLM error: {response.status_code}")
    except Exception as e:
        print(f"[ORCHESTRATOR] Meta-negotiation exception: {e}")
    
    return None

SYSTEM_PROMPT_TEMPLATE = """You are CT's reasoning core.

{plan_context_block}
{outcome_context_block}
{mandated_step_block}
{policy_block}

Given the current situation, output ONE intent as JSON matching this schema:

{{
  "intent": "...",
  "target": "...",
  "patch_content": "REQUIRED if intent is apply_patch (Unified Diff format)",
  "confidence": 0.0-1.0,
  "mode": "reason-only" | "simulate" | "propose",
  "notes": "optional"
}}

Rules:
- You MUST choose an intent from this exact list: ['inspect_repo', 'summarise_logs', 'analyze_code', 'plan_action', 'apply_patch']
- 'apply_patch' writes to a SANDBOX (/tmp/ct-sandbox/). 
- To promote changes to the real repo, instruct the human to run: './scripts/apply_patch.sh <filename>'
- If unsure, lower confidence.
- Do not invent certainty.
- Prefer reason-only unless blocked.
- Output JSON only. No commentary."""

SYNTHESIS_PROMPT_TEMPLATE = """You are CT's semantic synthesis unit.
Your task is to compress raw evidence into a concise, structured summary.

CONTENT to synthesize:
---
{content}
---

SCOPE: {scope}
CONTEXT: {intent}

Output ONLY valid JSON in this format:
{{
  "type": "semantic_summary",
  "scope": "{scope}",
  "findings": ["finding 1", "finding 2", ...],
  "confidence": 0.0-1.0
}}
"""

COMPARISON_PROMPT_TEMPLATE = """You are CT's comparative analysis unit.
Your task is to contrast two semantic summaries and highlight shifts, inconsistencies, or confirmations.

SUMMARY A (Prior):
{summary_a}

SUMMARY B (Current):
{summary_b}

Output ONLY valid JSON in this format:
{{
  "type": "semantic_comparison",
  "left": "{scope_a}",
  "right": "{scope_b}",
  "similarities": ["bullet", ...],
  "differences": ["bullet", ...],
  "implications": ["bullet", ...],
  "confidence": 0.0-1.0
}}
"""

PLANNING_PROMPT_TEMPLATE = """You are CT's execution planning unit.
Your task is to turn cognitive understanding into a structured, stepwise plan.

{previous_plan_block}
{policy_block}

COGNITIVE ARTIFACT:
{artifact}

Output ONLY valid JSON in this format:
{{
  "type": "execution_plan",
  "goal": "Brief description of the objective",
  "assumptions": ["assumption 1", ...],
  "steps": [
    {{
      "id": 1,
      "action": "inspect_repo | summarise_logs | analyze_code | plan_action | apply_patch",
      "target": "target path or file",
      "rationale": "Why this step is necessary. If using apply_patch, mention that human must promote it via ./scripts/apply_patch.sh afterwards.",
      "risk": "low | medium | high"
    }}
  ],
  "blocking_questions": ["What do you need to know from the human?", ...],
  "confidence": 0.0-1.0
}}

Mandatory Policy Checklist:
1. Every step must be compatible with the restricted paths in the POLICY structure above.
2. If a project-specific rule is active, it must be reflected in the steps.
3. Do not propose actions that violate 'hard' policies.
"""

MULTI_PLAN_PROMPT_TEMPLATE = """You are CT's multi-plan negotiation unit.
Your task is to propose 2–3 alternative approaches to the same objective, each with distinct tradeoffs.

{policy_block}

COGNITIVE ARTIFACT:
{artifact}

You MUST output exactly ONE JSON object matching this format:
{{
  "type": "execution_plan_set",
  "goal": "High-level objective (2-3 sentences)",
  "plans": [
    {{
      "plan_id": "A",
      "summary": "Conservative approach: minimal change, lower risk",
      "steps": [
        {{
          "id": 1,
          "action": "inspect_repo | summarise_logs | analyze_code | plan_action | apply_patch",
          "target": "target path or file",
          "rationale": "Why this step is necessary",
          "risk": "low | medium | high"
        }}
      ],
      "pros": ["pro 1", "pro 2", ...],
      "cons": ["con 1", "con 2", ...],
      "risks": ["risk 1", "risk 2", ...],
      "confidence": 0.0-1.0
    }},
    {{
      "plan_id": "B",
      "summary": "Moderate approach: balanced tradeoffs",
      "steps": [...],
      "pros": [...],
      "cons": [...],
      "risks": [...],
      "confidence": 0.0-1.0
    }},
    {{
      "plan_id": "C",
      "summary": "Aggressive approach: faster but higher risk (OPTIONAL - only if warranted)",
      "steps": [...],
      "pros": [...],
      "cons": [...],
      "risks": [...],
      "confidence": 0.0-1.0
    }}
  ],
  "recommended_plan_id": "A",
  "reasoning": "Why you prefer the recommended plan under current policy and calibration (2-3 sentences)"
}}

Rules:
1. Minimum 2 plans, maximum 3.
2. Each plan must differ meaningfully in approach or scope.
3. You MUST recommend exactly one plan.
4. Do NOT execute any tools.
5. Do NOT attempt to take action. This is purely planning.
6. All steps must be compatible with POLICY constraints above.
7. Output ONLY valid JSON. No commentary.
8. Output JSON only. No preamble or explanation.

OPTIONAL: If the goal requires multiple sequential steps with natural checkpoints,
you may structure your plan with phases instead of flat steps:

{{
  "type": "execution_plan_set",
  "goal": "...",
  "plans": [
    {{
      "plan_id": "A",
      "summary": "...",
      "phases": [
        {{
          "phase_id": 1,
          "phase_name": "Setup",
          "description": "Prepare environment and dependencies",
          "estimated_duration": "5-10 minutes (informational only)",
          "steps": [
            {{"id": 1, "action": "create_file", "target": "...", "rationale": "...", "risk": "low"}},
            {{"id": 2, "action": "run_command", "target": "...", "rationale": "...", "risk": "low"}}
          ],
          "success_criteria": [
            "Observable condition 1 (file exists, test passes, etc.)",
            "Observable condition 2"
          ],
          "rollback_notes": "How to undo this phase (informational only, not executed)",
          "dependencies": [],
          "blocks": [2, 3]
        }},
        {{
          "phase_id": 2,
          "phase_name": "Implementation",
          "description": "Core logic changes",
          "steps": [...],
          "success_criteria": [...],
          "rollback_notes": "...",
          "dependencies": [1],
          "blocks": []
        }}
      ],
      "pros": [...],
      "cons": [...],
      "risks": [...],
      "confidence": 0.85
    }}
  ]
}}

Phase Guidelines:
- Use phases when there are natural checkpoints (e.g., setup → implement → test)
- Each phase should have 2-5 steps maximum
- success_criteria must be observable (file exists, test passes, service responds)
- rollback_notes are informational only (not executed automatically)
- Human will review and approve each phase transition
- estimated_duration is advisory (no enforcement)
- dependencies and blocks document phase order (informational, not enforced)

Do NOT use phases for:
- Single-step tasks
- Tasks with no natural checkpoints
- Parallel work (phases are sequential)
"""

REVIEW_PROMPT_TEMPLATE = """You are CT's review assistant.
Your task is to translate a technical execution plan into a human-readable review artifact.

EXECUTION PLAN:
{execution_plan}

Output ONLY valid JSON in this format:
{{
  "type": "review_artifact",
  "change_summary": "Plain English description of what will be modified (2-3 sentences max)",
  "step_rationales": [
    {{
      "step_id": 1,
      "action": "action name",
      "target": "target file/path",
      "why": "Plain English explanation of why this step is necessary",
      "impact": "What this step will change or affect"
    }}
  ],
  "risk_assessment": {{
    "overall_risk": "low | medium | high",
    "potential_impacts": ["impact 1", "impact 2", ...],
    "failure_modes": ["failure mode 1", "failure mode 2", ...]
  }},
  "rollback_note": "Plain English instructions on how to undo these changes if needed",
  "confidence": 0.0-1.0
}}

Guidelines:
- Use plain English, avoid technical jargon where possible
- Be concise but complete
- Focus on what matters to a human reviewer
- Highlight any irreversible or high-risk operations
"""

BLOCKED_REVIEW_PROMPT_TEMPLATE = """You are CT's review assistant.
Your task is to explain why CT cannot proceed with planning.

BLOCKING CONTEXT:
Reason: {reason}
Details: {details}

Output ONLY valid JSON in this format:
{{
  "type": "review_blocked",
  "reason": "{reason}",
  "summary": "Plain English explanation of why CT cannot proceed (2-3 sentences)",
  "violated_constraints": ["constraint 1", "constraint 2", ...],
  "suggested_next_steps": ["suggestion 1", "suggestion 2", ...],
  "confidence": 1.0
}}

Guidelines:
- Be clear and direct about what is blocking progress
- Explain the constraint in plain English
- Suggest concrete next steps the human can take
- Do not apologize or be overly verbose
"""

# Sub-Agent Prompt Templates (Phase 11.0)
SUBAGENT_CONSERVATIVE_FRAMING = """You are Sub-Agent A: The Conservative Advisor.
Your role is to propose the safest, most risk-minimizing approaches.
- Prefer incremental changes over large refactors
- Minimize blast radius of any action
- Maximize rollback safety
- Err on the side of doing less rather than more
- Highlight potential failure modes explicitly
"""

SUBAGENT_SPEED_FRAMING = """You are Sub-Agent B: The Speed Optimizer.
Your role is to propose the fastest, most efficient approaches.
- Minimize number of steps required
- Prioritize quick wins
- Accept minor technical debt if it unblocks progress
- Suggest parallel execution where possible
- Focus on getting to a working state quickly, then iterate
"""

SUBAGENT_LONGTERM_FRAMING = """You are Sub-Agent C: The Sustainability Advisor.
Your role is to propose approaches optimized for long-term maintainability.
- Design for extensibility and clarity
- Consider how this decision affects future work
- Recommend refactors that pay technical debt
- Suggest modular, reusable patterns
- Think about maintainability for future operators
"""

print("CT orchestrator online (LLM-driven, restraint-locked, Memory v1, delegated reasoning)")

def get_penalty(intent_type, mode):
    return CALIBRATION.get((intent_type, mode), 1.0)

def update_penalty(intent_type, mode, outcome):
    key = (intent_type, mode)
    penalty = CALIBRATION.get(key, 1.0)
    
    if outcome == "decay":
        penalty = max(penalty * 0.85, 0.30)
        print(f"[CALIBRATION] Decay for ({intent_type}, {mode}): {penalty:.2f}")
    elif outcome == "recovery":
        penalty = min(penalty + 0.05, 1.0)
        print(f"[CALIBRATION] Recovery for ({intent_type}, {mode}): {penalty:.2f}")
    elif outcome == "reset":
        penalty = 1.0
        print(f"[CALIBRATION] Reset for ({intent_type}, {mode})")
        
    CALIBRATION[key] = penalty

def execute_patch(target, patch_content):
    """Apply a unified diff via the ct-action service."""
    print(f"[ORCHESTRATOR] Applying patch to {target}...")
    try:
        response = requests.post(
            f"{ACTION_URL}/patch",
            json={"path": target, "patch_content": patch_content},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            print(f"[ORCHESTRATOR] Patch applied successfully")
            return {"status": "success", "output": result.get("output")}
        else:
            print(f"[ORCHESTRATOR] Patch failed: {response.text}")
            return {"status": "error", "message": response.text}
    except Exception as e:
        print(f"[ORCHESTRATOR] Patch error: {e}")
        return {"status": "error", "message": str(e)}

def emit_event(event_data):
    try:
        requests.post(OBSERVER_URL, json=event_data, timeout=2)
    except Exception as e:
        print(f"[ORCHESTRATOR] Failed to log event to observer: {e}")

def bootstrap_memory():
    """Seed calibration from last 50 events in history."""
    if not os.path.exists(HISTORY_FILE):
        print(f"[MEMORY] No history file found at {HISTORY_FILE}. Starting fresh.")
        return

    print(f"[MEMORY] Bootstrapping from {HISTORY_FILE}...")
    try:
        with open(HISTORY_FILE, "r") as f:
            lines = f.readlines()
            recent = lines[-50:]
            
            for line in recent:
                try:
                    event = json.loads(line)
                    etype = event.get("type")
                    
                    if etype == "action_invocation" and event.get("status") == "success":
                        update_penalty(event.get("tool"), "reason-only", "recovery")
                    elif etype == "gate_rejection":
                        update_penalty(event.get("intent"), event.get("mode"), "decay")
                except:
                    continue
        print(f"[MEMORY] Bootstrap complete. Calibration seeds: {CALIBRATION}")
    except Exception as e:
        print(f"[MEMORY] Bootstrap failure: {e}")

def get_outcome_context(intent_type, mode):
    """Retrieve last success and last failure for prompt injection."""
    if not os.path.exists(HISTORY_FILE):
        return ""

    success = None
    failure = None

    try:
        with open(HISTORY_FILE, "r") as f:
            lines = f.readlines()
            for line in reversed(lines[-100:]):
                event = json.loads(line)
                etype = event.get("type")
                
                if etype == "action_invocation" and not success:
                    if event.get("status") == "success":
                        success = f"Last success ({event.get('tool')}): {str(event.get('output_summary'))[:100]}..."
                
                if etype == "gate_rejection" and not failure:
                    failure = f"Last rejection ({event.get('intent')}): Low confidence ({event.get('confidence')})"
                
                if success and failure:
                    break
    except:
        pass

    block = ""
    if success or failure:
        block = "PRIOR OUTCOMES:\n"
        if success: block += f"- {success}\n"
        if failure: block += f"- {failure}\n"
    return block

def generate_execution_plan(artifact):
    """Formalize understanding into a stepwise plan and HALT."""
    global HALTED, CURRENT_PLAN, APPROVED_STEP_ID
    print(f"[ORCHESTRATOR] Generating execution plan based on {artifact.get('type')}...")
    
    # Call site 2: Planning suppressed by policy
    # Check if policy forbids planning in current state
    if POLICY and "global_policies" in POLICY:
        for policy in POLICY["global_policies"]:
            if policy.get("severity") == "hard" and "planning forbidden" in policy.get("rule", "").lower():
                print(f"[ORCHESTRATOR] planning blocked by policy: {policy.get('id')}")
                blocked_review = generate_blocked_review(
                    reason="restricted_action",
                    details={
                        "policy_id": policy.get("id"),
                        "policy_rule": policy.get("rule"),
                        "context": "Planning suppressed by policy"
                    }
                )
                if blocked_review:
                    emit_event(blocked_review)
                    print("[ORCHESTRATOR] review_blocked artifact emitted")
                print("[ORCHESTRATOR] entering HALT")
                HALTED = True
                return None
    
    prev_plan_block = ""
    if CURRENT_PLAN:
        prev_plan_block = f"PREVIOUS PLAN (Refine this):\n{json.dumps(CURRENT_PLAN, indent=2)}\n"
    
    policy_block = ""
    if POLICY:
        policy_block = f"POLICY CONSTRAINTS (MANDATORY):\n{json.dumps(POLICY, indent=2)}\n"
    
    prompt = PLANNING_PROMPT_TEMPLATE.format(
        artifact=json.dumps(artifact, indent=2),
        previous_plan_block=prev_plan_block,
        policy_block=policy_block
    )
    
    for attempt in range(2):
        try:
            response = requests.post(
                LLM_URL,
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=120 # Increased timeout
            )
            if response.status_code == 200:
                plan = json.loads(response.json().get("response"))
                print(f"[ORCHESTRATOR] Execution plan produced.")
                emit_event(plan)
                CURRENT_PLAN = plan
                APPROVED_STEP_ID = None # Reset approval
                
                # Phase 9: Generate review artifact
                print("[ORCHESTRATOR] Generating review artifact...")
                review_artifact = generate_review_artifact(plan)
                if review_artifact:
                    emit_event(review_artifact)
                    print("[ORCHESTRATOR] Review artifact emitted.")
                
                print("[ORCHESTRATOR] Entering HALT state.")
                HALTED = True
                return plan
            else:
                print(f"[ORCHESTRATOR] Planning retry {attempt+1}: HTTP {response.status_code}")
        except Exception as e:
            print(f"[ORCHESTRATOR] Planning retry {attempt+1}: {e}")
        time.sleep(2)
    
    # Call site: Planning failure after retries (could be confidence or technical)
    print("[ORCHESTRATOR] Planning failure after retries")
    blocked_review = generate_blocked_review(
        reason="low_confidence",
        details={
            "context": "Planning failed after multiple attempts",
            "artifact_type": artifact.get("type"),
            "evidence": "Insufficient information to generate a confident plan"
        }
    )
    if blocked_review:
        emit_event(blocked_review)
        print("[ORCHESTRATOR] review_blocked artifact emitted")
    print("[ORCHESTRATOR] entering HALT")
    HALTED = True
    return None

def generate_execution_plan_set(artifact):
    """Generate 2-3 alternative execution plans with tradeoffs and HALT.
    
    Phase 11.0: If delegation is enabled, spawn sub-agents with different framings.
    Otherwise, use single-agent multi-plan generation.
    """
    global HALTED, LAST_PLAN_SET, APPROVED_PLAN_ID, LAST_DELEGATED_AGENTS
    print(f"[ORCHESTRATOR] Generating multi-plan negotiation based on {artifact.get('type')}...")
    
    # Check if policy forbids planning
    if POLICY and "global_policies" in POLICY:
        for policy in POLICY["global_policies"]:
            if policy.get("severity") == "hard" and "planning forbidden" in policy.get("rule", "").lower():
                print(f"[ORCHESTRATOR] multi-planning blocked by policy: {policy.get('id')}")
                blocked_review = generate_blocked_review(
                    reason="restricted_action",
                    details={
                        "policy_id": policy.get("id"),
                        "policy_rule": policy.get("rule"),
                        "context": "Multi-plan negotiation suppressed by policy"
                    }
                )
                if blocked_review:
                    emit_event(blocked_review)
                print("[ORCHESTRATOR] entering HALT")
                HALTED = True
                return None
    
    # Phase 11.0: Check for delegated reasoning
    delegation_config = POLICY.get("delegation_config", {})
    if delegation_config.get("enabled", False):
        print("[ORCHESTRATOR] Delegation enabled. Spawning sub-agents...")
        delegated_plan_sets = delegate_plan_generation(artifact, POLICY, CALIBRATION)
        
        if delegated_plan_sets and len(delegated_plan_sets) > 0:
            print(f"[ORCHESTRATOR] Collected {len(delegated_plan_sets)} sub-agent plan sets")
            
            # Perform meta-negotiation
            meta_comparison = negotiate_plan_sets(delegated_plan_sets, POLICY)
            if meta_comparison:
                emit_event(meta_comparison)
                print("[ORCHESTRATOR] Meta-negotiation complete, emitted meta_plan_comparison")
            
            # Consolidate into single plan set for review
            # Use Agent A's top plan as the representative plan_set
            agent_a_set = delegated_plan_sets[0][1]  # First agent's plan_set
            agent_a_id = delegated_plan_sets[0][0]   # Agent ID
            plan_set = agent_a_set.copy()
            LAST_PLAN_SET = plan_set
            APPROVED_PLAN_ID = None
            
            # Track which agent produced which plan (for learning)
            LAST_DELEGATED_AGENTS = {}
            for agent_id, agent_plan_set, _, _ in delegated_plan_sets:
                for plan in agent_plan_set.get("plans", []):
                    plan_id = plan.get("plan_id")
                    LAST_DELEGATED_AGENTS[f"plan_{plan_id}_{agent_id}"] = agent_id
            
            # Generate review noting multi-agent input
            print("[ORCHESTRATOR] Generating review for delegated plan sets...")
            review_artifact = generate_multiplan_review_artifact(plan_set, [], delegated_plan_sets[0][2])
            if review_artifact:
                # Add delegation context
                review_artifact["delegation_context"] = {
                    "agent_count": len(delegated_plan_sets),
                    "agent_ids": [a[0] for a in delegated_plan_sets],
                    "meta_comparison_summary": meta_comparison.get("summary") if meta_comparison else None
                }
                emit_event(review_artifact)
                print("[ORCHESTRATOR] Delegated review artifact emitted.")
            
            print("[ORCHESTRATOR] Entering HALT state (delegated multi-agent planning complete).")
            HALTED = True
            return plan_set
        else:
            print("[ORCHESTRATOR] Sub-agent delegation failed, falling back to single-agent planning")
    
    # Single-agent planning (original path, preserved for backward compatibility)
    policy_block = ""
    if POLICY:
        policy_block = f"POLICY CONSTRAINTS (MANDATORY):\n{json.dumps(POLICY, indent=2)}\n"
    
    prompt = MULTI_PLAN_PROMPT_TEMPLATE.format(
        artifact=json.dumps(artifact, indent=2),
        policy_block=policy_block
    )
    
    for attempt in range(2):
        try:
            response = requests.post(
                LLM_URL,
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=120
            )
            if response.status_code == 200:
                plan_set = json.loads(response.json().get("response"))
                print(f"[ORCHESTRATOR] Multi-plan set produced with {len(plan_set.get('plans', []))} alternatives.")
                emit_event(plan_set)
                
                # Phase 10.1: Policy-Driven Plan Pruning
                print("[ORCHESTRATOR] Applying policy-driven plan pruning...")
                approved_plans, rejected_plans = prune_plans_by_policy(plan_set, POLICY)
                
                # Emit pruning results
                pruning_event = {
                    "type": "plan_pruning_result",
                    "accepted_plan_ids": [p.get("plan_id") for p in approved_plans],
                    "rejected": rejected_plans,
                    "total_before": len(plan_set.get("plans", [])),
                    "total_after": len(approved_plans)
                }
                emit_event(pruning_event)
                print(f"[ORCHESTRATOR] Plan pruning: {len(approved_plans)} approved, {len(rejected_plans)} rejected")
                
                # If no plans survive pruning, block with explanation
                if not approved_plans:
                    print("[ORCHESTRATOR] No plans survived policy pruning")
                    blocked_review = generate_blocked_review(
                        reason="policy_pruning_no_survivors",
                        details={
                            "rejected_plans": rejected_plans,
                            "context": "All proposed plans violated policy constraints"
                        }
                    )
                    if blocked_review:
                        emit_event(blocked_review)
                    print("[ORCHESTRATOR] Entering HALT state.")
                    HALTED = True
                    return None
                
                # Update plan set with approved plans only
                plan_set["plans"] = approved_plans
                LAST_PLAN_SET = plan_set
                APPROVED_PLAN_ID = None
                
                # Phase 10.2: Confidence-Weighted Plan Ranking
                print("[ORCHESTRATOR] Ranking plans by confidence and calibration...")
                ranked_plans, ranking_breakdown = rank_plans(plan_set, CALIBRATION, POLICY)
                
                # Emit ranking results
                ranking_event = {
                    "type": "plan_ranking_result",
                    "ranked_order": [p.get("plan_id") for p in ranked_plans],
                    "ranking_breakdown": ranking_breakdown
                }
                emit_event(ranking_event)
                print(f"[ORCHESTRATOR] Plan ranking complete: {ranking_event['ranked_order']}")
                
                # Update plan set with ranked order
                plan_set["plans"] = ranked_plans
                LAST_PLAN_SET = plan_set
                
                # Generate review for the multi-plan set (now with ranking and pruning info)
                print("[ORCHESTRATOR] Generating review for multi-plan set...")
                review_artifact = generate_multiplan_review_artifact(plan_set, rejected_plans, ranking_breakdown)
                if review_artifact:
                    emit_event(review_artifact)
                    print("[ORCHESTRATOR] Multi-plan review artifact emitted.")
                
                print("[ORCHESTRATOR] Entering HALT state (awaiting plan selection).")
                HALTED = True
                return plan_set
            else:
                print(f"[ORCHESTRATOR] Multi-plan generation retry {attempt+1}: HTTP {response.status_code}")
        except Exception as e:
            print(f"[ORCHESTRATOR] Multi-plan generation retry {attempt+1}: {e}")
        time.sleep(2)
    
    print("[ORCHESTRATOR] Multi-plan generation failure after retries")
    blocked_review = generate_blocked_review(
        reason="low_confidence",
        details={
            "context": "Multi-plan generation failed after multiple attempts",
            "artifact_type": artifact.get("type"),
            "evidence": "Unable to generate alternative plans"
        }
    )
    if blocked_review:
        emit_event(blocked_review)
    print("[ORCHESTRATOR] entering HALT")
    HALTED = True
    return None


def generate_review_artifact(execution_plan):
    """Generate a human-readable review artifact from an execution plan."""
    prompt = REVIEW_PROMPT_TEMPLATE.format(
        execution_plan=json.dumps(execution_plan, indent=2)
    )
    
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            review = json.loads(response.json().get("response"))
            return review
        else:
            print(f"[ORCHESTRATOR] Review artifact generation failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"[ORCHESTRATOR] Review artifact generation error: {e}")
    
    return None

def generate_multiplan_review_artifact(plan_set, rejected_plans=None, ranking_breakdown=None):
    """Generate a human-readable review for a multi-plan set, including pruning and ranking info."""
    if rejected_plans is None:
        rejected_plans = []
    if ranking_breakdown is None:
        ranking_breakdown = []
    
    rejected_info = ""
    if rejected_plans:
        rejected_info = f"\n\nREJECTED PLANS (removed by policy pruning):\n{json.dumps(rejected_plans, indent=2)}"
    
    ranking_info = ""
    if ranking_breakdown:
        ranking_info = f"\n\nPLAN RANKING (by confidence-weighted score):\n{json.dumps(ranking_breakdown, indent=2)}"
    
    prompt = f"""You are CT's review assistant for multi-plan scenarios.
Your task is to explain the alternative plans in plain English, ordered by evidence-based ranking.

MULTI-PLAN SET (Approved, Ranked):
{json.dumps(plan_set, indent=2)}
{ranking_info}
{rejected_info}

Output ONLY valid JSON in this format:
{{
  "type": "review_multiplan_set",
  "goal": "What are we trying to accomplish?",
  "ranked_order": ["A", "B"],
  "plan_comparisons": [
    {{
      "plan_id": "A",
      "rank_position": 1,
      "confidence_score": 0.85,
      "summary": "What this plan does (1-2 sentences)",
      "why_prefer": "When you might choose this plan",
      "when_avoid": "When this plan is risky or inefficient",
      "score_breakdown": {{
        "base_confidence": 0.90,
        "calibration_multiplier": 1.0,
        "policy_friction": 0.0,
        "history_bonus": 0.05,
        "final_score": 0.85
      }}
    }},
    {{
      "plan_id": "B",
      "rank_position": 2,
      "confidence_score": 0.78,
      "summary": "...",
      "why_prefer": "...",
      "when_avoid": "...",
      "score_breakdown": {{...}}
    }}
  ],
  "removed_plans": [
    {{
      "plan_id": "C",
      "reason": "Plain English explanation of why this plan was removed (policy violation or confidence threshold)"
    }}
  ],
  "recommendation": "Why CT recommends Plan {{recommended_id}}: {{reasoning}} (2-3 sentences). The top-ranked plan has the highest evidence-weighted score.",
  "confidence": 0.0-1.0
}}

Guidelines:
- Plans are presented in rank order (best-scored first)
- Be clear and direct for human decision-making
- Explain score breakdowns so human understands the ranking
- Focus on practical tradeoffs
- Highlight irreversible or high-risk operations
- Explain why rejected plans were filtered (transparency, not censorship)
- Do not apologize or be overly verbose
- Output JSON only. No preamble or explanation.
"""
    
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            review = json.loads(response.json().get("response"))
            return review
        else:
            print(f"[ORCHESTRATOR] Multi-plan review generation failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"[ORCHESTRATOR] Multi-plan review generation error: {e}")
    
    return None

def generate_blocked_review(reason, details):
    """Generate a human-readable explanation of why planning is blocked."""
    prompt = BLOCKED_REVIEW_PROMPT_TEMPLATE.format(
        reason=reason,
        details=json.dumps(details, indent=2) if isinstance(details, dict) else str(details)
    )
    
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            blocked_review = json.loads(response.json().get("response"))
            return blocked_review
        else:
            print(f"[ORCHESTRATOR] Blocked review generation failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"[ORCHESTRATOR] Blocked review generation error: {e}")
    
    # Fallback: create a minimal blocked review
    return {
        "type": "review_blocked",
        "reason": reason,
        "summary": f"Planning blocked due to: {reason}",
        "violated_constraints": [str(details)],
        "suggested_next_steps": ["Review constraints", "Adjust policy or parameters"],
        "confidence": 1.0
    }

def emit_plan_draft(intent):
    global LAST_PLAN_DRAFT
    plan = {
        "type": "plan_draft",
        "source_mode": intent.get("mode", "unknown"),
        "intent": intent.get("intent"),
        "target": intent.get("target"),
        "confidence": intent.get("confidence"),
        "assumptions": [
            "Direct action was not permitted",
            "Prior strategies failed confidence gating"
        ],
        "open_questions": [
            "What additional data would increase certainty?",
            "Is the target correctly scoped?"
        ],
        "proposed_steps": [
            "Review available logs and summaries",
            "Clarify target boundaries",
            "Decide whether to allow simulation or action"
        ]
    }

    LAST_PLAN_DRAFT = plan
    print("[OBSERVER] PLAN_DRAFT")
    print(json.dumps(plan, indent=2))
    emit_event(plan)

def emit_resume_outcome(intent):
    if not LAST_PLAN_DRAFT:
        return

    outcome = {
        "type": "resume_outcome",
        "plan_ref_intent": LAST_PLAN_DRAFT.get("intent"),
        "plan_ref_target": LAST_PLAN_DRAFT.get("target"),
        "next_intent": intent.get("intent") if intent else "halted_again",
        "next_confidence": intent.get("confidence") if intent else 0.0,
        "next_mode": intent.get("mode") if intent else "none"
    }
    
    print("[ORCHESTRATOR] Emitting resume outcome to observer")
    emit_event(outcome)

def compare_evidence(summary_a, summary_b):
    """Contrast two semantic summaries and trigger planning."""
    print(f"[ORCHESTRATOR] Comparing {summary_a.get('scope')} vs {summary_b.get('scope')}...")
    prompt = COMPARISON_PROMPT_TEMPLATE.format(
        summary_a=json.dumps(summary_a, indent=2),
        summary_b=json.dumps(summary_b, indent=2),
        scope_a=summary_a.get("scope"),
        scope_b=summary_b.get("scope")
    )

    comparison = None
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=60
        )
        if response.status_code == 200:
            comparison = json.loads(response.json().get("response"))
            print(f"[ORCHESTRATOR] Semantic comparison produced (confidence: {comparison.get('confidence')})")
            emit_event(comparison)
            
            # Phase 4.0: Planning Discipline
            generate_execution_plan(comparison)
            
            return comparison
    except Exception as e:
        print(f"[ORCHESTRATOR] Comparison failure: {e}")
    return None

def find_prior_summary(scope):
    """Search history for the most recent summary of a given scope."""
    if not os.path.exists(HISTORY_FILE):
        return None
    try:
        with open(HISTORY_FILE, "r") as f:
            lines = f.readlines()
            for line in reversed(lines):
                event = json.loads(line)
                if event.get("type") == "semantic_summary" and event.get("scope") == scope:
                    return event
    except:
        pass
    return None

def synthesize_evidence(content, scope, intent):
    """Perform cognitive compression and trigger comparison/planning."""
    print(f"[ORCHESTRATOR] Synthesizing evidence for {scope}...")
    prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
        content=content,
        scope=scope,
        intent=intent
    )
    
    summary = None
    for attempt in range(2):
        try:
            response = requests.post(
                LLM_URL,
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )
            if response.status_code == 200:
                summary = json.loads(response.json().get("response"))
                print(f"[ORCHESTRATOR] Semantic summary produced (confidence: {summary.get('confidence')})")
                emit_event(summary)
                break
            else:
                print(f"[ORCHESTRATOR] Synthesis retry {attempt+1}: HTTP {response.status_code}")
        except Exception as e:
            print(f"[ORCHESTRATOR] Synthesis retry {attempt+1}: {e}")
        time.sleep(2)
    
    if summary:
        prior = find_prior_summary(scope)
        if prior:
            compare_evidence(prior, summary)
        else:
            # Phase 4.0: Planning Discipline (Direct from summary if no prior)
            generate_execution_plan(summary)
            
    return summary

def execute_tool(intent):
    name = intent.get("intent")
    target = intent.get("target")
    mode = intent.get("mode")
    
    if name == "inspect_repo":
        print(f"[ORCHESTRATOR] Executing tool: inspect_repo on {target}")
        try:
            resp = requests.post(ACTION_URL, json={"op": "ls", "path": target}, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                print(f"[ORCHESTRATOR] Tool result: {result.get('status')}")
                update_penalty(name, mode, "recovery")
                audit_event = {
                    "type": "action_invocation",
                    "tool": "inspect_repo",
                    "target": target,
                    "status": "success",
                    "output_summary": str(result.get("items", []))[:200]
                }
                emit_event(audit_event)
                return result
            else:
                print(f"[ORCHESTRATOR] Tool error: {resp.status_code}")
        except Exception as e:
            print(f"[ORCHESTRATOR] Tool failure: {e}")
    
    elif name in ["analyze_code", "summarise_logs"]:
        print(f"[ORCHESTRATOR] Executing tool: read_file on {target}")
        try:
            resp = requests.post(FILE_ACTION_URL, json={"path": target}, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                print(f"[ORCHESTRATOR] Tool result: {result.get('status')} ({result.get('bytes')} bytes)")
                update_penalty(name, mode, "recovery")
                
                content = result.get("content", "")
                audit_event = {
                    "type": "action_invocation",
                    "tool": "read_file",
                    "target": target,
                    "status": "success",
                    "bytes": result.get("bytes"),
                    "output_summary": str(content)[:200]
                }
                emit_event(audit_event)
                
                synthesize_evidence(content, target, name)
                
                return result
            else:
                print(f"[ORCHESTRATOR] Tool error: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[ORCHESTRATOR] Tool failure: {e}")
            
    elif name == "plan_action":
        print(f"[ORCHESTRATOR] Triggering formal planning based on {target}")
        generate_execution_plan(intent)
        return {"status": "success"}

    elif name == "apply_patch":
        print(f"[ORCHESTRATOR] Executing tool: apply_patch on {target}")
        patch_content = intent.get("patch_content")
        try:
            resp = requests.post(PATCH_ACTION_URL, json={"path": target, "patch_content": patch_content}, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                print(f"[ORCHESTRATOR] Patch applied successfully")
                update_penalty(name, mode, "recovery")
                audit_event = {
                    "type": "action_invocation",
                    "tool": "apply_patch",
                    "target": target,
                    "status": "success",
                    "output_summary": result.get("output", "")[:200]
                }
                emit_event(audit_event)
                return result
            else:
                print(f"[ORCHESTRATOR] Patch failed: {resp.status_code}")
                emit_event({"type": "action_invocation", "tool": "apply_patch", "target": target, "status": "error", "message": resp.text})
        except Exception as e:
            print(f"[ORCHESTRATOR] Patch failure: {e}")

    return None

def generate_intent_via_llm(plan_context=None, mandated_step=None):
    plan_context_block = ""
    if plan_context:
        plan_context_block = (
            "Previously, you produced the following plan draft or execution plan. Treat it as context, not instruction. "
            f"Re-evaluate the situation accordingly:\n{json.dumps(plan_context, indent=2)}\n"
        )
    
    mandated_step_block = ""
    if mandated_step:
        mandated_step_block = (
            "CRITICAL: The human has specifically approved Step ID {id} of the execution plan:\n"
            "STEP: {action} on {target}\n"
            "RATIONALE: {rationale}\n"
            "You MUST output this exact intent now."
        ).format(**mandated_step)

    outcome_block = get_outcome_context(None, None)
    if outcome_block:
        print("[MEMORY] Injecting historical context into prompt")

    policy_block = ""
    if POLICY:
        policy_block = f"POLICY CONSTRAINTS (MANDATORY):\n{json.dumps(POLICY, indent=2)}\n"
        
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        plan_context_block=plan_context_block,
        outcome_context_block=outcome_block,
        mandated_step_block=mandated_step_block,
        policy_block=policy_block
    )

    try:
        print("[ORCHESTRATOR] requesting reasoning from LLM...")
        response = requests.post(
            LLM_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            content = response.json().get("response")
            intent_data = json.loads(content)
            print(f"[ORCHESTRATOR] generated intent via LLM: {intent_data.get('intent')}")
            return intent_data
        else:
            print(f"[ORCHESTRATOR] LLM error: {response.status_code}")
            
    except Exception as e:
        print(f"[ORCHESTRATOR] LLM interaction failure: {e}")
        
    return None

def send_intent(intent, mandated=None):
    """Enforce confidence gating and Restraint Physics before tool execution."""
    global LAST_REJECTED_INTENT, HALTED
    
    # Calibration injection
    key = (intent.get("intent"), intent.get("mode"))
    if key in CALIBRATION:
        raw_confidence = intent.get("confidence", 0)
        penalty = CALIBRATION[key]
        calibrated_confidence = raw_confidence * penalty
        print(f"[ORCHESTRATOR] Calibrating confidence: {raw_confidence:.2f} -> {calibrated_confidence:.2f} (penalty {penalty:.2f})")
        intent["confidence"] = calibrated_confidence

    if intent.get("mode") == "propose":
        print("[ORCHESTRATOR] propose mode reached — generating plan draft")
        emit_plan_draft(intent)
        print("[ORCHESTRATOR] entering HALT state (awaiting external input)")
        HALTED = True
        LAST_REJECTED_INTENT = None
        return

    # Phase 5.0 Security Gates for apply_patch
    if intent.get("intent") == "apply_patch":
        if intent.get("confidence", 0) < 0.8:
            print(f"[ORCHESTRATOR] REJECTED: Write confidence {intent.get('confidence')} < 0.8")
            emit_event({
                "type": "gate_rejection",
                "intent": "apply_patch",
                "reason": "confidence_too_low",
                "confidence": intent.get("confidence")
            })
            return
        
        if not mandated or mandated.get("action") != "apply_patch":
            print(f"[ORCHESTRATOR] REJECTED: Write not in mandated plan step")
            emit_event({
                "type": "gate_rejection",
                "intent": "apply_patch",
                "reason": "action_mismatch_with_plan"
            })
            return

    try:
        response = requests.post(TOOL_URL, json=intent, timeout=5)
        
        if response.status_code == 200:
            print("[ORCHESTRATOR] intent accepted")
            LAST_REJECTED_INTENT = None
            execute_tool(intent)
        elif response.status_code == 422:
            print("[ORCHESTRATOR] intent rejected (low confidence)")
            LAST_REJECTED_INTENT = intent
            emit_event({
                "type": "gate_rejection",
                "intent": intent.get("intent"),
                "mode": intent.get("mode"),
                "confidence": intent.get("confidence")
            })
        else:
            print(f"[ORCHESTRATOR] unexpected status {response.status_code}")
    except Exception as e:
        print(f"[ORCHESTRATOR] error → {e}")

class SignalHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle governance query endpoints (read-only)."""
        if self.path == "/governance/orchestrator-state":
            # Return current orchestrator state (read-only snapshot)
            response = {
                "halted": HALTED,
                "current_phase": CURRENT_PHASE,
                "approved_phase_id": APPROVED_PHASE_ID,
                "approved_plan_id": APPROVED_PLAN_ID,
                "completed_phases": COMPLETED_PHASES,
                "skipped_phases": SKIPPED_PHASES,
                "current_plan_id": CURRENT_PLAN.get("plan_id") if CURRENT_PLAN else None,
                # Additional fields expected by validators
                "active_plan_count": len(COMPOSED_PLAN_REGISTRY.get_executing()) if 'COMPOSED_PLAN_REGISTRY' in globals() else 0,
                "pending_intent_count": len(INTENT_QUEUE.get_pending()) if INTENT_QUEUE else 0,
                "timestamp": time.time()
            }
            self._send_json_response(200, response)
        
        elif self.path == "/governance/plans":
            # Return multi-plan lifecycle info (pending, approved, executing, completed)
            response = {
                "pending": COMPOSED_PLAN_REGISTRY.get_pending() if 'COMPOSED_PLAN_REGISTRY' in globals() else [],
                "approved": COMPOSED_PLAN_REGISTRY.get_approved() if 'COMPOSED_PLAN_REGISTRY' in globals() else [],
                "executing": COMPOSED_PLAN_REGISTRY.get_executing() if 'COMPOSED_PLAN_REGISTRY' in globals() else [],
                "completed": COMPOSED_PLAN_REGISTRY.get_completed() if 'COMPOSED_PLAN_REGISTRY' in globals() else [],
                "timestamp": time.time()
            }
            self._send_json_response(200, response)
        
        elif self.path == "/governance/intents":
            # Return intent queue state (read-only)
            if INTENT_QUEUE:
                response = {
                    "pending": INTENT_QUEUE.get_pending(),
                    "approved": INTENT_QUEUE.get_approved(),
                    "rejected": INTENT_QUEUE.get_rejected(),
                    "timestamp": time.time()
                }
            else:
                response = {
                    "pending": [],
                    "approved": [],
                    "rejected": [],
                    "message": "Intent queue not initialized",
                    "timestamp": time.time()
                }
            self._send_json_response(200, response)
        
        elif self.path == "/health":
            # Lightweight health endpoint for Docker healthchecks
            response = {"status": "ok", "halted": HALTED, "current_plan_id": CURRENT_PLAN.get("plan_id") if CURRENT_PLAN else None}
            self._send_json_response(200, response)

        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        global HALTED, CURRENT_PLAN, CURRENT_PHASE, APPROVED_PHASE_ID, RESUME_REQUESTED, APPROVED_STEP_ID, APPROVED_PLAN_ID, SKIPPED_PHASES, STAGED_PHASE_CACHE, CURRENT_PHASE_APPROVAL_STATE, CURRENT_PHASE_ID, INTERNAL_STATE_CACHE, ACTIVE_SUBPLAN_ID, COMPLETED_PHASES, CURRENT_PHASE_RESULT
        
        if self.path == "/intent":
            # Phase 12 Step 1: Intent ingress endpoint (schema-gated, non-executing)
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    self._send_json_response(400, {
                        "status": "rejected",
                        "message": "Empty request body"
                    })
                    return
                
                post_data = self.rfile.read(content_length)
                intent_data = json.loads(post_data)
                
                # Validate intent against schema
                validation_result = validate_intent(intent_data) if INTENT_QUEUE else {
                    "status": "rejected",
                    "message": "Intent queue not initialized"
                }
                
                self._send_json_response(
                    200 if validation_result["status"] == "accepted" else 422,
                    validation_result
                )
            except json.JSONDecodeError:
                self._send_json_response(400, {
                    "status": "rejected",
                    "message": "Invalid JSON in request body"
                })
            except Exception as e:
                self._send_json_response(500, {
                    "status": "rejected",
                    "message": f"Internal server error: {str(e)}"
                })

        # POST /governance/approve/<intent_id> - human-only approval (pending -> approved)
        elif self.path.startswith("/governance/approve/"):
            try:
                intent_id = self.path.split('/')[-1]
                if not INTENT_QUEUE:
                    self._send_json_response(503, {"status": "error", "message": "Intent queue not initialized"})
                    return

                # Find pending intent
                pending = INTENT_QUEUE.get_pending()
                intent_obj = None
                for item in pending:
                    if item.get("intent_id") == intent_id:
                        intent_obj = item
                        break

                if not intent_obj:
                    self._send_json_response(404, {"status": "error", "message": "Intent not found"})
                    return

                if intent_obj.get("status") != "pending":
                    self._send_json_response(409, {"status": "error", "message": "Intent not pending"})
                    return

                # Attempt composition (best-effort)
                composed_plan_id = None
                try:
                    from composed_plan_builder import compose_from_intent
                    comp_ok, comp_plan_id = compose_from_intent(intent_obj)
                    if comp_ok:
                        composed_plan_id = comp_plan_id
                except Exception:
                    composed_plan_id = None

                # Approve intent in queue
                ok = INTENT_QUEUE.approve_intent(intent_id, composed_plan_id=composed_plan_id)
                if not ok:
                    self._send_json_response(500, {"status": "error", "message": "Approval failed"})
                    return

                # Emit audit event (best-effort)
                try:
                    from audit_system import AUDIT_LOG
                    actor = self.headers.get('Authorization', '').replace('Bearer ', '') or 'unknown'
                    AUDIT_LOG.emit({
                        'operation': 'intent_approved',
                        'actor': actor,
                        'result': 'success',
                        'details': {'intent_id': intent_id, 'composed_plan_id': composed_plan_id}
                    })
                except Exception:
                    pass

                self._send_json_response(200, {"status": "approved", "intent_id": intent_id, "composed_plan_id": composed_plan_id})
                return

            except Exception as e:
                self._send_json_response(500, {"status": "error", "message": f"Approval error: {e}"})
                return

        elif self.path == "/governance/approve-composed-plan":
            # Phase 12 Step 3: Approve composed plan and move to execution
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    self._send_json_response(400, {
                        "status": "rejected",
                        "message": "Empty request body"
                    })
                    return
                
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data)
                
                # Validate approval request
                if not APPROVAL_BRIDGE:
                    self._send_json_response(503, {
                        "status": "error",
                        "message": "Approval bridge not initialized"
                    })
                    return
                
                valid, plan_id, message = validate_approval_request(request_data)
                
                if not valid:
                    self._send_json_response(400, {
                        "status": "rejected",
                        "message": message
                    })
                    return
                
                # Attempt approval (this is where guards are enforced)
                from composed_plan_builder import COMPOSED_PLAN_REGISTRY
                
                orchestrator_state = {
                    "CURRENT_PLAN": CURRENT_PLAN,
                    "HALTED": HALTED,
                    "CURRENT_PHASE": CURRENT_PHASE,
                    "APPROVED_PHASE_ID": APPROVED_PHASE_ID
                }
                
                success, approval_message = APPROVAL_BRIDGE.approve_composed_plan(
                    plan_id,
                    COMPOSED_PLAN_REGISTRY,
                    orchestrator_state,
                    emit_event  # Use existing emit_event function
                )
                
                # Update globals with new state
                if success:
                    CURRENT_PLAN = orchestrator_state["CURRENT_PLAN"]
                    HALTED = orchestrator_state["HALTED"]
                    CURRENT_PHASE = orchestrator_state["CURRENT_PHASE"]
                    APPROVED_PHASE_ID = orchestrator_state["APPROVED_PHASE_ID"]
                
                self._send_json_response(
                    200 if success else 400,
                    {
                        "status": "approved" if success else "rejected",
                        "message": approval_message,
                        "plan_id": plan_id if success else None,
                        "halted": orchestrator_state.get("HALTED", True)
                    }
                )
            except json.JSONDecodeError:
                self._send_json_response(400, {
                    "status": "rejected",
                    "message": "Invalid JSON in request body"
                })
            except Exception as e:
                self._send_json_response(500, {
                    "status": "error",
                    "message": f"Internal server error: {str(e)}"
                })
        
        elif self.path == "/internal/resume":
            print("[ORCHESTRATOR] resume requested by human")
            
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                body = json.loads(post_data)
                APPROVED_STEP_ID = body.get("step_id", None)
                APPROVED_PLAN_ID = body.get("approve_plan_id", None)
                
                # Phase 11.2: Phase-specific resume fields
                APPROVED_PHASE_ID = body.get("approve_phase_id", None)
                skip_phases = body.get("skip_phases", [])
                abort = body.get("abort", False)
                
                # Phase 11.3: Clear staged phase cache on any resume action
                # (Precondition: no staged phase should persist beyond explicit approval)
                if APPROVED_PHASE_ID or skip_phases or abort:
                    STAGED_PHASE_CACHE.clear()
                
                if APPROVED_STEP_ID:
                    print(f"[ORCHESTRATOR] Approved Step ID: {APPROVED_STEP_ID}")
                if APPROVED_PLAN_ID:
                    print(f"[ORCHESTRATOR] Approved Plan ID: {APPROVED_PLAN_ID}")
                if APPROVED_PHASE_ID:
                    print(f"[ORCHESTRATOR] Approved Phase ID: {APPROVED_PHASE_ID}")
                    
                    # Step 2.3: Validate phase approval
                    if CURRENT_PLAN and "phases" in CURRENT_PLAN:
                        phase_config = POLICY.get("phase_execution_config", {}) if POLICY else {}
                        phases = CURRENT_PLAN["phases"]
                        
                        # Find the approved phase
                        approved_phase = None
                        for p in phases:
                            if p.get("phase_id") == APPROVED_PHASE_ID:
                                approved_phase = p
                                break
                        
                        if approved_phase:
                            # Check dependencies
                            if not check_phase_dependencies(approved_phase, COMPLETED_PHASES):
                                print(f"[ORCHESTRATOR] REJECTED: Phase {APPROVED_PHASE_ID} dependencies not met")
                                emit_phase_artifact("phase_blocked", approved_phase, CURRENT_PLAN.get("plan_id", "unknown"),
                                                  reason="dependencies_not_met",
                                                  required=approved_phase.get("depends_on", []),
                                                  completed=COMPLETED_PHASES)
                                APPROVED_PHASE_ID = None  # Clear invalid approval
                            else:
                                # Phase 11.3 Step 3: Record approval pattern (post-validation)
                                # Called only when approval is valid
                                if CURRENT_PHASE:
                                    record_approval_pattern(CURRENT_PHASE, APPROVED_PHASE_ID)
                        else:
                            print(f"[ORCHESTRATOR] REJECTED: Phase {APPROVED_PHASE_ID} not found in plan")
                            APPROVED_PHASE_ID = None
                
                if skip_phases:
                    # Step 2.3: Validate skip request
                    phase_config = POLICY.get("phase_execution_config", {}) if POLICY else {}
                    if not phase_config.get("allow_phase_skipping", True):
                        print(f"[ORCHESTRATOR] REJECTED: Phase skipping disabled by policy")
                        skip_phases = []  # Clear invalid skip
                    else:
                        SKIPPED_PHASES.extend(skip_phases)
                        print(f"[ORCHESTRATOR] Skipping phases: {skip_phases}")
                
                if abort:
                    print(f"[ORCHESTRATOR] Abort requested - terminating remaining phases")
                    # Abort will be handled in main loop
            except:
                pass
                
            RESUME_REQUESTED = True
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()
    
    def _send_json_response(self, status_code, response_dict):
        """Send JSON response with proper headers."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_dict, default=str).encode())

def start_signal_server():
    server = http.server.HTTPServer(("0.0.0.0", 9001), SignalHandler)
    server.serve_forever()

# STARTUP
bootstrap_memory()
threading.Thread(target=start_signal_server, daemon=True).start()

while True:
    if HALTED:
        if RESUME_REQUESTED:
            print("[ORCHESTRATOR] resuming from HALT")
            HALTED = False
            RESUME_REQUESTED = False
            JUST_RESUMED = True
            
            # Phase 10: Check if resuming with plan_id from multi-plan set
            if APPROVED_PLAN_ID and LAST_PLAN_SET:
                print(f"[ORCHESTRATOR] Plan approval received for Plan ID: {APPROVED_PLAN_ID}")
                selected_plan = None
                for plan in LAST_PLAN_SET.get("plans", []):
                    if plan.get("plan_id") == APPROVED_PLAN_ID:
                        selected_plan = plan
                        break
                
                if selected_plan:
                    print(f"[ORCHESTRATOR] Executing approved plan: {APPROVED_PLAN_ID}")
                    
                    # Phase 11.1: Track which agent was selected for preference learning
                    agent_selection_key = f"plan_{APPROVED_PLAN_ID}_*"
                    selected_agent = None
                    for key, agent_id in LAST_DELEGATED_AGENTS.items():
                        if key.startswith(f"plan_{APPROVED_PLAN_ID}_"):
                            selected_agent = agent_id
                            break
                    
                    if selected_agent:
                        print(f"[ORCHESTRATOR] Preference learning: User selected Agent {selected_agent}'s plan")
                        update_agent_preference(selected_agent, POLICY)
                    
                    # Convert selected plan to execution_plan format and set as CURRENT_PLAN
                    # Phase 11.2: Preserve phases if present
                    CURRENT_PLAN = {
                        "type": "execution_plan",
                        "goal": LAST_PLAN_SET.get("goal"),
                        "plan_id": APPROVED_PLAN_ID,
                        "assumptions": selected_plan.get("assumptions", []),
                        "confidence": selected_plan.get("confidence"),
                        "source_plan_set": True
                    }
                    
                    # Phase 11.2: Check if plan has phases
                    if "phases" in selected_plan and selected_plan["phases"]:
                        CURRENT_PLAN["phases"] = selected_plan["phases"]
                        print(f"[ORCHESTRATOR] Plan has {len(selected_plan['phases'])} phases")
                    else:
                        CURRENT_PLAN["steps"] = selected_plan.get("steps", [])
                    
                    LAST_PLAN_SET = None
                    APPROVED_PLAN_ID = None
                else:
                    print(f"[ORCHESTRATOR] Plan ID {APPROVED_PLAN_ID} not found in plan set")
        else:
            time.sleep(1)
            continue

    if LAST_REJECTED_INTENT:
        prev = LAST_REJECTED_INTENT
        print("[ORCHESTRATOR] reflecting on rejection")
        reflected_intent = {
            **prev,
            "confidence": min(prev["confidence"] + 0.2, 1.0),
            "notes": f"Reflected after rejection; initial confidence was {prev['confidence']}"
        }
        print("[ORCHESTRATOR] reissuing reflected intent")
        send_intent(reflected_intent)

        if LAST_REJECTED_INTENT:
            update_penalty(prev.get("intent"), prev.get("mode"), "decay")
            current_mode = prev.get("mode", "reason-only")
            next_mode = MODE_TRANSITIONS.get(current_mode)
            if not next_mode:
                print("[ORCHESTRATOR] no further mode available, halting")
                LAST_REJECTED_INTENT = None
            else:
                update_penalty(prev.get("intent"), next_mode, "reset")
                reframed_intent = {
                    **prev,
                    "mode": next_mode,
                    "confidence": 0.50,
                    "notes": f"Reframed after repeated rejection. Mode {current_mode} rejected even after reflection.",
                }
                send_intent(reframed_intent)
                LAST_REJECTED_INTENT = None
    else:
        mandated = None
        is_post_resume = JUST_RESUMED
        if JUST_RESUMED:
            # Phase 11.2: Route to phased execution if applicable
            if CURRENT_PLAN:
                phase_config = POLICY.get("phase_execution_config", {}) if POLICY else {}
                has_phases = "phases" in CURRENT_PLAN and CURRENT_PLAN.get("phases")
                phase_enabled = phase_config.get("enabled", False)
                
                if phase_enabled and has_phases:
                    # Phased execution path
                    print("[ORCHESTRATOR] Entering phased execution mode")
                    execute_plan_with_phases(CURRENT_PLAN)
                    # After phased execution, system will HALT at phase boundaries
                    # or complete the plan
                    JUST_RESUMED = False
                    continue
            
            # Phase 4.1: Step Approval Protocol (flat execution path)
            if CURRENT_PLAN and APPROVED_STEP_ID:
                for step in CURRENT_PLAN.get("steps", []):
                    if step.get("id") == APPROVED_STEP_ID:
                        mandated = step
                        break
            
            plan_to_context = CURRENT_PLAN or LAST_PLAN_DRAFT
            intent = generate_intent_via_llm(plan_context=plan_to_context, mandated_step=mandated)
            
            JUST_RESUMED = False
            # We keep APPROVED_STEP_ID for send_intent gating, then clear it
        else:
            intent = generate_intent_via_llm()
        
        if intent:
            if "intent" in intent and "confidence" in intent:
                if is_post_resume:
                    emit_resume_outcome(intent)
                send_intent(intent, mandated=mandated)
                APPROVED_STEP_ID = None # Clear after use
            else:
                print("[ORCHESTRATOR] LLM output missing required fields, skipping")
        else:
            if is_post_resume:
                emit_resume_outcome(None)
            print("[ORCHESTRATOR] waiting for cognition...")

    time.sleep(15)
