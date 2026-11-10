import gspread
import pandas as pd
import yaml

# ① 設定を読む（どのシートに書くか・鍵はどこか）
with open("sheet.yaml", encoding="utf-8") as f:
    conf = yaml.safe_load(f)

# ② 鍵で本人確認して、スプレッドシートを開く
gc = gspread.service_account(filename=conf["credentials"])
sh = gc.open_by_key(conf["spreadsheet_id"])
print(f"■ 開いたスプレッドシート：{sh.title}")


# ③ 表を「スプレッドシートに書ける形」（見出し＋行のリスト）に変える
def to_rows(df):
    df = df.astype(object).where(df.notna(), "")  # 空欄（NaN）は "" にする
    return [df.columns.tolist()] + df.values.tolist()


# ④ シート（タブ）を用意して、中身を消してから書き込む
def write(name, df):
    try:
        ws = sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1, cols=1)  # 無ければ作る
    ws.clear()
    ws.update(range_name="A1", values=to_rows(df), value_input_option="USER_ENTERED")
    print(f"  {name}：{len(df)}行を書き込みました")


daily = pd.read_csv("output/daily_cpa.csv", encoding="utf-8-sig")
daily["cpa"] = daily["cpa"].round(0)  # CPAは円単位で見やすく
alerts = pd.read_csv("output/alerts.csv", encoding="utf-8-sig")

write("daily_cpa", daily)
write("alerts", alerts)