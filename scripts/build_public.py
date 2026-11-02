from pathlib import Path
import shutil
import os, json
root=Path(__file__).resolve().parents[1]
out=root/'site/public';out.mkdir(parents=True,exist_ok=True)
for f in ['index.html','styles.css','app.js','editor.html']:
    shutil.copy2(root/'site'/f,out/f)
(out/'data').mkdir(exist_ok=True)
shutil.copy2(root/'site/data/published.json',out/'data/published.json')
(out/'config.json').write_text(json.dumps({'repository':os.getenv('GITHUB_REPOSITORY','')})+'\n',encoding='utf-8')
print('Built public site without pending/rejected/audit metadata')
