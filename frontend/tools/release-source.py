"""Create an allowlisted source snapshot locally; run build/tests only on the server."""
from pathlib import Path
import hashlib,json,tarfile,datetime
root=Path(__file__).resolve().parents[1]
files=sorted(p for p in root.rglob('*') if p.is_file() and str(p.relative_to(root)) != 'docs/development.md' and not any(part in {'node_modules','dist','.git','reports'} for part in p.relative_to(root).parts))
rows=[{'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size_bytes':p.stat().st_size} for p in files]
aggregate=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
release='m12a-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+aggregate[:12]
manifest={'release_id':release,'aggregate_sha256':aggregate,'files':rows}
manifest_path=Path('/tmp')/(release+'.json');manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
archive=Path('/tmp')/(release+'.tar.gz')
with tarfile.open(archive,'w:gz') as tar:
 for p in files:tar.add(p,arcname='frontend/'+str(p.relative_to(root)))
 tar.add(manifest_path,arcname='source-manifest.json')
print(json.dumps({'release':release,'archive':str(archive),'manifest':str(manifest_path),'files':len(files),'archive_bytes':archive.stat().st_size}))
