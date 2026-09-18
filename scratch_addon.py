import json

with open(r'D:\Games\.minecraft\versions\UltimateMinePack\TLauncherAdditional.json', encoding='utf-8') as f:
    data = json.load(f)

ver = data['modpack']['version']
sps = ver.get('shaderpacks', [])

print('Last 5 shaderpacks (to see official ones):')
for s in sps[-5:]:
    state = s.get('stateGameElement')
    sid = s.get('id')
    name = s.get('name')
    user = s.get('userInstall')
    parser = s.get('parser')
    v = s.get('version', {})
    m = v.get('metadata', {})
    url = m.get('url')
    path = m.get('path')
    print(f'  state={state} | id={sid} | name={name} | userInstall={user} | parser={parser}')
    print(f'    url={url} | path={path}')
