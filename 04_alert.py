from pathlib import Path

import pandas as pd
import yaml

# ① 判定ルールを読む
with Path("alert_rules.yaml").open(encoding="utf-8") as f:
    rules = yaml.safe_load(f)
cpa_rule = rules["cpa_alert"]
zero_rule = rules["zero_conversion_alert"]

# ② 段階1の表を読み、行が無い日を0で埋める（03と同じ）
ads = pd.read_csv("output/ads_combined.csv", encoding="utf-8-sig", parse_dates=["date"])
days = pd.DataFrame({"date": pd.date_range(ads["date"].min(), ads["date"].max())})
camps = ads[["media", "campaign"]].drop_duplicates()
daily = camps.merge(days, how="cross").merge(ads, on=["media", "campaign", "date"], how="left")
nums = ["spend", "conversions", "impressions", "clicks"]
daily[nums] = daily[nums].fillna(0)

# ③ 「CPAを判定できる日」を定義して、その日だけCPAを計算する
judgeable = (daily["conversions"] >= cpa_rule["min_conversions"]) & (daily["spend"] >= cpa_rule["min_spend"])
daily["cpa"] = (daily["spend"] / daily["conversions"]).where(judgeable)

# ④ 判定する日（いちばん新しい日）と、「ふだん」を測る期間
target_date = daily["date"].max()
start = target_date - pd.Timedelta(days=cpa_rule["baseline_days"])
print(f"■ 判定する日：{target_date.date()}（ふだん＝{start.date()}〜前日の中央値）")
print()

alerts = []  # 通知する内容をためるリスト

# ⑤ キャンペーンごとに、CPAの急騰を判定する
for (media, campaign), g in daily.groupby(["media", "campaign"]):
    today = g[g["date"] == target_date].iloc[0]
    past = g[(g["date"] >= start) & (g["date"] < target_date)]
    baseline = past["cpa"].median()

    if pd.isna(today["cpa"]):
        print(f"  {media}/{campaign}：判定外（成果{today['conversions']:.0f}件・広告費{today['spend']:,.0f}円）")
        continue
    if pd.isna(baseline):
        print(f"  {media}/{campaign}：判定外（ふだんのCPAを測れる日が足りない）")
        continue

    ratio = today["cpa"] / baseline
    mark = "🔔急騰" if ratio > cpa_rule["threshold_ratio"] else "OK"
    print(f"  {media}/{campaign}：CPA {today['cpa']:,.0f}円 ／ ふだん {baseline:,.0f}円 ＝ {ratio:.1f}倍 → {mark}")
    if mark != "OK":
        alerts.append(f"【CPA急騰】{media}/{campaign}：{today['cpa']:,.0f}円（ふだんの{ratio:.1f}倍）")

# ⑥ 「お金を使ったのに成果0件」が続いていないか（CPAとは別の通知）
print()
n = zero_rule["consecutive_days"]
for (media, campaign), g in daily.groupby(["media", "campaign"]):
    last_n = g[g["date"] > target_date - pd.Timedelta(days=n)]
    is_zero = (last_n["spend"] >= zero_rule["min_spend"]) & (last_n["conversions"] == 0)
    if len(last_n) == n and is_zero.all():
        alerts.append(f"【成果0件が{n}日連続】{media}/{campaign}：広告費 合計{last_n['spend'].sum():,.0f}円")

# ⑦ 結果
print("■ 通知する内容")
if alerts:
    for a in alerts:
        print("  " + a)
else:
    print("  なし")

# ⑧ 次の段階のために保存
daily.to_csv("output/daily_cpa.csv", index=False, encoding="utf-8-sig")
pd.DataFrame({"alert": alerts}).to_csv("output/alerts.csv", index=False, encoding="utf-8-sig")