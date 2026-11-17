import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import pandas as pd

SENT_SHEET = "notified"  # 送った通知の記録（05_to_sheet.py は消さないタブ）


# ① 通知する内容を読む（04_alert.py が作ったもの）
alerts = pd.read_csv("output/alerts.csv", encoding="utf-8-sig").dropna(subset=["alert"])

if alerts.empty:
    print("■ 通知なし（CPAの急騰も、成果0件の連続も、データの遅れもなし）→ メールは送りません")
    sys.exit(0)

dry_run = os.environ.get("DRY_RUN") == "1"


# ② 送った記録のタブを開く（試し実行では開かない）
def open_sent_sheet():
    import gspread
    import yaml

    with open("sheet.yaml", encoding="utf-8") as f:
        conf = yaml.safe_load(f)
    sh = gspread.service_account(filename=conf["credentials"]).open_by_key(conf["spreadsheet_id"])
    try:
        return sh.worksheet(SENT_SHEET)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=SENT_SHEET, rows=1, cols=3)
        ws.update(range_name="A1", values=[["key", "alert", "sent_at"]])
        return ws


def new_only(alerts, sent_keys):
    """まだ送っていない通知だけを残す（同じ日・同じキャンペーンの同じ通知は2回送らない）"""
    return alerts[~alerts["key"].isin(sent_keys)]


if dry_run:
    sent_ws, sent_keys = None, set()
else:
    sent_ws = open_sent_sheet()
    sent_keys = set(sent_ws.col_values(1)[1:])  # 1行目は見出し

new = new_only(alerts, sent_keys)
skipped = len(alerts) - len(new)
if skipped:
    print(f"■ 送信済みのため、送らない通知：{skipped}件")
if new.empty:
    print("■ 新しい通知はありません → メールは送りません")
    sys.exit(0)

# ③ メールの件名と本文を作る
subject = f"【広告レポート】要確認 {len(new)}件"
body = (
    "次の内容を確認してください。\n\n"
    + "\n".join(new["alert"])
    + "\n\n日ごとの数字は、スプレッドシートの daily_cpa タブで確認できます。"
    + "\n同じ内容の通知は、翌日以降は送りません（送った記録は notified タブ）。"
)

# ④ 試し実行なら、送らずに表示するだけ（送った記録も残さない）
if dry_run:
    print("■ 試し実行（DRY_RUN=1）：メールは送りません")
    print(f"件名：{subject}")
    print(body)
    sys.exit(0)

# ⑤ 金庫から渡された情報で送る（足りなければ、ここでエラーになって止まる）
user = os.environ["MAIL_USER"]
password = os.environ["MAIL_APP_PASSWORD"]
to = os.environ["MAIL_TO"]

msg = EmailMessage()
msg["Subject"] = subject
msg["From"] = user
msg["To"] = to
msg.set_content(body)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(user, password)
    smtp.send_message(msg)
print(f"■ メールを送りました（{len(new)}件）")

# ⑥ 送れたあとで、送った記録を残す
#    先に記録してから送ると、送信に失敗したときに「送ったこと」になって二度と届かない。
#    この順なら、記録に失敗しても翌日もう一度届くだけで済む。
sent_at = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M")
sent_ws.append_rows([[k, a, sent_at] for k, a in zip(new["key"], new["alert"])])
print(f"■ 送った記録を {SENT_SHEET} タブに残しました")
