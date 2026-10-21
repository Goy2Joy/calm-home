#!/usr/bin/env python3
"""Calm Home setup helper. Python 3.10+, standard library only. See AGENT_SETUP.md."""
from __future__ import annotations
import argparse,hashlib,ipaddress,json,os,platform,re,shutil,subprocess,sys,urllib.parse,urllib.request,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'.setup'
DOWNLOADS=json.loads((ROOT/'tools/downloads.json').read_text())

def tv_address(value):
    address=ipaddress.ip_address(value)
    networks=[ipaddress.ip_network(n) for n in ['10.0.0.0/8','172.16.0.0/12','192.168.0.0/16']]
    if address.version!=4 or not any(address in n for n in networks):
        raise ValueError('Enter the TV’s local IPv4 address from its Network Status screen.')
    return str(address)

def check_download_url(url):
    if url not in [entry['url'] for entry in DOWNLOADS.values()]:
        raise ValueError('Download URL is outside the pinned official installer list.')
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname!='download.tizen.org' or parsed.username or parsed.password:
        raise ValueError('Only HTTPS downloads from download.tizen.org are allowed.')

class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        check_download_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def verify_download(path,entry):
    if path.stat().st_size!=entry['bytes']:raise ValueError('Installer size mismatch; keep the file for inspection and download again to a new location.')
    digest=hashlib.file_digest(path.open('rb'),'sha256').hexdigest() if hasattr(hashlib,'file_digest') else hashlib.sha256(path.read_bytes()).hexdigest()
    if entry.get('sha256') and digest!=entry['sha256']:raise ValueError('Installer checksum mismatch.')
    return digest

def sdk_root(explicit=None):
    candidates=[]
    if explicit:candidates.append(Path(explicit).expanduser())
    if os.environ.get('TIZEN_STUDIO'):candidates.append(Path(os.environ['TIZEN_STUDIO']).expanduser())
    executable=shutil.which('sdb')
    if executable:candidates.append(Path(executable).resolve().parents[1])
    candidates.extend([Path.home()/'tizen-studio',Path('C:/tizen-studio')])
    for path in candidates:
        sdb=path/'tools'/('sdb.exe' if platform.system()=='Windows' else 'sdb')
        if sdb.is_file():return path.resolve()
    return None

def sdk_tools(explicit=None):
    root=sdk_root(explicit)
    if root is None:raise RuntimeError('Tizen Studio not found. Run download-tools, complete its official installer, then doctor.')
    windows=platform.system()=='Windows'
    sdb=root/'tools'/('sdb.exe' if windows else 'sdb')
    tizen=root/'tools/ide/bin'/('tizen.bat' if windows else 'tizen')
    if not tizen.is_file():raise RuntimeError('Install the TV web tools in Tizen Package Manager first.')
    return sdb,tizen

def run(arguments,timeout=180):
    # Only local tools and fixed argument lists; never evaluate TV-provided strings as commands.
    result=subprocess.run([str(x) for x in arguments],text=True,capture_output=True,timeout=timeout)
    if result.returncode:raise RuntimeError((result.stderr or result.stdout or 'Tool failed').strip())
    return result.stdout

def check_sdb_connect(output,code):
    if code or re.search(r'\berror\b|failed to connect',output,re.I):raise RuntimeError('Developer connection failed: '+output.strip())

def connect(address,explicit=None):
    address=tv_address(address);sdb,_=sdk_tools(explicit);serial=address+':26101'
    result=subprocess.run([str(sdb),'connect',serial],text=True,capture_output=True,timeout=25)
    check_sdb_connect(result.stdout+result.stderr,result.returncode)
    listing=run([sdb,'devices'])
    row=next((line.split() for line in listing.splitlines() if line.split() and line.split()[0]==serial),None)
    if not row or len(row)<3 or row[1]!='device':raise RuntimeError('The TV is not ready in the developer-device list.')
    return serial,row[2]

