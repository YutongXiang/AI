import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://jluat-smart-app-api.yuntu.cn/third/jsphb"
BOARD_ID = "4832828643476639840"
TASK_ID = "4829238709759119407"
QUESTION_ID = "4829599581618704402"
TEAM = "Overfit"
STAGES = ("初赛", "复赛", "决赛")
DATA_FILE = Path(__file__).resolve().parents[1] / "docs" / "data.json"

def post(payload):
    request = Request(API, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json","User-Agent":"Overfit-Ranking-Tracker/1.0"}, method="POST")
    with urlopen(request, timeout=20) as response:
        result = json.load(response)
    if not result.get("success"):
        raise RuntimeError("排行榜接口返回失败")
    return result.get("data")

def number(value):
    try:
        parsed = float(value)
        return int(parsed) if parsed.is_integer() else parsed
    except (TypeError, ValueError):
        return None

def main():
    previous = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {"stages":[]}
    old = {item["stage"]: item for item in previous.get("stages", [])}
    metadata = post({"type":"JSJD","bdId":BOARD_ID,"stbh":QUESTION_ID}) or {}
    releases = metadata.get("jsbdList") or []
    published = releases[0].get("ZXFBSJ_") if releases else None
    source_time = published.replace(" ", "T") + "+08:00" if published else None
    stages = []
    has_valid_update = False
    for stage in STAGES:
        rows = post({"pageNo":0,"pageSize":1000,"type":"JSDF","rwId":TASK_ID,"stbh":QUESTION_ID,"jd":stage}) or []
        valid = [row for row in rows if number(row.get("XH_")) is not None and number(row.get("FS_")) is not None]
        team_row = next((row for row in rows if row.get("TDMC_") == TEAM), None)
        current_rank = number(team_row.get("XH_")) if team_row else None
        current_score = number(team_row.get("FS_")) if team_row else None
        prior = old.get(stage, {})
        is_valid = current_rank is not None and current_score is not None
        if is_valid:
            has_valid_update = True
            current_total = len(valid)
        else:
            current_rank = prior.get("currentRank")
            current_total = prior.get("currentTotal")
            current_score = prior.get("currentScore")
        best_rank = prior.get("bestRank")
        best_total = prior.get("bestTotal")
        if is_valid and (best_rank is None or current_rank < best_rank):
            best_rank, best_total = current_rank, current_total
        best_score = prior.get("bestScore")
        if is_valid and (best_score is None or current_score > best_score):
            best_score = current_score
        stages.append({"stage":stage,"currentRank":current_rank,"currentTotal":current_total,"currentScore":current_score,"bestRank":best_rank,"bestTotal":best_total,"bestScore":best_score})
    checked_at = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds") if has_valid_update else previous.get("checkedAt")
    effective_source_time = source_time if has_valid_update else previous.get("sourcePublishedAt")
    DATA_FILE.write_text(json.dumps({"team":TEAM,"checkedAt":checked_at,"sourcePublishedAt":effective_source_time,"stages":stages}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

if __name__ == "__main__":
    main()

