"""Verify the patched SDK supplied in the complete source archive."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
manifest=json.loads((root/'.release-source-manifest.json').read_text())
assert manifest['sdk_commit']=='f5337cdc947ff6d4c4196737e2c807a48f2a1fc2'
for entry in manifest['files']:
 path=(root/entry['path']).resolve()
 assert path.is_relative_to(root),entry['path']
 assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],entry['path']
print('SDK source snapshot verified:',len(manifest['files']),'files')