def download_tools(system=None,dry_run=False):
    system=system or platform.system()
    if system not in DOWNLOADS:raise RuntimeError('This helper supports macOS and Windows. Other systems require a separately checked setup.')
    entry=DOWNLOADS[system];check_download_url(entry['url'])
    target=STATE/'downloads'/Path(urllib.parse.urlsplit(entry['url']).path).name
    if dry_run:return {'platform':system,'url':entry['url'],'destination':str(target),'bytes':entry['bytes'],'status':entry['status']}
    if sdk_root():return {'status':'Tizen Studio already exists; reuse it. Run doctor.'}
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():return {'file':str(target),'sha256':verify_download(target,entry),'cached':True}
    partial=target.with_suffix(target.suffix+'.part-'+str(os.getpid()))
    try:
        opener=urllib.request.build_opener(OfficialRedirects())
        total=0
        with opener.open(entry['url'],timeout=30) as response,partial.open('xb') as output:
            check_download_url(response.geturl())
            while True:
                chunk=response.read(256*1024)
                if not chunk:break
                total+=len(chunk)
                if total>entry['bytes']:raise ValueError('Installer exceeds its pinned size.')
                output.write(chunk)
        digest=verify_download(partial,entry);partial.replace(target)
        return {'file':str(target),'sha256':digest,'next':'Open the official installer. The owner handles its license and any OS permission prompts.'}
    finally:
        if partial.exists():partial.unlink()

def configure(environment):
    key=os.environ.get(environment,'').strip()
    if not re.fullmatch('[0-9a-fA-F]{32}',key):raise ValueError('The named environment variable must contain a valid TMDB API key. Do not put the key in command arguments.')
    STATE.mkdir(exist_ok=True)
    try:STATE.chmod(0o700)
    except OSError:pass
    path=STATE/'config.json';path.write_text(json.dumps({'tmdbKey':key})+'\n')
    try:path.chmod(0o600)
    except OSError:pass
    return {'status':'Personal TMDB key saved locally under .setup; it will not be printed.'}

def build(profile,explicit=None):
    if not re.fullmatch('[A-Za-z0-9_-]{1,64}',profile):raise ValueError('Use a simple certificate profile name, such as CalmHome.')
    _,tizen=sdk_tools(explicit)
    source=STATE/'build-src';destination=STATE/'build';signed=STATE/'signed'
    for directory in [source,destination,signed]:
        if directory.exists():shutil.rmtree(directory)  # Only this helper's generated build directories.
    shutil.copytree(ROOT/'app',source)
    private=STATE/'config.json'
    if private.is_file():
        personal=json.loads(private.read_text());key=personal.get('tmdbKey','')
        if not re.fullmatch('[0-9a-fA-F]{32}',key):raise ValueError('Invalid local TMDB key.')
        path=source/'config.js';config=path.read_text()
        config=re.sub(r'("tmdbKey"\s*:\s*)"[^"]*"',lambda m:m.group(1)+json.dumps(key),config)
        path.write_text(config)
    sys.path.insert(0,str(ROOT/'tools'))
    from package import validate_assets
    inventory=validate_assets(source)
    run([tizen,'build-web','-out',destination,'--',source])
    run([tizen,'package','-t','wgt','-s',profile,'-o',signed,'--',destination])
    package=signed/'Calm Home.wgt'
    if not package.is_file():raise RuntimeError('Signing did not produce Calm Home.wgt.')
    return {'package':str(package),'version':inventory['version'],'next':'Install this personal package only on the TV included in your certificate.'}

def advanced_session(args):
    sdb,_=sdk_tools(args.sdk)
    state={'tv_ip':tv_address(args.tv_ip),'host_ip':tv_address(args.host_ip),'sdb':str(sdb),
           'root_source':str(Path(args.root_source).resolve()),'payloads':str(Path(args.payloads).resolve())}
    STATE.mkdir(exist_ok=True)
    path=STATE/'session.json';path.write_text(json.dumps(state,indent=2)+'\n')
    try:path.chmod(0o600)
    except OSError:pass
    return {'status':'Saved local connection paths only; no root operation or TV change performed.','next':'Read docs/advanced-home.md and obtain the TV owner’s explicit approval before advanced integration.'}

