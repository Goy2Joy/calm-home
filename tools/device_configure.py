"""Run one bounded, owner-authorized Home operation on the exact verified TV.

The native helper guards the build, library hashes and effective Home baseline.
This utility records root-session shutdown/staging checks and never changes a boot record.
"""
import argparse,asyncio,datetime,json,sys
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
STATE=PROJECT/'.setup'
HELPER='/usr/bin/dotnet /home/owner/share/tmp/sdk_tools/calm-home-integration/CalmHomeTool.dll'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('action',choices=['inspect','set-launcher','set-stock'])
parser.add_argument('--expected',choices=['com.samsung.tv.csfs','CalmHome01.Home'])
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
from guard import assert_target, assert_baseline

if args.action!='inspect' and args.expected is None:parser.error('a mutation requires --expected from verified readback')
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
recovery=STATE/'recovery'/stamp
recovery.mkdir(parents=True)
commands=[HELPER+' inspect',"sqlite3 -readonly /opt/dbspace/.appsvc.db 'SELECT * FROM appsvc;'",'vconftool get db/appfw/home_appid','cat /etc/os-release']
if args.action!='inspect':commands=[HELPER+' '+args.action+' 0 '+args.expected,HELPER+' inspect']
record={'action':args.action,'expected':args.expected,'started_utc':stamp,'status':'started'}
path=recovery/'home-operation.json'
def save():path.write_text(json.dumps(record,indent=2)+'\n')
async def main():
    save()
    try:
        client=SdbClient(SDB,TV_IP,timeout=12)
        client.connect()
        listing=client.run(('devices',),check=True).stdout
        device=next((line.split() for line in listing.splitlines() if line.split() and line.split()[0]==client.serial),None)
        if not device or len(device)<3 or device[1]!='device':raise ValueError('target is not ready')
        release=client.capture('cat /etc/os-release',timeout=15).output
        build=next((line.split('=',1)[1] for line in release.splitlines() if line.startswith('BUILD_ID=')),None)
        actual={'model':device[2],'build':build,'address':device[0].split(':')[0]}
        assert_target(actual,{'model':'UN65CU7000DXZA','build':'T-KSU2ECAKUC-0080-REL-202412040254','address':TV_IP})
        record['target']=actual
        raw=client.capture(HELPER+' inspect',timeout=15).output
        baseline=json.loads(next(line for line in raw.splitlines() if line.startswith('{')))
        record['sdk_baseline']=baseline
        if args.action!='inspect':
            assert_baseline({'code':baseline.get('currentCode'),'home':baseline.get('currentApp')},{'code':0,'home':args.expected})
        save()
        record['evidence']=await archive_root.probe(TV_IP,model='UN65CU7000DXZA',callback_host=HOST_IP,bind_host=HOST_IP,sdb_timeout=12,accept_timeout=20,command_timeout=20,commands=tuple(commands),payloads=PAYLOADS)
        results=record['evidence'].get('commands',[])
        if len(results)!=len(commands) or any(row.get('exit_code')!=0 or row.get('timed_out') for row in results):
            raise ValueError('a device command failed; review recorded readback before further changes')
        native=json.loads(next(line for line in results[-1 if args.action!='inspect' else 0]['stdout'].splitlines() if line.startswith('{')))
        record['native_readback']=native
        if args.action!='inspect':
            wanted='CalmHome01.Home' if args.action=='set-launcher' else 'com.samsung.tv.csfs'
            assert_baseline({'code':native.get('currentCode'),'home':native.get('currentApp')},{'code':0,'home':wanted})
        record['status']='verified_and_session_closed'
    except Exception as error:
        record.update(status='failed',error=type(error).__name__+': '+str(error))
    finally:
        save();print(json.dumps(record,indent=2),flush=True);print('Evidence:',path,flush=True)
    return 0 if record['status']=='verified_and_session_closed' else 1
raise SystemExit(asyncio.run(main()))
