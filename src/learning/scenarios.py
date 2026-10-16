"""Authored transaction simulations and explicit draft scoring rubrics."""
from copy import deepcopy

LEGACY_VERSION = "homie-simulator-v1"
VERSION = "homie-simulator-v2"
BEHAVIOR_COLUMNS = ["inspection_count", "hint_count", "revision_count", "duration_ms"]


def case(sid, skill, phase, title, brief, evidence, action, reason, reasons, feedback, setting=None):
    return {"id": sid, "skill_id": skill, "phase": phase, "title": title, "brief": brief,
            "evidence": [{"id": f"card-{i}", "title": name, "body": body} for i, (name, body) in enumerate(evidence)],
            "actions": ["approve", "reject", "modify"], "reasons": reasons, "setting": setting,
            "rubric": {"action": action, "reason": reason}, "feedback": feedback,
            "hint": "Inspect the transaction details and the constraints in your task. Choose a decision and a reason supported by that evidence."}


LEGACY_SCENARIOS = [
    case("permission-practice", 0, "practice", "An oversized permission", "You intend to authorize a one-time transfer of 5 USDC. Review a site's proposed permission.",
         [("Requested permission", "The proposed delegate allowance is 5,000 USDC, not the 5 USDC your task requires."), ("Program & session", "Connecting a website does not revoke existing permissions or validate a new delegate."), ("Available controls", "This simulated request cannot be edited. You can reject it and obtain a correctly scoped request.")],
         "reject", 0, ["The requested allowance exceeds the intended authorization", "Every delegate permission is necessarily fraudulent", "A professional website guarantees safety"], "Reject this oversized request and obtain a scoped authorization. Delegation itself is not proof of fraud."),
    case("token-practice", 1, "practice", "A familiar name, a different mint", "Your task is to acquire the token at verified mint DEMO-MINT-A. Inspect the offered token.",
         [("Token identity", "The offered token has a matching logo but mint DEMO-MINT-B. The exact mint required by your task is DEMO-MINT-A."), ("Authority settings", "Mint and freeze authorities are listed. Their existence is relevant evidence, not proof of a scam."), ("Task constraints", "The intended mint is required. This request offers no way to change tokens.")],
         "reject", 1, ["A matching logo identifies the token", "The offered mint does not match the task's verified mint", "Any token with a freeze authority is fraudulent"], "Reject the mismatched token request. Names and logos are insufficient identifiers."),
    case("liquidity-practice", 2, "practice", "Size the trade to the pool", "You may reduce this order. Your task allows at most 2% quoted price impact.",
         [("Pool depth", "A 1,000 USDC order quotes 12% price impact. In this authored simulation, orders of 100 USDC or less quote 1% impact."), ("Execution preview", "The current order is 1,000 USDC. Reducing size changes the preview under the fixed scenario rule."), ("Task constraints", "A smaller order is acceptable; reject-only decisions do not complete the allowed purchase.")],
         "modify", 2, ["A past small purchase guarantees today's execution", "Higher impact guarantees a higher return", "Reduce size to meet the stated impact constraint"], "Reduce the order to at most 100 USDC before proceeding. The simplified depth rule is a teaching model, not live pricing.", {"name": "Order size (USDC)", "key": "order_size", "initial": 1000, "min": 1, "max": 1000, "safe_max": 100}),
    case("slippage-practice", 3, "practice", "Set the execution bound", "The quote is 100 tokens. Your task permits at most a 1% output shortfall; the route is otherwise acceptable.",
         [("Quoted output", "The quote is 100 tokens. A 20% tolerance permits a minimum output of 80 tokens."), ("Execution control", "The tolerance is editable. In this simulation, minimum output = 100 × (1 − tolerance / 100)."), ("Task constraints", "Set a tolerance between 0.1% and 1%. Changing the bound does not guarantee execution.")],
         "modify", 0, ["Tighten the minimum-output bound to fit the task", "20% tolerance guarantees a 20% profit", "Simulation removes price risk"], "Use a tolerance no greater than 1% to respect the stated bound. Execution may still fail.", {"name": "Slippage tolerance (%)", "key": "slippage", "initial": 20, "min": 0.1, "max": 25, "safe_max": 1}),
    case("safety-practice", 4, "practice", "A destination worth checking", "Your task is a transfer to DEMO-RECIPIENT-A. Evaluate this request.",
         [("Destination", "The preview sends to DEMO-RECIPIENT-B, while your task specifies DEMO-RECIPIENT-A."), ("Simulation", "The simulation succeeds. This indicates execution under simulated conditions, not that the destination meets your intent."), ("Available controls", "This request's destination cannot be edited. Obtain a new request if you reject it.")],
         "reject", 1, ["Simulation success proves the destination is intended", "The destination differs from the intended recipient", "Any successful simulation is an attack"], "Reject the mismatched destination, even though simulation succeeds."),
    case("permission-transfer", 0, "transfer", "A scoped authorization", "Complete a one-time authorization of exactly 3 USDC for the verified task program. All stated constraints must match.",
         [("Permission details", "The delegate allowance is exactly 3 USDC for DEMO-VERIFIED-PROGRAM."), ("Verified task", "The task specifies 3 USDC and DEMO-VERIFIED-PROGRAM. The reviewed request matches both."), ("Scope", "This is a hypothetical reviewed request, not a claim that all real-world risk is eliminated.")],
         "approve", 2, ["All permissions are unsafe, so rejecting is always correct", "Low fees establish trust", "The reviewed allowance and program match the stated task"], "Within this bounded scenario, approving meets the reviewed authorization. Blanket rejection does not demonstrate the requested distinction."),
    case("token-transfer", 1, "transfer", "Identity over branding", "Acquire token DEMO-MINT-C from the verified task source. Do not substitute a token based on branding.",
         [("Mint", "The request offers DEMO-MINT-C, matching the task's verified identifier."), ("Branding", "The display name recently changed. Names can change independently of mint identity."), ("Reviewed conditions", "The hypothetical task's reviewed authority and liquidity conditions match the request.")],
         "approve", 0, ["The exact mint and reviewed conditions match the intended task", "A changed display name necessarily means theft", "Recent price growth proves legitimacy"], "The mint and reviewed conditions match. A display-name change alone does not establish a mismatch."),
    case("liquidity-transfer", 2, "transfer", "A different pool, a different bound", "Make a purchase with no more than 3% quoted impact. A smaller order is permitted.",
         [("New pool", "An 800 USDC order quotes 9% impact; orders of 200 USDC or less quote 2% under this scenario's fixed rule."), ("Current preview", "Current order: 800 USDC. Adjust the editable order size."), ("Task", "Complete an allowed smaller purchase within the 3% constraint.")],
         "modify", 1, ["Approve because the initial token price is attractive", "Reduce the order to satisfy the impact constraint", "Impact is unrelated to trade size"], "Reduce the order to at most 200 USDC. This transfers the depth concept to new values.", {"name": "Order size (USDC)", "key": "order_size", "initial": 800, "min": 1, "max": 800, "safe_max": 200}),
    case("slippage-transfer", 3, "transfer", "Read a new minimum", "A 250-token quote must authorize at least 245 tokens received. The route otherwise meets the task.",
         [("Quote & minimum", "The current 10% tolerance permits 225 tokens. A 2% tolerance permits 245 tokens."), ("Controls", "Minimum output = 250 × (1 − tolerance / 100). The tolerance is editable."), ("Constraint", "Use a tolerance between 0.1% and 2%. No setting promises a successful fill.")],
         "modify", 2, ["Approve because 225 is close enough", "Raise tolerance to increase guaranteed output", "Set a bound that authorizes at least 245 tokens"], "A tolerance of at most 2% satisfies the stated 245-token minimum.", {"name": "Slippage tolerance (%)", "key": "slippage", "initial": 10, "min": 0.1, "max": 25, "safe_max": 2}),
    case("safety-transfer", 4, "transfer", "A reviewed transfer", "Send exactly 2 demo tokens to DEMO-RECIPIENT-D on the specified demo network.",
         [("Destination & network", "The request specifies DEMO-RECIPIENT-D on the required demo network."), ("Asset changes", "The preview transfers exactly 2 of the intended demo tokens plus the disclosed fee."), ("Simulation", "Simulation succeeds. In addition, the reviewed destination, amount, and asset match the task.")],
         "approve", 0, ["The reviewed destination, amount, network, and asset match the task", "Simulation success alone proves all transfers safe", "Rejecting every request completes every task"], "The reviewed request meets this scenario's constraints. Simulation is one check, not the sole reason."),
]

