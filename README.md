# moonlight

moonlight is a reverse port forwarding tool written by python

## install

```bash
python -m pip install moonlightpy
```

## run

### server config.json

```json
{
  "addr": "0.0.0.0",
  "port": 9001,
  "max_num": 1024,
  "rule_file": "rules.csv"
}
```

### rule.csv

```csv
192.168.0.134,22,0.0.0.0,13422
192.168.0.132,22,0.0.0.0,13222
```

### run

```bash
# run server on some public network host (e.g. 1.1.1.1)
 python -m moonlightpy server .\config.json
 
 # run clients on some intranet host 
 python -m moonlightpy client 1.1.1.1 9001
```

Now you can access the `192.168.0.134:22` from `1.1.1.1:13422` and `192.168.0.132:22` from `1.1.1.1:13222`

