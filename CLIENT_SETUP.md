# ad-report 導入手順（お客さま向け）

広告CSVをまとめてCPA（成果1件あたりの広告費）の急騰を判定し、お客さまのGoogleスプレッドシートに書き込むツールです。
この手順書だけで、受け取ったZIPから書き込みまで進められます。

## 全体の流れ

```
【Google側（ブラウザ）】
  1. Google Cloud にプロジェクトを作る（組織なし）
  2. Sheets API / Drive API を有効にする
  3. サービスアカウント（書き込み専用のロボット用アカウント）を作る
  4. サービスアカウントの鍵（JSONファイル）を作る
  5. スプレッドシートを、サービスアカウントに「編集者」で共有する
        ↓
【PC】
  6. ZIPを展開する
  7. 鍵を credentials/ に置く
  8. sheet.yaml にスプレッドシートのIDを書く
  9. Python の準備をする
 10. 広告CSVを input/ に置く
 11. 02 → 04 → 05 の順に実行する
 12. スプレッドシートで結果を確認する
```

## 用意するもの

| もの | 内容 |
|---|---|
| Googleアカウント | Google Cloud を使うアカウント。会社の組織に属していない個人のGmailでも可 |
| 書き込み先のスプレッドシート | 空のスプレッドシートを1つ。タブはツールが作ります |
| **Python 3.13 または 3.14** | **3.15 は使えません**（部品の1つ PyYAML に、3.15 用の配布物がないため） |
| 広告CSV | Meta広告・Google広告・Yahoo広告の管理画面から出力したもの（使っている媒体の分だけでOK） |

> **鍵（JSONファイル）は、だれにも送らないでください。** 開発者にも送る必要はありません。鍵があれば、共有したスプレッドシートを書き換えられます。

---

## A. Google側でやること（ブラウザ）

### 1. プロジェクトを作る

1. `https://console.cloud.google.com` を開く
2. 画面左上のプロジェクト名のボタン →「新しいプロジェクト」
3. プロジェクト名を入れる（例：`ad-report`）
4. 「組織」と「親リソース」が **組織なし** になっていることを確認して「作成」

> 会社の組織の下に作ると、組織のルール（サービスアカウントキーの作成をブロック、など）で手順4の鍵が作れないことがあります。

### 2. API を有効にする

1. 画面左上のプロジェクト名が、手順1のプロジェクトになっていることを確認
2. 上の検索バーで `Google Sheets API` を開き「有効にする」
3. 同じように `Google Drive API` を開き「有効にする」

ボタンが「管理」になっていれば、すでに有効です。

### 3. サービスアカウントを作る

1. 左上の ≡ →「IAM と管理」→「サービス アカウント」
2. 「＋ サービス アカウントを作成」
3. 名前を入れる（例：`ad-report-writer`）→「作成して続行」
4. 「権限（省略可）」は **何も選ばずに**「続行」→「完了」

> ロール（権限）は付けません。書き込める範囲を「共有したスプレッドシート1枚」だけにするためです。

一覧に `ad-report-writer@（プロジェクトID）.iam.gserviceaccount.com` の形のメールアドレスが出ます。手順5で使います。

### 4. 鍵（JSONファイル）を作る

1. 手順3のサービスアカウントのメールアドレスをクリック
2. 「鍵」タブ →「鍵を追加」→「新しい鍵を作成」→「JSON」→「作成」
3. JSONファイルがダウンロードされます。**開かずに**、手順7まで置いておきます

### 5. スプレッドシートを共有する

1. 書き込み先のスプレッドシートを開く
2. 右上の「共有」→ 手順3のメールアドレスを貼り付け
3. 権限を **「編集者」** にし、「通知」のチェックを外して「送信」
4. 「一般的なアクセス」は **「制限付き」のまま** にする（「リンクを知っている全員」にはしない）
5. ブラウザのURLの `/d/` と `/edit` の間の文字列が、スプレッドシートのIDです。メモしておきます

```
https://docs.google.com/spreadsheets/d/【ここがID】/edit
```

---

## B. PCでやること

Mac はターミナル、Windows は PowerShell で操作します。

### 6. ZIPを展開する

作業用のフォルダに ZIP を展開し、そのフォルダに移動します。

**Mac**
```bash
mkdir -p ~/work/ad-report
cd ~/work/ad-report
unzip ~/Downloads/ad-report-delivery.zip
```

**Windows**：ZIPを右クリック →「すべて展開」で展開し、PowerShell でそのフォルダに移動します。
```powershell
cd C:\Users\（ユーザー名）\ad-report
```

### 7. 鍵を置く

`credentials` フォルダを作り、手順4の鍵を `service_account.json` という名前で置きます。

**Mac**
```bash
mkdir credentials
mv ~/Downloads/（鍵のファイル名）.json credentials/service_account.json
chmod 600 credentials/service_account.json
```

**Windows**
```powershell
mkdir credentials
Move-Item "$HOME\Downloads\（鍵のファイル名）.json" credentials\service_account.json
```

> コピーではなく移動します。ダウンロードフォルダに鍵を残さないためです。

### 8. sheet.yaml を作る

見本をコピーして、`spreadsheet_id` を手順5のIDに書き換えます。