def build_advanced():
    from tools.family_session import load
    session=load(ROOT,require_build=False)
    dotnet=shutil.which('dotnet')
    if not dotnet:raise RuntimeError('A Microsoft .NET SDK is required. See docs/advanced-home.md.')
    source=Path(session['root_source']);payloads=STATE/'root-payloads';native=STATE/'native'
    for directory in [payloads,native,source/'payloads/common/obj',source/'payloads/common/bin',ROOT/'native/obj',ROOT/'native/bin']:
        if directory.exists():shutil.rmtree(directory)
    # Fixed projects, pinned C#/project inputs, no inherited Directory.Build hooks.
    projects=[(source/'payloads/common/SamsungTvArchiveRoot.csproj',payloads),
              (source/'payloads/common/SamsungTvRootAgent.csproj',payloads),
              (ROOT/'native/HomeTool.csproj',native)]
    for project,destination in projects:
        run([dotnet,'build',project,'-c','Release','-o',destination,'-p:ImportDirectoryBuildProps=false','-p:ImportDirectoryBuildTargets=false'],timeout=240)
    inputs=json.loads((ROOT/'tools/root-build-inputs.json').read_text())
    record={'rootSourceCommit':json.loads((ROOT/'compatibility.json').read_text())['rootSourceCommit'],'inputs':inputs,'nativeInputs':json.loads((ROOT/'tools/native-build-inputs.json').read_text()),'outputs':{},'dotnetSdk':run([dotnet,'--version']).strip()}
    for directory,stems in [(payloads,['SamsungTvRootAgent','SamsungTvArchiveRoot']),(native,['CalmHomeTool'])]:
        for stem in stems:
            for suffix in ['.dll','.deps.json','.runtimeconfig.json']:
                path=directory/(stem+suffix)
                if not path.is_file():raise RuntimeError('Build output missing: '+path.name)
                record['outputs'][path.relative_to(STATE).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    (STATE/'payload-build.json').write_text(json.dumps(record,indent=2)+'\n')
    load(ROOT)
    return {'status':'Reviewed-source build and output hashes verified locally. No TV connection or root operation performed.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',help='Existing Tizen Studio directory; optional.')
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('doctor')
    p=sub.add_parser('download-tools');p.add_argument('--dry-run',action='store_true');p.add_argument('--platform',choices=['Darwin','Windows'])
    p=sub.add_parser('configure');p.add_argument('--tmdb-env',default='CALM_TMDB_KEY')
    p=sub.add_parser('build');p.add_argument('--profile',required=True)
    p=sub.add_parser('advanced-session');p.add_argument('--tv-ip',required=True);p.add_argument('--host-ip',required=True);p.add_argument('--root-source',required=True);p.add_argument('--payloads',required=True)
    sub.add_parser('build-advanced')
    for action in ['connect','install','launch','disconnect']:
        p=sub.add_parser(action);p.add_argument('--tv-ip',required=True,type=tv_address)
    args=parser.parse_args()
    try:
        if args.action=='doctor':
            root=sdk_root(args.sdk)
            result={'system':platform.system(),'architecture':platform.machine(),'python':platform.python_version(),'sdk':str(root) if root else None,'next':'See AGENT_SETUP.md for TV/certificate steps.'}
        elif args.action=='download-tools':result=download_tools(args.platform,args.dry_run)
        elif args.action=='configure':result=configure(args.tmdb_env)
        elif args.action=='build':result=build(args.profile,args.sdk)
        elif args.action=='advanced-session':result=advanced_session(args)
        elif args.action=='build-advanced':result=build_advanced()
        elif args.action=='disconnect':
            sdb,_=sdk_tools(args.sdk);run([sdb,'disconnect',args.tv_ip+':26101']);run([sdb,'kill-server']);result={'status':'Disconnected and stopped the local SDB server.'}
        else:
            serial,model=connect(args.tv_ip,args.sdk)
            _,tizen=sdk_tools(args.sdk)
            if args.action=='install':
                package=STATE/'signed/Calm Home.wgt'
                if not package.is_file():raise RuntimeError('Build and sign with your own certificate first.')
                with zipfile.ZipFile(package) as archive:
                    if b'id="CalmHome01.Home"' not in archive.read('config.xml'):raise ValueError('Unexpected package identity.')
                run([tizen,'install','-s',serial,'-n',package.name,'--',package.parent])
            elif args.action=='launch':run([tizen,'run','-s',serial,'-p','CalmHome01.Home'])
            result={'status':args.action+' succeeded','model':model,'serial':serial}
        print(json.dumps(result,indent=2));return 0
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired,zipfile.BadZipFile) as error:
        print('Setup stopped: '+str(error),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
