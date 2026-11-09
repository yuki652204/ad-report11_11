from pathlib import Path

import yaml

# ① 設定ファイルを読む
config_path = Path("columns.yaml")
with config_path.open(encoding="utf-8") as f:
    config = yaml.safe_load(f)

# ② 読み込んだものの「形」を確かめる
print("型：", type(config))
print("媒体の一覧：", list(config.keys()))
print("Googleで飛ばす行数：", config["google"]["skip_rows"])
print()

# ③ 媒体ごとに、列名の対応を表示する
for media, settings in config.items():
    print(f"■ {media}（文字コード：{settings['encoding']}）")
    for common, actual in settings["columns"].items():
        print(f"  {common:<12} ← {actual}")
    print()