**Mac**：`cp sheet.example.yaml sheet.yaml`
**Windows**：`copy sheet.example.yaml sheet.yaml`

書き換えたあとの形：
```yaml
spreadsheet_id: "（手順5のID）"
credentials: "credentials/service_account.json"
```

### 9. Python の準備をする

**Python 3.13 か 3.14 を指定して**、このフォルダ専用の環境（venv）を作ります。

**Mac**
```bash
python3 --version          # 3.13.x か 3.14.x であることを確認
python3 -m venv .venv
source .venv/bin/activate  # 行の先頭に (.venv) が付けばOK
pip install -r requirements.txt
```

**Windows**
```powershell
py list                    # 3.13 か 3.14 が入っているか確認
py -V:3.13 -m venv .venv   # 3.14 を使う場合は -V:3.14
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> Windows で `python` とだけ打つと、既定の Python（3.15 など）が使われることがあります。`py -V:3.13` のように版を指定してください。

`requirements.txt` には、動作確認した部品の版がすべて書いてあります。版は変えずにそのまま使ってください。

### 10. 広告CSVを置く

広告の管理画面から出力したCSVを `input/` フォルダに置きます（フォルダがなければ作ります）。
ファイル名は、媒体ごとに次の名前で始めます。

| 媒体 | ファイル名 | 例 |
|---|---|---|
| Meta広告 | `meta_ads_` で始まる `.csv` | `meta_ads_20261123.csv` |
| Google広告 | `google_ads_` で始まる `.csv` | `google_ads_20261123.csv` |
| Yahoo広告 | `yahoo_ads_` で始まる `.csv` | `yahoo_ads_20261123.csv` |

使っていない媒体のCSVはなくてもかまいません（`⚠️ ファイルが見つかりません → スキップ` と出て、残りの媒体で続けます）。この決まりは `columns.yaml` の `file_pattern` に書いてあります。

> まず動作を試すときは、`input/` を使わずに、同梱の `sample_data/`（架空のデータ）を読ませることができます（手順11）。

### 11. 実行する

**必ずこの順番**で実行します。

**Mac**（venv が有効な状態で）
```bash
python 02_load_ads.py   # サンプルで試すときは：INPUT_DIR=sample_data python 02_load_ads.py
python 04_alert.py
python 05_to_sheet.py
```

**Windows**
```powershell
.\.venv\Scripts\python.exe 02_load_ads.py
.\.venv\Scripts\python.exe 04_alert.py
.\.venv\Scripts\python.exe 05_to_sheet.py
```

Windows でサンプルを試すときは、02 の前に次を1回打ちます（その PowerShell の画面を閉じると元に戻ります）。
```powershell
$env:INPUT_DIR = "sample_data"
```

| スクリプト | うまくいったときの表示 |
|---|---|
| `02_load_ads.py` | `■ 読むフォルダ：input`（サンプルなら `sample_data`）と、読み込んだファイル名 |
| `04_alert.py` | キャンペーンごとのCPAと判定（OK / 🔔急騰） |
| `05_to_sheet.py` | `■ 開いたスプレッドシート：（シート名）` と、書き込んだ行数 |

### 12. 結果を確認する

スプレッドシートを開き（開いていれば再読み込み）、次のタブができていることを確認します。

| タブ | 中身 |
|---|---|
| `daily_cpa` | 日別・キャンペーン別の広告費、成果、CPA。データが無い日は0の行で補います |
| `alerts` | 通知が必要なもの（CPA急騰、データ未更新など） |

成果0件の日は、CPAを計算できないので空欄になります。

---

## うまくいかないとき

### エラーで止まったとき

`05_to_sheet.py` は、下の表の上から順に確かめながら進みます。**最初に引っかかった段階**が原因です。

| # | 確かめていること | 出るエラーの例 | 直すところ |
|---|---|---|---|
| 1 | `sheet.yaml` が読めるか | `FileNotFoundError: … sheet.yaml` | 手順8。実行しているフォルダも確認 |
| 2 | 鍵ファイルが見つかるか | `FileNotFoundError: … service_account.json` | 手順7。置き場所と名前 |
| 3 | 鍵が有効か | `invalid_grant` / `Invalid JWT` | 手順4で鍵を作り直す。PCの時計も確認 |
| 4 | API が有効か | `has not been used … or it is disabled` | 手順2 |
| 5 | スプレッドシートがあるか | `SpreadsheetNotFound` / `404` | 手順8のIDをURLと照合 |
| 6 | 共有されているか | `PERMISSION_DENIED` | 手順5。「編集者」で共有したか |

5 と 6 は、どちらのエラーにも見えることがあります。どちらかが出たら、IDと共有の両方を確認してください。

`pip install` で `Microsoft Visual C++ 14.0 or greater is required` と出たときは、Python 3.15 で venv を作っています。手順9で 3.13 か 3.14 を指定して作り直してください。

### 「書き込みました」と出たのに、シートが古いままのとき

ツールは正常に動いています。手間の少ない順に確認します。

1. スプレッドシートを再読み込みする
2. `05_to_sheet.py` の `■ 開いたスプレッドシート：` のシート名が、見ているシートと同じか（違えば `sheet.yaml` のID）
3. `02_load_ads.py` の `■ 読むフォルダ：` が想定どおりか（違えば 02 → 04 → 05 をやり直す）
