from pathlib import Path

import pandas as pd
import yaml

INPUT_DIR = Path("input")

# ① 設定ファイルを読む（01と同じ）
with Path("columns.yaml").open(encoding="utf-8") as f:
    config = yaml.safe_load(f)

frames = []  # 媒体ごとの表を入れていく、空のリスト

# ② 媒体ごとに、CSVを読んで列名をそろえる
for media, settings in config.items():

    # ②-1 ファイルを探す（無ければ知らせて、次の媒体へ）
    files = sorted(INPUT_DIR.glob(settings["file_pattern"]))
    if not files:
        print(f"⚠️ {media}：ファイルが見つかりません（{settings['file_pattern']}）→ スキップ")
        continue
    path = files[-1]  # いちばん新しいファイル
    print(f"✅ {media}：{path.name} を読み込みます")

    # ②-2 読む（表紙の行を飛ばし、全部を文字として）
    df = pd.read_csv(
        path,
        encoding=settings["encoding"],
        skiprows=settings["skip_rows"],
        dtype=str,
    )

    # ②-3 「合計」などのまとめの行を除く（設定に無い媒体は何もしない）
    date_col = settings["columns"]["date"]
    for word in settings.get("drop_rows_starting_with", []):
        df = df[~df[date_col].str.startswith(word)]

    # ②-4 列名を共通の名前にそろえる（方言 → 共通語の対応表を作る）
    rename_map = {}
    for common, actual in settings["columns"].items():
        rename_map[actual] = common
    df = df.rename(columns=rename_map)
    df = df[list(settings["columns"].keys())]  # 使う列だけ残す

    # ②-5 どの媒体のデータか、印を付けて保存
    df["media"] = media
    frames.append(df)

# ③ 媒体ごとの表を、縦に1つにつなげる
ads = pd.concat(frames, ignore_index=True)

# ④ 書き方をそろえる（日付・数字）
ads["date"] = pd.to_datetime(ads["date"].str.replace("/", "-"), format="%Y-%m-%d")
for col in ["spend", "conversions", "impressions", "clicks"]:
    ads[col] = pd.to_numeric(ads[col].str.replace(",", ""))

# ---- 確認 ----
print()
print("■ 先頭の5行")
print(ads.head().to_string())
print()
print("■ 媒体ごとの行数")
print(ads["media"].value_counts().to_string())
print()
print("■ 媒体ごとの広告費の合計")
print(ads.groupby("media")["spend"].sum().to_string())