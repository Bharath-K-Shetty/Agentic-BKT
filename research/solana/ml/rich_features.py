"""Ordinary richer prefix summaries; no new architecture or ownership inference."""
from collections import defaultdict
import numpy as np
from prefix_baseline import prefix_features


def gini(values):
    values = np.sort(np.asarray(values, dtype=float))
    if len(values) == 0 or values.sum() <= 0:
        return 0.0
    n = len(values)
    return float((2 * np.arange(1, n+1) - n - 1).dot(values) / (n * values.sum()))


def enriched_features(events, horizon=300):
    t0, base = prefix_features(events, horizon)
    rows = [e for e in events if t0 <= int(e['timestamp']) <= t0 + horizon]
    rows.sort(key=lambda e: (int(e['block_slot']), int(e['block_index']), e['signature']))
    swaps = [e for e in rows if 'swap' in e['type']]
    balances = defaultdict(float)
    buy_amount, sell_amount, buy_count, sell_count = (defaultdict(float) for _ in range(4))
    first_buy, mint_participants, parent = {}, set(), {}

    def find(w):
        parent.setdefault(w, w)
        while parent[w] != w:
            parent[w] = parent[parent[w]]
            w = parent[w]
        return w

    for e in rows:
        active = []
        for w, amount in e.get('trader_map', {}).items():
            amount = float(amount)
            balances[w] += amount
            find(w)
            if 'mint' in e['type'] and amount != 0:
                mint_participants.add(w)
            if 'swap' in e['type']:
                if amount > 0:
                    buy_amount[w] += amount; buy_count[w] += 1
                    first_buy.setdefault(w, int(e['timestamp']) - t0)
                elif amount < 0:
                    sell_amount[w] += -amount; sell_count[w] += 1
                if amount != 0:
                    active.append(w)
        if len(active) > 1:
            for w in active[1:]:
                parent[find(w)] = find(active[0])
    positive = {w: max(v, 0) for w, v in balances.items()}
    total = sum(positive.values())
    shares = np.array(list(positive.values())) / total
    f = dict(base)
    f['rich_holding_gini'] = gini(shares)
    f['rich_holding_entropy'] = float(-(shares[shares > 0] * np.log(shares[shares > 0])).sum())
    f['rich_negative_balance_fraction'] = sum(v < -1e-6 for v in balances.values()) / len(balances)
    for k in (3, 5, 20, 50):
        f[f'rich_top{k}_holding_share'] = float(np.sort(shares)[-k:].sum())
    for q in (.25, .5, .75, .95, .99):
        f[f'rich_holding_q{int(q*100)}'] = float(np.quantile(shares, q))
    buyers, sellers = set(buy_amount), set(sell_amount)
    f['rich_unique_buyers'] = len(buyers)
    f['rich_unique_sellers'] = len(sellers)
    f['rich_buy_sell_wallet_fraction'] = len(buyers & sellers) / max(len(buyers | sellers), 1)
    f['rich_repeat_buyer_fraction'] = sum(v > 1 for v in buy_count.values()) / max(len(buyers), 1)
    f['rich_repeat_seller_fraction'] = sum(v > 1 for v in sell_count.values()) / max(len(sellers), 1)
    f['rich_total_sold_to_bought'] = sum(sell_amount.values()) / max(sum(buy_amount.values()), 1e-12)
    f['rich_mint_participant_share'] = sum(positive.get(w, 0) for w in mint_participants) / total
    # Mint transaction participation does not prove deployer or insider identity.
    cohorts = {f'first_{s}s': {w for w, t in first_buy.items() if t <= s} for s in (0, 1, 5, 10, 30)}
    ordered_buyers = sorted(first_buy, key=lambda w: (first_buy[w], w))
    # Equal timestamp buyer order is ambiguous: include entire timestamp cohort.
    for k in (5, 10, 20):
        boundary = first_buy[ordered_buyers[min(k, len(ordered_buyers))-1]] if ordered_buyers else -1
        cohorts[f'first_{k}_buyers_with_ties'] = {w for w, t in first_buy.items() if t <= boundary}
    for name, wallets in cohorts.items():
        f[f'rich_{name}_count'] = len(wallets)
        f[f'rich_{name}_holding_share'] = sum(positive.get(w, 0) for w in wallets) / total
        bought = sum(buy_amount[w] for w in wallets)
        f[f'rich_{name}_sold_to_bought'] = sum(sell_amount[w] for w in wallets) / max(bought, 1e-12)
    component = defaultdict(float)
    for w, amount in positive.items():
        component[find(w)] += amount / total
    cs = np.array(list(component.values()))
    f['rich_component_gini'] = gini(cs)
    for k in (3, 5, 10, 20):
        f[f'rich_top{k}_component_share'] = float(np.sort(cs)[-k:].sum())
    volumes = np.array([abs(float(e['sol_amount'])) for e in swaps])
    fees = np.array([float(e['fee_amount']) for e in swaps])
    prices = np.array([abs(float(e['price'])) for e in swaps])
    times = np.array([int(e['timestamp']) - t0 for e in swaps])
    for name, values in [('sol_volume', volumes), ('fee', fees)]:
        f[f'rich_{name}_std'] = float(values.std())
        for q in (.25, .5, .75, .95, .99):
            f[f'rich_{name}_q{int(q*100)}'] = float(np.quantile(values, q))
    f['rich_volume_top5_fraction'] = float(np.sort(volumes)[-5:].sum() / max(volumes.sum(), 1e-12))
    f['rich_prefix_max_drawdown'] = float((1 - prices / np.maximum.accumulate(prices)).max())
    f['rich_log_price_to_max'] = float(np.log(prices[-1] / prices.max()))
    f['rich_log_price_to_min'] = float(np.log(prices[-1] / prices.min()))
    f['rich_abs_log_price_changes'] = float(np.abs(np.diff(np.log(prices))).sum())
    seconds, counts = np.unique(times, return_counts=True)
    f['rich_max_swaps_per_second'] = int(counts.max())
    f['rich_same_second_swap_fraction'] = float(counts[counts > 1].sum() / len(swaps))
    f['rich_unique_swap_slots'] = len({e['block_slot'] for e in swaps})
    f['rich_last_swap_age_fraction'] = float((horizon - times[-1]) / horizon)
    # Six fixed bins; no lifespan normalization or future event boundaries.
    for b in range(6):
        mask = np.minimum((times * 6 / horizon).astype(int), 5) == b
        selected = [e for e, yes in zip(swaps, mask) if yes]
        f[f'rich_bin{b}_swap_count'] = len(selected)
        f[f'rich_bin{b}_sol_volume'] = float(volumes[mask].sum())
        f[f'rich_bin{b}_log_return'] = float(np.log(prices[mask][-1] / prices[mask][0])) if mask.any() else 0.0
        bought = sum(float(v) > 0 for e in selected for v in e.get('trader_map', {}).values())
        sold = sum(float(v) < 0 for e in selected for v in e.get('trader_map', {}).values())
        f[f'rich_bin{b}_sell_fraction'] = sold / max(bought + sold, 1)
    if not np.isfinite(list(f.values())).all():
        raise ValueError('Nonfinite enriched features')
    return t0, f
