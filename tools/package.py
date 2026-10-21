"""Validate the offline TV app and create deterministic, explicitly unsigned input."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

APP_FILES = ('config.xml','core.js','icon.png','index.html','landscape.svg','main.js','styles.css','tv.js')
PRIVILEGES = {'http://tizen.org/privilege/application.launch','http://tizen.org/privilege/tv.window'}
NS = {'w':'http://www.w3.org/ns/widgets','t':'http://tizen.org/ns/widgets'}
FEED_ORIGINS = {'https://api.themoviedb.org','https://image.tmdb.org','https://api.open-meteo.com','https://api.binance.com'}
EXTRA_FILES = {'history.js','saver-policy.js','bridge.js','config.js','coins.js','strings.js','zones.js','data.js','LICENSE-free-my-tv.txt','THIRD-PARTY-NOTICES.txt'}


def approved_name(name):
    if name in APP_FILES or name in EXTRA_FILES:
        return True
    return bool(re.fullmatch(r'(logos|symbols|fonts|aerials)/[A-Za-z0-9_.-]+\.(svg|png|jpg|ttf|txt)',name))


PRIVATE_SUFFIXES = {'.p12','.pfx','.pem','.key','.jks','.keystore','.db','.sqlite'}


class PagePolicy(HTMLParser):
    def __init__(self):
        super().__init__()
        self.policies = []
        self.resources = []

    def handle_starttag(self,tag,attributes):
        attrs=dict(attributes)
        if tag=='meta' and attrs.get('http-equiv','').lower()=='content-security-policy':
            self.policies.append(attrs.get('content',''))
        if tag in ('script','img','link'):
            value=attrs.get('src') if tag!='link' else attrs.get('href')
            if value:
                self.resources.append(value)


def validate_assets(directory: Path) -> dict:
    directory=Path(directory)
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('symlink assets are not allowed: '+path.name)
        if path.is_file() and path.suffix.lower() in PRIVATE_SUFFIXES:
            raise ValueError('private credential or database material in app assets: '+path.name)
    names=sorted(path.relative_to(directory).as_posix() for path in directory.rglob('*') if path.is_file())
    for name in names:
        if not approved_name(name):
            raise ValueError('unapproved app asset: '+name)
        if name.endswith('.svg'):
            svg=(directory/name).read_text()
            if re.search(r'<script|<foreignObject|\bon[a-z]+\s*=|(?:href|src)\s*=\s*[\"\'](?:https?:|//|javascript:)',svg,re.I):
                raise ValueError('executable or remote SVG asset: '+name)
    for name in APP_FILES:
        if not (directory/name).is_file():
            raise ValueError('missing app asset: '+name)
    manifest=ET.parse(directory/'config.xml').getroot()
    app=manifest.find('t:application',NS)
    if app is None or app.get('id')!='CalmHome01.Home' or app.get('package')!='CalmHome01':
        raise ValueError('unexpected application identity')
    if app.get('required_version')!='8.0':
        raise ValueError('unexpected required TV version')
    profile=manifest.find('t:profile',NS)
    if profile is None or profile.get('name')!='tv-samsung':
        raise ValueError('unexpected TV profile')
    content=manifest.find('w:content',NS)
    if content is None or content.get('src')!='index.html':
        raise ValueError('unexpected application entry point')
    privileges={node.get('name') for node in manifest.findall('t:privilege',NS)}
    network='http://tizen.org/privilege/internet' in privileges
    expected_privileges=PRIVILEGES | ({'http://tizen.org/privilege/internet'} if network else set())
    if privileges!=expected_privileges:
        raise ValueError('unapproved or missing privilege')
    origins={node.get('origin') for node in manifest.findall('w:access',NS)}
    if origins and (not network or origins!=FEED_ORIGINS):
        raise ValueError('unapproved network origin')
    if not re.fullmatch(r'\d+\.\d+\.\d+',manifest.get('version','')):
        raise ValueError('invalid application version')
    page=PagePolicy()
    page.feed((directory/'index.html').read_text())
    policies=[{entry.strip().split()[0]:entry.strip().split()[1:] for entry in policy.split(';') if entry.strip()} for policy in page.policies]
    allowed_connections=FEED_ORIGINS-{'https://image.tmdb.org'}
    valid_policy=any(set(policy.get('connect-src',[]))==allowed_connections if network
                     else policy.get('connect-src')==["'none'"] for policy in policies)
    if not valid_policy or (network and origins!=FEED_ORIGINS):
        raise ValueError('network policy is missing or unapproved')
    for resource in page.resources:
        if resource=='$WEBAPIS/webapis/webapis.js':
            continue  # Samsung's exact, documented built-in Product API library.
        parsed=urlsplit(resource)
        if parsed.scheme or parsed.netloc or resource.startswith('//'):
            raise ValueError('remote resource in app entry point')
        if parsed.path not in names:
            raise ValueError('unknown local resource: '+resource)
    if not (directory/'icon.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('icon.png is not a PNG')
    return {'package':'CalmHome01','application':'CalmHome01.Home','version':manifest.get('version'),
            'files':{name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in names}}


def make_unsigned_archive(directory: Path,destination: Path) -> dict:
    directory,destination=Path(directory),Path(destination)
    inventory=validate_assets(directory)
    if destination.resolve().is_relative_to(directory.resolve()):
        raise ValueError('archive destination must be outside app assets')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in inventory['files']:
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            archive.writestr(info,(directory/name).read_bytes())
    inventory['unsigned']=True
    inventory['archive_sha256']=hashlib.sha256(destination.read_bytes()).hexdigest()
    return inventory


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    result=make_unsigned_archive(args.app,args.output)
    args.output.with_suffix('.inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
