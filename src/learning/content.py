"""Versioned, authored teaching scenarios. Requires educator review before a study.

These are hypothetical examples, not labels inferred from wallet losses.
"""

BANK_VERSION = "homie-defi-v1"
SKILLS = [
    {"id": 0, "name": "Wallet permissions", "lesson": "A wallet connection exposes your public address; a signature or transaction can authorize additional actions. Inspect the program, accounts, requested permissions, and asset changes before signing. Never share a seed phrase. Disconnecting a website does not necessarily revoke permissions already granted on-chain."},
    {"id": 1, "name": "Token risk", "lesson": "A token name, trending chart, or low price does not establish legitimacy. Inspect the exact mint address, relevant mint and freeze authorities, distribution, and liquidity. Each is evidence to investigate, not a guarantee. A falling price alone does not prove a rug pull."},
    {"id": 2, "name": "Liquidity", "lesson": "Liquidity determines how easily a trade can execute. A large trade relative to available liquidity can move the price substantially. A high quoted yield does not remove withdrawal, market, or smart-contract risk. Inspect pool depth and conditions before trading or depositing."},
    {"id": 3, "name": "Slippage", "lesson": "Price impact is the price change caused by your trade against available liquidity. Slippage is the difference between expected and executed terms. Slippage tolerance sets an acceptable execution bound; raising it can permit a worse price. It is not a profit target or a guarantee that your trade will execute."},
    {"id": 4, "name": "Transaction safety", "lesson": "Check the exact destination, program, amounts, network, and expected asset changes. Simulation can reveal problems but is not a safety guarantee. A failed transaction can still incur a fee. Keep private keys and recovery phrases private, even when a website claims to offer support."},
]


def _q(qid, skill, phase, prompt, options, answer, explanation):
    return {"id": qid, "skill_id": skill, "phase": phase, "prompt": prompt,
            "options": options, "answer": answer, "explanation": explanation}


