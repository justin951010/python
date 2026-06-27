from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import requests 
from bs4 import BeautifulSoup 
import urllib.parse
from datetime import datetime

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")

db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)

try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"資料庫提示: {e}")

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/todo")
def todo():
    todos = Todo.query.all()
    return render_template("todo.html", todos=todos)

@app.route("/add", methods=["POST"])
def add_todo():
    content = request.form.get("content")
    if content:
        new_todo = Todo(content=content)
        db.session.add(new_todo)
        db.session.commit()
    return redirect("/todo")

@app.route("/update/<int:id>", methods=["POST"])
def update_todo(id):
    todo = Todo.query.get(id)
    if todo:
        new_content = request.form.get("content")
        if new_content:
            todo.content = new_content
            db.session.commit()
    return redirect("/todo")

@app.route("/lol_esports", methods=["GET"])
def lol_esports():
    matches = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        cargo_api_url = (
            f"https://lol.fandom.com/api.php?action=cargoquery&format=json"
            f"&tables=MatchSchedule=M"
            f"&fields=M.Team1,M.Team2,M.DateTime_UTC,M.Tournament,M.BestOf"
            f"&where=M.DateTime_UTC >= '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' "
            f"AND (M.Tournament LIKE '%First Stand%' OR M.Tournament LIKE '%Mid-Season Invitational%' OR M.Tournament LIKE '%World Championship%')"
            f"&order_by=M.DateTime_UTC ASC"
            f"&limit=5"
        )
        response = requests.get(cargo_api_url, headers=headers, timeout=5).json()
        if "cargoquery" in response and response["cargoquery"]:
            for row in response["cargoquery"]:
                m_data = row["title"]
                t1 = m_data.get("Team1", "T1")
                t2 = m_data.get("Team2", "TLAW")
                raw_time = m_data.get("DateTime UTC", "")
                tournament = m_data.get("Tournament", "MSI")
                bo_format = m_data.get("BestOf", "5")
                time_str = "11:00 上午"
                if raw_time:
                    try:
                        dt = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
                        hour = dt.hour
                        ampm = "上午" if hour < 12 else "下午"
                        display_hour = hour if hour <= 12 else hour - 12
                        if display_hour == 0: display_hour = 12
                        time_str = f"{display_hour:02d}:{dt.minute:02d} {ampm}"
                    except:
                        pass
                matches.append({
                    "time": time_str, "team_a": t1, "team_b": t2, "stage": f"{tournament} • 淘汰賽", "bo": f"BO{bo_format}"
                })
    except Exception as e:
        print(f"❌ 賽程數據錯誤: {e}")
    if not matches:
        matches = [
            {"time": "11:00 上午", "team_a": "T1", "team_b": "TLAW", "stage": "MSI • 入圍賽淘汰賽", "bo": "BO5"},
            {"time": "04:00 下午", "team_a": "KC", "team_b": "DCG", "stage": "MSI • 入圍賽淘汰賽", "bo": "BO5"}
        ]
    return render_template("lol_esports.html", matches=matches)

@app.route("/lol_champions", methods=["GET"])
def lol_champions():
    champions_list = []
    target_url = "https://www.op.gg/zh-tw/lol/champions?position=all&tier=all"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-TW,zh;q=0.9'
    }
    try:
        res = requests.get(target_url, headers=headers, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.select("table tbody tr")
            count = 0
            for row in rows:
                if count >= 20: break
                name_node = row.select_one("td strong") or row.select_one(".champion-name") or row.select_one("td a span")
                if not name_node: continue
                chinese_name = name_node.text.strip()
                cells = row.select("td")
                win_rate, pick_rate, ban_rate = "51.2%", "8.5%", "12.3%"
                data_texts = [c.text.strip() for c in cells if "%" in c.text]
                if len(data_texts) >= 3:
                    win_rate, pick_rate, ban_rate = data_texts[0], data_texts[1], data_texts[2]
                img_node = row.select_one("img")
                image_url = img_node['src'] if img_node and img_node.has_attr('src') else ""
                count += 1
                champions_list.append({
                    "rank": count, "name": chinese_name, "win_rate": win_rate, "pick_rate": pick_rate, "ban_rate": ban_rate, "image_url": image_url
                })
    except Exception as e:
        print(f"❌ 現場網頁解析出錯: {e}")
    return render_template("lol_champions.html", champions=champions_list)


# ═══ 🚀 傳送門分流路由：處理 Riot ID 並拋接給前端 ═══
@app.route("/lol_search", methods=["GET", "POST"])
def lol_search():
    player_id = ""
    opgg_url = None
    
    if request.method == "POST":
        player_id = request.form.get("player_id", "").strip()
        if player_id:
            # 處理 Riot ID 格式，將 # 轉為 -
            formatted_id = player_id.replace("#", "-")
            encoded_id = urllib.parse.quote(formatted_id)
            # 生成標準台服官方對應路徑
            opgg_url = f"https://www.op.gg/summoners/tw/{encoded_id}"
            
    return render_template("lol_search.html", player_id=player_id, opgg_url=opgg_url)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)