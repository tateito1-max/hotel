"""判定・遭遇係数の検証シミュレーション。

検証したいこと:
1. 比率式 成功率 = clamp(50% + 50%*(R-1), 5%, 95%), R = パーティ集計能力/課題値 の手触り
2. 人数を増やしたときのカーブ:
   - 遭遇頻度は緩やかに増える（自動解決なので頻度増は許容。方針確定済み）
   - 主(ボス)クラス遭遇率は人数で上がり、これが大所帯の実リスクになる
   - 報酬は頭割り分配なので、人数過剰は利益率を直撃する
   → 「依頼ごとに損益と生存率のバランスが取れた適正人数が現れる」ことを確認する
"""
import random
from statistics import mean

# ---- 判定式 ----
def check_success(power, difficulty):
    r = power / difficulty
    return max(0.05, min(0.95, 0.5 + 0.5 * (r - 1.0)))

# ---- 遭遇係数（たたき台） ----
SIZE_FREQ = 0.05        # 遭遇頻度の人数係数: ×(1 + 0.05*(n-4))
SIZE_ELITE = 0.015      # 主クラス遭遇率: 5% + 1.5%*(n-4)、上限35%
ELITE_BASE = 0.05
ELITE_CAP = 0.35
ELITE_POWER = 2.5       # 主クラスの敵戦力倍率
SCOUT_CAP = 0.6         # 斥候による遭遇軽減の上限

# ---- 経済（balance_sim.py と同じ相場） ----
SHARE_RATE = 0.40
FOOD_PER_DAY = 2
BASE_WAGE = 5
PENALTY_RATE = 0.4
REVIVE = 600

# メンバー1人の課題能力 = 能力値 + スキルLv*2 → 序盤の平均像を13とする
MEMBER_POWER = 13
SCOUT_SKILL_LV = 4      # 斥候1人が同行する想定（軽減 = 0.06*Lv, 上限0.6）

# 依頼: (固定報酬, 回収品, 日数, 戦闘席数, 戦闘課題値, 作業課題値(加算型), 経路危険度, 敵戦力)
QUESTS = {
    "E討伐(安全・席4)": (220,  40, 2, 4, 20, None, 0.10, 15),
    "D討伐(並・席4)":   (420,  90, 3, 4, 33, None, 0.20, 25),
    "C採掘(並・席4)":   (650, 550, 5, 4, 26, 42,   0.20, 24),
    "C討伐(危険・席6)": (850, 170, 4, 6, 52, None, 0.35, 40),
}

def run_quest(rng, name, n):
    reward, loot, days, seats, combat_req, work_req, route, enemy = QUESTS[name]
    combat_power = min(n, seats) * MEMBER_POWER          # 席数型
    work_power = n * MEMBER_POWER * 0.6                  # 加算型(非戦闘員換算で0.6掛け)
    mitigation = min(SCOUT_CAP, 0.06 * SCOUT_SKILL_LV)
    freq = route * (1 + SIZE_FREQ * (n - 4)) * (1 - mitigation)
    elite_p = min(ELITE_CAP, ELITE_BASE + SIZE_ELITE * (n - 4))
    deaths, injuries, encounters = 0, 0, 0
    aborted = False
    for _ in range(days):
        if rng.random() < freq:
            encounters += 1
            e_power = enemy * (ELITE_POWER if rng.random() < elite_p else 1.0)
            win = rng.random() < check_success(combat_power, e_power)
            if win:
                if rng.random() < 0.10:
                    injuries += 1
            else:  # 敗走: 負傷者・死者が出て任務中断
                injuries += max(1, n // 6)
                if rng.random() < 0.40:
                    deaths += 1
                aborted = True
                break
    if aborted:
        success = False
    else:
        req = combat_req if work_req is None else work_req
        power = combat_power if work_req is None else work_power
        success = rng.random() < check_success(power, req)
    total = reward + loot
    if success:
        income = total - int(total * SHARE_RATE)
    else:
        income = -int(reward * PENALTY_RATE)
    cost = n * FOOD_PER_DAY * days + n * BASE_WAGE * days + deaths * REVIVE
    return success, income - cost, deaths, encounters

def stats(name, n, trials=4000):
    rng = random.Random(42)
    res = [run_quest(rng, name, n) for _ in range(trials)]
    sr = mean(1 if r[0] else 0 for r in res)
    profit = mean(r[1] for r in res)
    deaths = sum(r[2] for r in res) / trials * 100
    enc = mean(r[3] for r in res)
    return sr, profit, deaths, enc

for name in QUESTS:
    print(f"--- {name} ---")
    print("人数 | 成功率 | 期待利益/件 | 死者/100件 | 遭遇/件")
    for n in (2, 3, 4, 5, 6, 8, 10, 14, 20):
        sr, profit, deaths, enc = stats(name, n)
        print(f"{n:4d} | {sr:5.0%} | {profit:8.0f}G | {deaths:7.1f} | {enc:5.2f}")
    print()
