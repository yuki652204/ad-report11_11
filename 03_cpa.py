import pandas as pd

# ① 段階1でまとめた表を読む
ads = pd.read_csv("output/ads_combined.csv", encoding="utf-8-sig", parse_dates=["date"])

# ② 「行が無い日」を0で埋める
#    媒体×キャンペーン と 全部の日付 の「すべての組み合わせ」の枠を作り、データを当てはめる
days = pd.DataFrame({"date": pd.date_range(ads["date"].min(), ads["date"].max())})
camps = ads[["media", "campaign"]].drop_duplicates()
grid = camps.merge(days, how="cross")
daily = grid.merge(ads, on=["media", "campaign", "date"], how="left")

filled = daily["spend"].isna()  # 枠はあるのにデータが無かった行に○
nums = ["spend", "conversions", "impressions", "clicks"]
daily[nums] = daily[nums].fillna(0)

print(f"■ 行が無かったので0で埋めた日：{filled.sum()}件")
print(daily[filled][["date", "media", "campaign"]].to_string(index=False))
print()

# ③ CPAを計算する ── まずは「そのまま割った」場合（わざと失敗させる）
daily["cpa_naive"] = daily["spend"] / daily["conversions"]
bad = (daily["cpa_naive"] == float("inf")) | daily["cpa_naive"].isna()
print("■ そのまま割ったときの、おかしな値")
print(daily[bad][["date", "media", "campaign", "spend", "conversions", "cpa_naive"]].to_string(index=False))
print()

# ④ 正しい計算：CVが0件の日は「計算しない（空欄）」
daily["cpa"] = (daily["spend"] / daily["conversions"]).where(daily["conversions"] > 0)

# ---- 確認 ----
print("■ CVが0件で、CPAを空欄にした日")
zero = daily[daily["conversions"] == 0]
print(zero[["date", "media", "campaign", "spend", "conversions", "cpa"]].to_string(index=False))
print()
print("■ キャンペーンごとの、ふだんのCPA（中央値）")
print(daily.groupby(["media", "campaign"])["cpa"].median().round(0).to_string())