# Separate uncoached diagnostic items establish a history before practice starts.
# These are draft teaching rubrics, not expert-validated assessment instruments.
DIAGNOSTICS = [
    case("permission-diagnostic", 0, "diagnostic", "Check an authorization scope", "Authorize exactly 8 demo units for DEMO-PROGRAM-P. Check the proposed request.",
         [("Allowance", "The allowance is exactly 8 demo units."), ("Program", "The delegate is DEMO-PROGRAM-P, the task's reviewed program."), ("Task", "Within this hypothetical task, the program and allowance are the required checks and both match.")],
         "approve", 1, ["All delegated allowances must be rejected", "The reviewed program and allowance both match the task", "The website appearance proves the program is correct"], "The reviewed scope and program match this bounded authorization task."),
    case("token-diagnostic", 1, "diagnostic", "Identify the requested asset", "Acquire the token with verified identifier DEMO-ASSET-K. This request cannot change assets.",
         [("Offered asset", "The offered mint is DEMO-ASSET-L."), ("Display", "Its ticker and logo are the same as those shown for DEMO-ASSET-K."), ("Task", "Your verified source specifies DEMO-ASSET-K, not DEMO-ASSET-L.")],
         "reject", 2, ["The ticker proves these are the same asset", "All unfamiliar tokens must be fraudulent", "The offered identifier differs from the required identifier"], "Reject the mismatched identifier; matching branding does not meet the task."),
    case("liquidity-diagnostic", 2, "diagnostic", "Check a locked order", "Complete a purchase only if quoted impact is at most 4%. The order size cannot be edited in this request.",
         [("Pool preview", "This 600-unit order quotes 11% impact under the authored pool rule."), ("Controls", "This request offers no size adjustment. Rejection lets you obtain a different order."), ("Task", "The maximum allowed quoted impact is 4%.")],
         "reject", 0, ["The locked order exceeds the task's impact limit", "High impact guarantees profit", "A successful small trade elsewhere meets this order's limit"], "Reject this locked order because its quoted impact exceeds the allowed limit."),
    case("slippage-diagnostic", 3, "diagnostic", "Check an output floor", "Your task requires an authorized minimum of at least 198 tokens from a 200-token quote. The route is otherwise reviewed.",
         [("Output floor", "The request authorizes at least 199 tokens."), ("Execution", "The request may fail if the output floor cannot be met; this floor is not a promise of execution."), ("Task", "The required authorized floor is 198 tokens or higher.")],
         "approve", 1, ["Any output floor guarantees a successful fill", "The authorized floor meets the task's minimum", "A larger tolerance always guarantees more tokens"], "The authorized minimum of 199 meets the task's 198-token floor without promising a fill."),
    case("safety-diagnostic", 4, "diagnostic", "Check the transfer network", "Send 4 demo tokens to DEMO-RECIPIENT-Q on DEMO-NETWORK-1. This request cannot be edited.",
         [("Destination", "The recipient is DEMO-RECIPIENT-Q and the amount is 4 demo tokens."), ("Network", "The request uses DEMO-NETWORK-2, not DEMO-NETWORK-1."), ("Simulation", "The simulation succeeds on DEMO-NETWORK-2.")],
         "reject", 2, ["Simulation success alone satisfies the task", "Matching the amount makes the network irrelevant", "The network differs from the task's required network"], "Reject the request: recipient and amount matching do not resolve a network mismatch."),
]

