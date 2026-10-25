import json, sys, datetime, os
now = datetime.datetime.now()
minutes = now.hour * 60 + now.minute
if not (105 <= minutes < 330):
    sys.exit(0)
p = '/private/tmp/cairn-long-calibration/overnight-state.json'
try:
    st = json.load(open(p))
    ts = st.get('timestamp') or st.get('updated') or st.get('ts')
    if st.get('paused') is False and ts:
        t = datetime.datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        if t.tzinfo is not None:
            t = t.astimezone().replace(tzinfo=None)
        if t.date() == now.date() and t.hour * 60 + t.minute >= 120:
            sys.exit(0)
except Exception:
    pass
sys.exit(1)
