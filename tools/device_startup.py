"""Guarded one-shot startup configuration; no daemon, boot script, or binary edits."""
import argparse,asyncio,datetime,hashlib,json,sys
from pathlib import Path
from guard import assert_target,assert_baseline
from startup_policy import ORIGINAL,ENABLED,READ,parse_values,settings_script,validate_home

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
STATE=PROJECT/'.setup'
HELPER='/usr/bin/dotnet /home/owner/share/tmp/sdk_tools/calm-home-integration/CalmHomeTool.dll inspect'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('action',choices=['enable','restore'])
parser.add_argument('--owner-approved-root',action='store_true',help='Only after the TV owner explicitly approves temporary root and the recovery plan.')
args=parser.parse_args()
if not args.owner_approved_root:parser.error('The owner must approve temporary root and recovery before this action.')
from tools.family_session import load
SESSION=load(PROJECT)
STATE=PROJECT/'.setup'
TV_IP=SESSION['tv_ip']; HOST_IP=SESSION['host_ip']; SDB=Path(SESSION['sdb'])
PAYLOADS=Path(SESSION['payloads'])
sys.path.insert(0,str(Path(SESSION['root_source'])/'src'))
from samsung_tv_root import archive_root
from samsung_tv_root.sdb import SdbClient

before,after=(ORIGINAL,ENABLED) if args.action=='enable' else (ENABLED,ORIGINAL)
boot_hash=json.loads((PROJECT/'compatibility.json').read_text())['bootManagerSha256']
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
path=STATE/'recovery'/stamp/'startup-operation.json';path.parent.mkdir(parents=True)
record={'action':args.action,'before':before,'after':after,'boot_manager_sha256':boot_hash,'status':'started'}
def save():path.write_text(json.dumps(record,indent=2)+'\n')
async def main():
    save()
    try:
        client=SdbClient(SDB,TV_IP,timeout=12)
        client.connect();client.require_device()
        listing=client.run(('devices',),check=True).stdout
        row=next(line.split() for line in listing.splitlines() if line.startswith(client.serial+'\t') or line.startswith(client.serial+' '))
        release=client.capture('cat /etc/os-release',timeout=15).output
        build=next(line.split('=',1)[1] for line in release.splitlines() if line.startswith('BUILD_ID='))
        assert_target({'model':row[2],'build':build,'address':row[0].split(':')[0]},
                      {'model':'UN65CU7000DXZA','build':'T-KSU2ECAKUC-0080-REL-202412040254','address':TV_IP})
        native=client.capture(HELPER,timeout=15).output
        native=json.loads(next(line for line in native.splitlines() if line.startswith('{')))
        validate_home(args.action,native)
        actual=parse_values(client.capture(READ,timeout=15).output)
        if actual!=before:raise ValueError('startup baseline mismatch')
        record['sdk_baseline']=actual;save()
        evidence=await archive_root.probe(TV_IP,model='UN65CU7000DXZA',callback_host=HOST_IP,bind_host=HOST_IP,sdb_timeout=12,accept_timeout=20,command_timeout=20,
            commands=(settings_script(before,after,boot_hash),READ,HELPER),payloads=PAYLOADS)
        record['evidence']=evidence;save()
        results=evidence.get('commands',[])
        if len(results)!=3 or any(x.get('exit_code')!=0 or x.get('timed_out') for x in results):raise ValueError('startup command failed; inspect recovery readback')
        actual=parse_values(results[1]['stdout'])
        if actual!=after:raise ValueError('startup restore/readback mismatch')
        record['readback']=actual;record['status']='verified_and_session_closed'
    except Exception as error:record.update(status='failed',error=type(error).__name__+': '+str(error))
    finally:save();print(record['status'],str(path),flush=True)
    return 0 if record['status']=='verified_and_session_closed' else 1
raise SystemExit(asyncio.run(main()))
