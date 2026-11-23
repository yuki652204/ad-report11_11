# ad-report

Meta広告・Google広告のCSVを1つの表にまとめて、CPA（成果1件あたりの広告費）の急騰を判定し、Googleスプレッドシートに書き込む自動化です。GitHub Actionsで毎朝実行します。

> **お客さまへ**：導入と実行の手順は [CLIENT_SETUP.md](CLIENT_SETUP.md) にまとめています。

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
- **データ未更新**：最新のデータが、実行した日（日本時間）の **前日より古ければ** 通知。取り込みが止まったまま古いデータで判定し続けるのを防ぐ

## 手元で動かす

対応Python は **3.13 / 3.14** です。3.15 は、PyYAML 6.0.3 の配布物がないため `pip install` に失敗します（2026-11-23 確認）。

```powershell
py -V:3.13 -m venv .venv   # Python の版を指定して作る
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy sheet.example.yaml sheet.yaml   # スプレッドシートのIDを書く
# credentials/service_account.json にサービスアカウントの鍵を置く
python 02_load_ads.py
python 04_alert.py
python 05_to_sheet.py
```

読み込むフォルダは環境変数 `INPUT_DIR` で切り替えられます（指定しなければ `input/`）。

```powershell
# サンプルデータで試すとき（PowerShell。画面を閉じると元に戻る）
$env:INPUT_DIR = "sample_data"
```

```bash
# Mac
INPUT_DIR=sample_data python 02_load_ads.py
```

## 納品ZIPの作り方

```powershell
git archive --format=zip -o ad-report-delivery.zip HEAD
```

Git管理のファイルだけが入るので、`credentials/`・`sheet.yaml`・`input/`・`output/` は入らない。`.github/` も `.gitattributes` の `export-ignore` で除外している（お客さまは GitHub Actions を使わないため）。お客さま向けの手順は `CLIENT_SETUP.md`。

## GitHub Actions

`.github/workflows/daily.yml` で、毎朝実行します（手動の「Run workflow」も可）。

| Secrets | 中身 |
|---|---|
| `GCP_SA_KEY` | サービスアカウントの鍵（JSON） |
| `SHEET_ID` | 書き込み先のスプレッドシートのID |
| `MAIL_USER` | 通知を送るGmail（通知専用のアカウント） |
| `MAIL_APP_PASSWORD` | 通知専用アカウントのアプリパスワード |
| `MAIL_TO` | 通知を受け取るアドレス |

### 通知（06_notify.py）

- `alerts.csv` に1件以上あるときだけ、Gmailでメールを送る。**急騰がない日は送らない**（毎日届くと読まなくなり、本当の急騰を見逃すため）
- 送信元は**通知専用のGmailアカウント**。アプリパスワードは範囲をしぼれないため、漏れてもふだんのアカウントに影響しないようにしている
- 必須の設定（`MAIL_USER` など）は `os.environ["…"]` で読み、**足りなければ送信前にエラーで止める**。黙って送らずに終わると、通知が壊れたことに気づけないため
- 手元では `DRY_RUN=1` を付けると、送らずに件名と本文だけを表示する（送った記録も残さない）
- **同じ通知は1回だけ送る**。通知ごとに「種類｜日付｜キャンペーン」の名札（key）を付け、送った名札をスプレッドシートの `notified` タブに残す。次の朝は、名札が残っている通知を送らない
- 記録は**送れたあと**に残す。先に記録すると、送信に失敗したときに二度と届かなくなるため。この順なら、記録に失敗しても翌日もう一度届くだけで済む

> サンプルデータは11/09で止まっているため、以前は毎朝**同じ「11/09のCPA急騰」**が届いていた。データが古いことにもメールからは気づけなかった。この2つを直すために、重複の防止とデータ未更新の通知を入れた。

## GitHubに上げないもの

| もの | 理由 |
|---|---|
| `input/` `output/` | 本番では依頼主の広告費・成果の数字が入る |
| `credentials/` | スプレッドシートに書き込むための鍵 |
| `sheet.yaml` | 依頼主ごとに違う書き込み先 |

## わかったこと：実行時刻の遅れ

GitHub Actions の `schedule` は混雑で遅れます。日本時間 8:17 に設定したところ、2026/11/11〜13 の実測では **11:46〜12:48 に実行** されました（3〜4時間半の遅れ）。

決まった時刻に更新する必要がある場合は、外部のスケジューラ（Google Cloud Scheduler など）から `workflow_dispatch` を呼ぶ方法を検討します。手動実行（`workflow_dispatch`）は、順番待ちせずにすぐ始まることを確認しています。

## わかったこと：60日で自動実行が止まる

公開リポジトリでは、**60日間コミットなどがないと `schedule` が止まる**。止まっても失敗（✗）にはならないので、失敗のメールも届かない。

このリポジトリでは対策を入れていないが、次の方法で防げる。

| 方法 | 内容 |
|---|---|
| 毎回の実行の最後に `gh workflow enable` を呼ぶ | コミットを増やさずに、60日の数え直しになる。権限は `actions: write` だけの**別のjob**に分け、レポートを作るjobには権限を足さない |
| 45日ごとに空のコミットを自動で作る | 確実だが、履歴に自動のコミットが増え続ける |

止まった場合は、何か1回コミットするか、`gh workflow enable daily.yml` で再開できる。


