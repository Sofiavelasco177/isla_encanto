from run import app

with app.test_client() as client:
    resp = client.get('/hospedaje/calendar/1')
    print('status:', resp.status_code)
    try:
        j = resp.get_json()
        print('json keys:', list(j.keys()) if isinstance(j, dict) else type(j))
        # print sample head
        if isinstance(j, dict) and 'days' in j:
            print('days sample (first 6):', j['days'][:6])
    except Exception as e:
        print('cannot parse json; raw:', resp.data[:100])
