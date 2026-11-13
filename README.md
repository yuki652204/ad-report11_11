# ad-report

Meta広告・Google広告のCSVを1つの表にまとめて、CPA（成果1件あたりの広告費）の急騰を判定し、Googleスプレッドシートに書き込む自動化です。GitHub Actionsで毎朝実行します。

> `sample_data/` のデータは**架空**です。実在する広告アカウントの数字ではありません。

## 全体の流れ

```
sample_data/*.csv（本番では input/）
   ↓ 02_load_ads.py   媒体ごとの列名をそろえて、1つの表にまとめる（columns.yaml）
output/ads_combined.csv
   ↓ 04_alert.py      行が無い日を0で埋めてCPAを計算し、急騰を判定する（alert_rules.yaml）
output/daily_cpa.csv / output/alerts.csv
   ↓ 05_to_sheet.py   サービスアカウントでGoogleスプレッドシートに書き込む（sheet.yaml）
スプレッドシート（daily_cpa / alerts）
```

## 判定ルール（alert_rules.yaml）

- **CPA急騰**：その日のCPAが、直近7日の中央値の **2.0倍を超えたら** 通知（2.0倍ちょうどは含まない）
- 成果0件の日や広告費が少ない日は、CPAを計算できないので **判定から外す**（0円として扱わない）
- **成果0件が続く**：広告費を使っているのに成果0件が続いたら、CPAとは別に通知

## 手元で動かす

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy sheet.example.yaml sheet.yaml   # スプレッドシートのIDを書く
# credentials/service_account.json にサービスアカウントの鍵を置く
python 02_load_ads.py
python 04_alert.py
python 05_to_sheet.py
```

読み込むフォルダは環境変数 `INPUT_DIR` で切り替えられます（指定しなければ `input/`）。

## GitHub Actions

`.github/workflows/daily.yml` で、毎朝実行します（手動の「Run workflow」も可）。

| Secrets | 中身 |
|---|---|
| `GCP_SA_KEY` | サービスアカウントの鍵（JSON） |
| `SHEET_ID` | 書き込み先のスプレッドシートのID |

## GitHubに上げないもの

| もの | 理由 |
|---|---|
| `input/` `output/` | 本番では依頼主の広告費・成果の数字が入る |
| `credentials/` | スプレッドシートに書き込むための鍵 |
| `sheet.yaml` | 依頼主ごとに違う書き込み先 |

## わかったこと：実行時刻の遅れ

GitHub Actions の `schedule` は混雑で遅れます。日本時間 8:17 に設定したところ、2026/11/11〜13 の実測では **11:46〜12:48 に実行** されました（3〜4時間半の遅れ）。

決まった時刻に更新する必要がある場合は、外部のスケジューラ（Google Cloud Scheduler など）から `workflow_dispatch` を呼ぶ方法を検討します。手動実行（`workflow_dispatch`）は、順番待ちせずにすぐ始まることを確認しています。