import os
import smtplib
import sys
from email.message import EmailMessage

import pandas as pd

# ① 通知する内容を読む（04_alert.py が作ったもの）
alerts = pd.read_csv("output/alerts.csv", encoding="utf-8-sig")["alert"].dropna().tolist()

if not alerts:
    print("■ 通知なし（CPAの急騰も、成果0件の連続もなし）→ メールは送りません")
    sys.exit(0)

# ② メールの件名と本文を作る
subject = f"【広告レポート】要確認 {len(alerts)}件"
body = (
    "次のキャンペーンを確認してください。\n\n"
    + "\n".join(alerts)
    + "\n\n日ごとの数字は、スプレッドシートの daily_cpa タブで確認できます。"
)

# ③ 試し実行なら、送らずに表示するだけ
if os.environ.get("DRY_RUN") == "1":
    print("■ 試し実行（DRY_RUN=1）：メールは送りません")
    print(f"件名：{subject}")
    print(body)
    sys.exit(0)

# ④ 金庫から渡された情報で送る（足りなければ、ここでエラーになって止まる）
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

print(f"■ メールを送りました（{len(alerts)}件）")