QUESTIONS = [
    _q("permissions-pre", 0, "diagnostic", "A site asks you to connect a wallet, then immediately requests a signature. What should you do?", ["Sign because connecting made the site trustworthy", "Inspect what the signature authorizes before approving", "Send the site your recovery phrase"], 1, "Connecting a wallet does not establish trust or make every subsequent signature safe."),
    _q("token-pre", 1, "diagnostic", "Two tokens have the same name and logo. What best identifies the one you intended to use?", ["Its position in a trending list", "The token with the lower price", "Its exact mint address checked against a trusted source"], 2, "Names and logos can be copied. A mint address identifies the particular token."),
    _q("liquidity-pre", 2, "diagnostic", "You want to trade a large amount in a pool with very little liquidity. What is the main execution concern?", ["Large price impact", "Guaranteed profit", "The wallet becomes public for the first time"], 0, "A large trade relative to pool depth can substantially change the execution price."),
    _q("slippage-pre", 3, "diagnostic", "A swap fails at a 1% slippage tolerance. Increasing it to 20% primarily does what?", ["Guarantees a 20% return", "Permits a much larger difference from expected execution terms", "Removes all transaction fees"], 1, "A higher tolerance may allow execution on worse terms; it does not promise a return."),
    _q("safety-pre", 4, "diagnostic", "A support account asks for your recovery phrase to fix a failed swap. What should you do?", ["Share it only in a private message", "Share half now and half later", "Refuse and use an independently verified support channel"], 2, "A recovery phrase controls the wallet. Support does not need it to investigate a transaction."),
    _q("permissions-practice-a", 0, "practice", "You disconnected a website. Can you assume every on-chain permission previously granted is revoked?", ["Yes, always", "No; inspect and revoke relevant permissions separately", "Only if you close your browser"], 1, "Disconnecting a browser session and revoking an on-chain permission are different actions."),
    _q("permissions-practice-b", 0, "practice", "A transaction preview contains a program you do not recognize. What is the best next step?", ["Investigate the program and requested changes", "Approve if the interface looks professional", "Assume a small fee proves safety"], 0, "The appearance of a site and transaction fee do not validate a program's behavior."),
    _q("token-practice-a", 1, "practice", "A token falls 80% in price. Which conclusion is justified from the price change alone?", ["Every holder is inexperienced", "The developers definitely stole liquidity", "The price fell severely; the cause needs more evidence"], 2, "A large price decline is not sufficient evidence of a rug pull or of a holder's knowledge."),
    _q("token-practice-b", 1, "practice", "Why inspect a token's freeze authority?", ["It can be relevant to whether token accounts may be frozen", "It fixes the token's market price", "It guarantees that the token is fraudulent"], 0, "Authority settings affect capabilities. Their existence alone is not proof of fraud."),
    _q("liquidity-practice-a", 2, "practice", "A pool advertises high yield. Which additional check is useful?", ["Only the color of its website", "Liquidity, withdrawal terms, and protocol risks", "Whether its token name contains AI"], 1, "A yield figure does not capture market, withdrawal, or contract risks."),
    _q("liquidity-practice-b", 2, "practice", "Two otherwise similar pools quote the same initial price. Your trade is large. What else matters?", ["Only the pool name", "Nothing; execution must be identical", "Available depth and expected price impact"], 2, "Identical initial prices do not imply identical execution for a large order."),
    _q("slippage-practice-a", 3, "practice", "Your own large swap moves the pool price. What is this called?", ["Price impact", "A recovery phrase", "Guaranteed sandwich detection"], 0, "Price impact describes the effect of the trade itself on price."),
    _q("slippage-practice-b", 3, "practice", "A quote says 100 tokens and minimum received says 98. What does the minimum describe?", ["A promise of profit", "An execution bound encoded for that swap", "The number of validators"], 1, "The minimum output constrains acceptable execution; it does not guarantee a fill."),
    _q("safety-practice-a", 4, "practice", "A transaction simulation succeeds. What can you conclude?", ["The transaction can never be harmful", "The destination is definitely correct", "The simulation passed under its conditions; other checks still matter"], 2, "Simulation success is useful evidence, not a comprehensive guarantee of safety."),
    _q("safety-practice-b", 4, "practice", "A Solana transaction fails. What may still happen?", ["A transaction fee may still be charged", "The recovery phrase changes", "Every intended asset transfer must complete"], 0, "A failed transaction may incur fees even though its intended state changes do not complete."),
    _q("permissions-post", 0, "assessment", "A familiar site requests a new transaction signature. Which rule applies?", ["Past use makes all future requests safe", "Review the specific authorization and asset changes each time", "Only inspect it if the fee is high"], 1, "Every authorization should be reviewed on its own terms."),
    _q("token-post", 1, "assessment", "Which is the strongest approach to investigating an unfamiliar token?", ["Trust a copied logo", "Trust recent price growth", "Combine mint verification, authority checks, distribution, and liquidity evidence"], 2, "Several independent checks provide more context than branding or recent price movement."),
    _q("liquidity-post", 2, "assessment", "A small purchase executed well yesterday. Why might a much larger purchase execute poorly today?", ["Trade size and current pool liquidity can differ", "Small purchases guarantee all future prices", "Wallet connections set pool depth"], 0, "Execution depends on current liquidity and order size, not only a previous trade."),
    _q("slippage-post", 3, "assessment", "Why should a trader inspect the minimum received before approving a swap?", ["It reveals the recovery phrase", "It shows the lower output bound they are authorizing", "It guarantees the quoted market price will stay fixed"], 1, "Minimum received helps the trader understand the accepted execution bound."),
    _q("safety-post", 4, "assessment", "Before sending tokens to a new address, which check is most directly useful?", ["Whether the recipient's avatar looks familiar", "Whether someone promises a refund", "Verify the exact destination and intended network and asset"], 2, "Address, network, and asset verification reduce avoidable destination mistakes."),
]
BY_ID = {q["id"]: q for q in QUESTIONS}


def public_question(question):
    return {k: v for k, v in question.items() if k not in {"answer", "explanation"}}