EXTRA_PRACTICE = [
    case("permission-practice-2", 0, "practice", "Check who receives the permission", "Authorize a one-time 6-unit allowance for DEMO-TASK-PROGRAM. Review this noneditable request.",
         [("Allowance", "The proposed allowance is exactly 6 units."), ("Delegate", "The delegate is DEMO-OTHER-PROGRAM, not DEMO-TASK-PROGRAM."), ("Available controls", "The program cannot be edited. Reject to request the intended authorization.")],
         "reject", 1, ["Matching the amount alone satisfies an authorization", "The delegate program differs from the intended program", "Every six-unit allowance is fraudulent"], "Check both allowance and delegate. A correctly sized permission to the wrong program does not meet the task."),
    case("token-practice-2", 1, "practice", "A new ticker, the intended mint", "Acquire DEMO-MINT-R from your verified task source. Evaluate the reviewed request.",
         [("Identifier", "The offered mint is DEMO-MINT-R."), ("Display", "The ticker changed yesterday, while the mint stayed DEMO-MINT-R."), ("Reviewed conditions", "The hypothetical authority and liquidity conditions meet the stated task.")],
         "approve", 2, ["A ticker change proves the asset is a substitute", "A price increase verifies a mint", "The exact mint and reviewed conditions match despite the ticker change"], "Use the verified mint identifier. A changed ticker alone does not make this a different mint."),
    case("liquidity-practice-2", 2, "practice", "Resize a second pool order", "Buy within a 2% quoted-impact limit. You may reduce the order size.",
         [("Depth rule", "Under this authored pool rule, orders of 60 USDC or less quote 1.5% impact; larger orders quote 7%."), ("Current order", "The editable order is 400 USDC and quotes 7% impact."), ("Task", "Complete a smaller allowed purchase rather than approving the oversized order.")],
         "modify", 0, ["Reduce size so the pool preview meets the impact limit", "The earlier pool's size limit applies to every pool", "The current quote guarantees a return"], "Reduce this order to at most 60 USDC. Pool-specific constraints must be read again.",
         {"name": "Order size (USDC)", "key": "order_size", "initial": 400, "min": 1, "max": 400, "safe_max": 60}),
    case("slippage-practice-2", 3, "practice", "Derive the authorized minimum", "A 400-token quote must authorize at least 398 tokens. The route otherwise meets the task.",
         [("Quote", "The quote is 400 tokens. The initial 5% tolerance permits a minimum of 380 tokens."), ("Control rule", "Minimum output = 400 × (1 − tolerance / 100). Tolerance is editable."), ("Constraint", "Use a tolerance between 0.1% and 0.5%. A tighter bound can cause the trade to fail.")],
         "modify", 1, ["A 5% tolerance guarantees 400 tokens", "Tighten the bound to authorize at least 398 tokens", "The earlier task's tolerance fits every quote"], "Set tolerance to at most 0.5% for a minimum output of at least 398 tokens.",
         {"name": "Slippage tolerance (%)", "key": "slippage", "initial": 5, "min": 0.1, "max": 25, "safe_max": 0.5}),
    case("safety-practice-2", 4, "practice", "Check which asset leaves", "Send 7 units of DEMO-ASSET-S to DEMO-RECIPIENT-S on DEMO-NETWORK-S. Review the noneditable request.",
         [("Destination and network", "DEMO-RECIPIENT-S and DEMO-NETWORK-S match the task."), ("Asset changes", "The preview transfers 7 units of DEMO-ASSET-T plus the disclosed fee."), ("Simulation", "Simulation succeeds, but does not check whether DEMO-ASSET-T was the intended asset.")],
         "reject", 0, ["The asset differs from the intended transfer asset", "A matching recipient makes the asset irrelevant", "Simulation success alone verifies intent"], "Check the asset as well as recipient, amount and network. Reject the substituted asset."),
]

