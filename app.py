
from flask import Flask, request, jsonify, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

# メッセージ受信時処理（GPT連携）
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは『まるは食堂』のAI専属AIコンシェルジュです。"
                    "南知多の観光名所として有名な『ジャンボエビフライ』や、"
                    "活魚料理、温泉や回転寿司などなど…"
                    "まるは食堂グループの魅力をお客様に親切で丁寧に、"
                    "わかりやすく案内してください。"
                    "質問に応じて最適な提案をすることが求められます。"
                )
            },
            {
                "role": "user",
                "content": user_text
            }
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
