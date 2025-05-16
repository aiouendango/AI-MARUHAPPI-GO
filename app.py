from flask import Flask, request, jsonify, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv

app = Flask(__name__)

# LINE Bot 設定
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Google Sheets 認証設定
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

# LINE Webhook エンドポイント
@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK", 200

# テキストファイルの読み込み関数
def read_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# CSVのメニュー情報を取得
def read_csv(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        data = [row for row in reader]
    return data

# メッセージ受信時処理（GPT連携）
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    # ファイルを読み込む
    txt_content = read_txt('まるは心構え.txt')
    menu_data = read_csv('本店メニュー完全版.csv')
    
    # メインのsystem_prompt
    system_prompt = f"""
    あなたは「まるは食堂」の公式AIコンシェルジュ『AIまるはっぴー』です。

    ようこそ いらっしゃいませ
    お客さまとのお約束ごと
    まるは食堂のAIコンシェルジュ『AIまるはっぴー』です。
    こちらはAIがお答えしているため、特に営業日・営業時間・メニュー内容・予約状況などの
    重要事項については、必ず該当の店舗へ直接ご確認ください。

    【公式ウェブサイト】
    http://maruha-net.co.jp

    【グループ会社】
    http://hazunohoshi.jp  
    http://15oka.net  

    【メニュー】
    {read_csv('本店メニュー完全版.csv')}  # CSVファイル内容

    【その他の情報】
    {read_txt('まるは心構え.txt')}  # TXTファイル内容
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    )

    reply_text = response.choices[0].message.content

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# GPTs 連携用 Google Sheets 書き込みエンドポイント
@app.route('/append', methods=['POST'])
def append_to_sheet():
    data = request.json
    sheet_id = data.get('sheetId')
    range_name = data.get('range')
    values = data.get('values')

    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.worksheet(range_name.split('!')[0])
        worksheet.append_rows(values)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ローカル実行用
if __name__ == "__main__":
    app.run()
