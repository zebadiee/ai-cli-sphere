import time, random, requests, json, threading, http.server, os

INTENTS = [
    "inspect_repo",
    "summarise_logs",
    "analyze_code",
    "plan_action",
    "apply_patch"
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

print("CT orchestrator online (LLM-driven, restraint-locked, Memory v1)")

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
    """Generate 2-3 alternative execution plans with tradeoffs and HALT."""
    global HALTED, LAST_PLAN_SET, APPROVED_PLAN_ID
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
                LAST_PLAN_SET = plan_set
                APPROVED_PLAN_ID = None
                
                # Generate review for the multi-plan set
                print("[ORCHESTRATOR] Generating review for multi-plan set...")
                review_artifact = generate_multiplan_review_artifact(plan_set)
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

def generate_multiplan_review_artifact(plan_set):
    """Generate a human-readable review for a multi-plan set."""
    prompt = f"""You are CT's review assistant for multi-plan scenarios.
Your task is to explain the alternative plans in plain English.

MULTI-PLAN SET:
{json.dumps(plan_set, indent=2)}

Output ONLY valid JSON in this format:
{{
  "type": "review_multiplan_set",
  "goal": "What are we trying to accomplish?",
  "plan_comparisons": [
    {{
      "plan_id": "A",
      "summary": "What this plan does (1-2 sentences)",
      "why_prefer": "When you might choose this plan",
      "when_avoid": "When this plan is risky or inefficient"
    }},
    {{
      "plan_id": "B",
      "summary": "...",
      "why_prefer": "...",
      "when_avoid": "..."
    }}
  ],
  "recommendation": "Why CT recommends {{recommended_id}}: {{reasoning}} (2-3 sentences)",
  "confidence": 0.0-1.0
}}

Guidelines:
- Be clear and direct for human decision-making
- Focus on practical tradeoffs
- Highlight irreversible or high-risk operations
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
    def do_POST(self):
        if self.path == "/internal/resume":
            global RESUME_REQUESTED, APPROVED_STEP_ID, APPROVED_PLAN_ID
            print("[ORCHESTRATOR] resume requested by human")
            
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                body = json.loads(post_data)
                APPROVED_STEP_ID = body.get("step_id", None)
                APPROVED_PLAN_ID = body.get("approve_plan_id", None)
                
                if APPROVED_STEP_ID:
                    print(f"[ORCHESTRATOR] Approved Step ID: {APPROVED_STEP_ID}")
                if APPROVED_PLAN_ID:
                    print(f"[ORCHESTRATOR] Approved Plan ID: {APPROVED_PLAN_ID}")
            except:
                pass
                
            RESUME_REQUESTED = True
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

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
                    # Convert selected plan to execution_plan format and set as CURRENT_PLAN
                    CURRENT_PLAN = {
                        "type": "execution_plan",
                        "goal": LAST_PLAN_SET.get("goal"),
                        "plan_id": APPROVED_PLAN_ID,
                        "assumptions": selected_plan.get("assumptions", []),
                        "steps": selected_plan.get("steps", []),
                        "confidence": selected_plan.get("confidence"),
                        "source_plan_set": True
                    }
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
            # Phase 4.1: Step Approval Protocol
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
