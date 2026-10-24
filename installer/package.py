"""Package a locally built runtime. Never reads user profiles or game data."""
from pathlib import Path
import argparse,hashlib,io,json,re,zipfile
parser=argparse.ArgumentParser()
parser.add_argument('--runtime',type=Path,required=True)
parser.add_argument('--python',dest='python_dir',type=Path,required=True,help='Official Windows x64 Python 3.12 embeddable package, extracted')
args=parser.parse_args();here=Path(__file__).resolve().parent;root=here.parent
files={}
# Explicit allowlist: no configuration, save, log or arbitrary runtime-directory file.
required=['mcla.exe','rexgpu-xenos.dll','rexruntime.dll','amd_fidelityfx_dx12.dll','amd_fidelityfx_vk.dll','amd_fidelityfx_loader_dx12.dll','amd_fidelityfx_upscaler_dx12.dll','amd_fidelityfx_framegeneration_dx12.dll']
optional=['concrt140.dll','msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_atomic_wait.dll','msvcp140_codecvt_ids.dll','vccorlib140.dll','vcruntime140.dll','vcruntime140_1.dll','vcruntime140_threads.dll']
for name in required+optional:
 p=args.runtime/name
 if p.is_file():files['payload/runtime/'+name]=p.read_bytes()
 elif name in required:raise FileNotFoundError(p)
files['payload/runtime/game.ico']=(here/'source/assets/setup.ico').read_bytes()
files['payload/runtime/AMD-FSR-LICENSE.md']=(args.runtime/'AMD-FSR-LICENSE.md').read_bytes()
for name in ['LICENSE','CREDITS.md','THIRD-PARTY-NOTICES.md']:files['payload/licenses/'+name]=(root/name).read_bytes()
files['payload/licenses/ReXGlue-LICENSE.txt']=(root/'third_party/rexglue-sdk/LICENSE').read_bytes()
for p in args.python_dir.iterdir():
 if p.is_file() and p.name!='python.cat':files['tools/python/'+p.name]=p.read_bytes()
for name in ['python.exe','python312.dll','python312.zip','python312._pth','LICENSE.txt']:
 if 'tools/python/'+name not in files:raise FileNotFoundError(name)
# Preserve Python notices outside the internal tool package too.
files['payload/licenses/Python-LICENSE.txt']=(args.python_dir/'LICENSE.txt').read_bytes()
project=io.BytesIO()
inputs=['scripts/extract_game.py','scripts/configure_install.py','localization/build_ptbr.py','localization/pt-BR/native-texts.json','localization/pt-BR/dialogue-pt-BR.json','localization/pt-BR/subtitle-files.json','launcher/dev/shaderpack/build_pack.py','third_party/rexglue-sdk/src/system/xex_module.cpp','third_party/rexglue-sdk/LICENSE']
with zipfile.ZipFile(project,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n in inputs:z.writestr(n,(root/n).read_bytes())
files['payload/project.zip']=project.getvalue();files['compact_prepare.py']=(here/'source/compact_prepare.py').read_bytes()
manifest={'format':1,'identity':'mcla-la-recompiled','runtime_version':'FSR 4.1.2 / Frame Generation 4.0.2','isolated_user_profile':True,'files':[{'path':n,'size':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(files.items())]}
files['payload/manifest.json']=json.dumps(manifest,indent=2).encode()
package=here/'bundle.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n,b in sorted(files.items()):z.writestr(n,b)
hash=hashlib.sha256(package.read_bytes()).hexdigest();core=here/'source/Core.cs';text=core.read_text(encoding='utf8');core.write_text(re.sub(r'public const string Hash = "[0-9a-f]+";', 'public const string Hash = "'+hash+'";',text),encoding='utf8')
print('Pacote interno criado. Execute installer/source/build.ps1 para gerar o instalador/configurador.')
