"""序盤〜中盤の経済バランス机上シミュレーション。

モデル（仕様書の確定事項に準拠）:
- 1ターン=1日。依頼は所要日数の後に成否判定。
- 収入: 依頼の固定報酬 + 回収品換金。分配率で参加者に頭割り（ギルドは残り）。
- 支出: 基本給(全員・毎日・死亡中も) + 食料(派遣者×日数) + 違約金 + 蘇生費。
"""
import random

# ---- たたき台の数値 ----
INIT_GOLD = 1500
SHARE_RATE = 0.40          # 報酬のうち冒険者分配に回す割合
FOOD_PER_DAY = 2           # 食料コスト/人/日
BASE_WAGE = 5              # E級相当の基本給/人/日
PENALTY_RATE = 0.4         # 違約金 = 固定報酬の40%
REVIVE_COST = {"健全": 300, "損傷": 600, "白骨": 1200}

# 依頼テンプレ: (固定報酬, 回収品期待値, 所要日数, 適正人数, 適正時成功率)
QUESTS = {
    "E討伐":   (220,  40, 2, 3, 0.85),
    "E採取":   (150, 110, 3, 4, 0.90),
    "D討伐":   (420,  90, 3, 4, 0.80),
    "D遺跡":   (500, 210, 4, 5, 0.75),
    "C討伐":   (850, 170, 4, 6, 0.75),
    "C採掘":   (650, 550, 5, 8, 0.85),
}

def run(seed, days=60, log=False):
    rng = random.Random(seed)
    gold = INIT_GOLD
    roster = 4                      # 初期メンバー
    quest_queue = ["E討伐", "E採取", "E討伐", "E採取", "D討伐",
                   "D遺跡", "D討伐", "D遺跡", "C採掘", "C討伐"] * 3
    qi = 0
    busy_until = 0
    active = None
    deaths = 0
    min_gold = gold
    for day in range(1, days + 1):
        # 派遣開始
        if active is None and qi < len(quest_queue):
            name = quest_queue[qi]; qi += 1
            reward, loot, dur, party, p = QUESTS[name]
            party = min(party, roster)
            active = (name, reward, loot, dur, party, p)
            busy_until = day + dur - 1
        # 支出: 基本給 + 食料
        gold -= roster * BASE_WAGE
        if active:
            gold -= active[4] * FOOD_PER_DAY
        # 帰還判定
        if active and day >= busy_until:
            name, reward, loot, dur, party, p = active
            if rng.random() < p:
                total = reward + loot
                gold += total - int(total * SHARE_RATE)
            else:
                gold -= int(reward * PENALTY_RATE)
                if rng.random() < 0.25:          # 失敗時25%で死者1名
                    deaths += 1
                    gold -= REVIVE_COST["損傷"]  # 損傷状態で蘇生と仮定
            active = None
        # 人員増強: 資金に余裕があれば雇用（一時金100G）
        if gold > 800 and roster < 10 and day % 10 == 0:
            gold -= 100; roster += 1
        min_gold = min(min_gold, gold)
        if log and day % 10 == 0:
            print(f"  day{day:3d}: gold={gold:5d} roster={roster} deaths={deaths}")
    return gold, min_gold, roster, deaths

print("=== 60日(序盤E→C帯)を100シードで試行 ===")
finals, mins, bankrupt = [], [], 0
for s in range(100):
    g, mg, r, d = run(s)
    finals.append(g); mins.append(mg)
    if mg < 0: bankrupt += 1
finals.sort(); mins.sort()
print(f"最終資金  中央値: {finals[50]}  下位10%: {finals[10]}  上位10%: {finals[90]}")
print(f"最低資金  中央値: {mins[50]}  下位10%: {mins[10]}")
print(f"倒産(資金<0)率: {bankrupt}%")
print()
print("=== 代表1シードの推移 ===")
run(7, log=True)
