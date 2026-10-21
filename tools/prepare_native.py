"""Stage or remove only Calm Home's SDK helper on the exact supported TV."""
import argparse,json,sys
from pathlib import Path,PurePosixPath
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from tools.family_session import load
from tools.guard import assert_target

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-approved-root',action='store_true')
    parser.add_argument('--cleanup',action='store_true')
    args=parser.parse_args()
    if not args.owner_approved_root:parser.error('Read the advanced guide and obtain owner approval first.')
    session=load(PROJECT);sys.path.insert(0,str(Path(session['root_source'])/'src'))
    from samsung_tv_root.sdb import SdbClient
    client=SdbClient(Path(session['sdb']),session['tv_ip'],timeout=12);client.connect();client.require_device()
    listing=client.run(('devices',),check=True).stdout
    row=next(line.split() for line in listing.splitlines() if line.split() and line.split()[0]==client.serial)
    release=client.capture('cat /etc/os-release',timeout=15).output
    build=next(line.split('=',1)[1] for line in release.splitlines() if line.startswith('BUILD_ID='))
    assert_target({'model':row[2],'build':build,'address':session['tv_ip']},
                  {'model':'UN65CU7000DXZA','build':'T-KSU2ECAKUC-0080-REL-202412040254','address':session['tv_ip']})
    remote=PurePosixPath('/home/owner/share/tmp/sdk_tools/calm-home-integration')
    names=['CalmHomeTool.dll','CalmHomeTool.deps.json','CalmHomeTool.runtimeconfig.json']
    if args.cleanup:
        command='rm -f -- '+' '.join(str(remote/name) for name in names)+'; rmdir '+str(remote)
    else:
        paths=[PROJECT/'.setup/native'/name for name in names]
        if not all(path.is_file() for path in paths):raise ValueError('Build native/HomeTool.csproj into .setup/native first.')
        result=client.capture('mkdir -p '+str(remote),timeout=15).output
        if '[exit:0]' not in result:raise RuntimeError('Could not create the dedicated SDK helper directory.')
        for path,name in zip(paths,names):client.push(path,remote/name)
        command='/usr/bin/dotnet '+str(remote/'CalmHomeTool.dll')+' inspect'
    result=client.capture(command,timeout=15).output
    if '[exit:0]' not in result:raise RuntimeError('Helper action failed: '+result)
    print(result)

if __name__=='__main__':
    try:main()
    except Exception as error:print('Stopped: '+str(error),file=sys.stderr);raise SystemExit(1)
