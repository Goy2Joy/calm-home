"""Fail-closed gates for the exact TV and reversible, individually recorded changes."""
from copy import deepcopy


def assert_target(actual, expected):
    required = ('model', 'build', 'address')
    if any(not isinstance(expected.get(k), str) or not expected[k] or actual.get(k) != expected[k]
           for k in required):
        raise ValueError('target identity mismatch or unknown identity')


def _known(value):
    if value is None:
        return False
    if isinstance(value, dict):
        if 'exists' in value:
            if value.get('verified') is not True or type(value['exists']) is not bool:
                return False
            return not value['exists'] or value.get('value') is not None
        return bool(value) and all(_known(v) for v in value.values())
    return True


def assert_baseline(current, original):
    if not _known(original) or current != original:
        raise ValueError('baseline changed or was never verified')


def operation_record(target, before, after, restore):
    if not target or not _known(before) or not _known(after) or not isinstance(restore, dict) or not restore.get('method'):
        raise ValueError('operation needs a known baseline and explicit restoration method')
    return deepcopy({'target':target,'before':before,'after':after,'restore':restore,
                     'verified':False,'restore_verified':False})


def verify_restore(record, readback):
    if readback != record['before'] or not _known(readback):
        raise ValueError('restore readback mismatch')
    record['restore_verified'] = True
