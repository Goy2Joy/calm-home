"""Two exact, reversible startup settings verified on the owner's firmware."""
import re
import shlex

HOME='db/appfw/home_appid'
AUTO='db/menu/smart_hub/ontvsetting/auto_start'
ORIGINAL={HOME:('com.samsung.tv.csfs','String'),AUTO:('0','Int32')}
ENABLED={HOME:('CalmHome01.Home','String'),AUTO:('1','Int32')}
READ='; '.join('vconftool get '+key for key in ORIGINAL)

def validate_home(action,state):
    allowed=['CalmHome01.Home'] if action=='enable' else ['CalmHome01.Home','com.samsung.tv.csfs']
    if action not in ('enable','restore') or state.get('currentCode')!=0 or state.get('currentApp') not in allowed:
        raise ValueError('unexpected native Home baseline')

def parse_values(text):
    values={}
    for line in text.splitlines():
        match=re.fullmatch(r'(db/[^,]+), value = (.*?) \((String|Int32)\)',line)
        if not match:continue
        key,value,kind=match.groups()
        if key not in ORIGINAL or key in values:raise ValueError('unexpected startup readback')
        values[key]=(value,kind)
    if values not in (ORIGINAL,ENABLED):raise ValueError('unknown or incomplete startup baseline')
    return values

def settings_script(before,after,boot_hash):
    if before not in (ORIGINAL,ENABLED) or after not in (ORIGINAL,ENABLED) or before==after:
        raise ValueError('unapproved startup settings')
    if not re.fullmatch('[0-9a-f]{64}',boot_hash):raise ValueError('invalid boot manager hash')
    def setting(key,pair):
        value,kind=pair
        return 'vconftool set -t '+('string' if kind=='String' else 'int')+' -f '+shlex.quote(key)+' '+shlex.quote(value)
    lines=['set -eu','actual=$(sha256sum /usr/bin/app-boot-manager)',
           '[ "${actual%% *}" = '+shlex.quote(boot_hash)+' ] || { echo "boot manager mismatch"; exit 1; }']
    for key,(value,kind) in before.items():
        expected=f'{key}, value = {value} ({kind})'
        lines.append('[ "$(vconftool get '+shlex.quote(key)+')" = '+shlex.quote(expected)+' ] || { echo "startup baseline mismatch"; exit 1; }')
    lines.append('rollback() { trap - EXIT; '+ '; '.join(setting(k,p)+' || true' for k,p in before.items())+'; }')
    lines.append('trap rollback EXIT')
    lines.extend(setting(key,pair) for key,pair in after.items())
    for key,(value,kind) in after.items():
        lines.append('[ "$(vconftool get '+shlex.quote(key)+')" = '+shlex.quote(f'{key}, value = {value} ({kind})')+' ]')
    lines.extend(['trap - EXIT',READ])
    return '\n'.join(lines)