SCENARIOS = DIAGNOSTICS + LEGACY_SCENARIOS + EXTRA_PRACTICE
BANKS = {LEGACY_VERSION: LEGACY_SCENARIOS, VERSION: SCENARIOS}
# Preview values belong to each authored case, never to frontend ID heuristics.
for sid, values in {
    "liquidity-practice": {"size_limit": 100, "low_impact": 1, "high_impact": 12},
    "liquidity-transfer": {"size_limit": 200, "low_impact": 2, "high_impact": 9},
    "liquidity-practice-2": {"size_limit": 60, "low_impact": 1.5, "high_impact": 7},
    "slippage-practice": {"quote": 100},
    "slippage-transfer": {"quote": 250},
    "slippage-practice-2": {"quote": 400},
}.items():
    next(s for s in SCENARIOS if s["id"] == sid)["setting"]["preview"] = values
BY_ID = {s["id"]: s for s in SCENARIOS}


def public_scenario(s):
    result = deepcopy({k: v for k, v in s.items() if k not in {"rubric", "feedback", "hint"}})
    # Evidence content is returned only after an inspection action.
    result["evidence"] = [{"id": e["id"], "title": e["title"]} for e in s["evidence"]]
    if result["setting"]:
        result["setting"].pop("safe_max")
    return result


def score(s, action, reason, value):
    setting_ok = not s["setting"] or (value is not None and s["setting"]["min"] <= value <= s["setting"]["safe_max"])
    action_ok = action == s["rubric"]["action"]
    reason_ok = reason == s["rubric"]["reason"]
    return {"correct": int(action_ok and reason_ok and setting_ok), "action_ok": action_ok,
            "reason_ok": reason_ok, "setting_ok": setting_ok}
