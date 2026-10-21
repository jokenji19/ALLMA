from unittest.mock import Mock
import json
from allma_model.ui.system_notifications import SystemNotifications


def backend(allowed=True):
    return Mock(allowed=Mock(return_value=allowed), post=Mock(return_value=True))


def test_system_permission_alone_is_not_user_consent(tmp_path):
    native = backend()
    obj = SystemNotifications(tmp_path/'notifications.json', native)
    assert not obj.status()['active']
    assert not obj.publish('message')
    native.post.assert_not_called()
    native.request.assert_not_called()


def test_opt_in_persisted_and_explicit_disable_cancels_notifications(tmp_path):
    native = backend()
    path = tmp_path/'notifications.json'
    obj = SystemNotifications(path, native)
    changes = []
    obj.configure(True, changes.append)
    assert changes[-1]['active'] and obj.publish('message')
    assert SystemNotifications(path, native).enabled
    obj.configure(False, changes.append)
    assert not changes[-1]['active'] and not obj.publish('test', explicit_test=True)
    native.cancel.assert_called_once()
    assert json.loads(path.read_text())['enabled'] is False


def test_denial_never_enables_notifications(tmp_path):
    native = backend(False)
    native.request.side_effect = lambda callback: callback(False)
    obj = SystemNotifications(tmp_path/'notifications.json', native)
    updates = []
    obj.configure(True, updates.append)
    assert not updates[-1]['active'] and not obj.enabled
    assert not obj.publish('message')
    native.post.assert_not_called()


def test_late_permission_result_cannot_override_disable(tmp_path):
    native = backend(False)
    callbacks = []
    native.request.side_effect = callbacks.append
    obj = SystemNotifications(tmp_path/'notifications.json', native)
    updates = []
    obj.configure(True, updates.append)
    obj.configure(False, updates.append)
    native.allowed.return_value = True
    callbacks[0](True)
    assert not obj.enabled
    assert not json.loads(obj.path.read_text())['enabled']


def test_permission_or_channel_revoked_is_checked_at_each_send(tmp_path):
    native = backend()
    obj = SystemNotifications(tmp_path/'notifications.json', native)
    obj.configure(True, lambda _: None)
    native.allowed.return_value = False
    assert obj.status()['enabled'] and not obj.status()['active']
    assert not obj.publish('dream')
    native.post.assert_not_called()


def test_rate_limit_survives_restart_and_test_is_explicit(tmp_path):
    native = backend()
    now = [1000.0]
    path = tmp_path/'notifications.json'
    obj = SystemNotifications(path, native, clock=lambda: now[0])
    obj.configure(True, lambda _: None)
    assert obj.publish('message')
    restored = SystemNotifications(path, native, clock=lambda: now[0])
    assert not restored.publish('message', explicit_test=True)
    assert restored.publish('test', explicit_test=True)
    assert restored.publish('test', explicit_test=True)
    now[0] += 600
    assert restored.publish('message')


def test_invalid_preference_and_implicit_consent_are_rejected(tmp_path):
    path = tmp_path/'notifications.json'
    path.write_text('not json')
    obj = SystemNotifications(path, backend())
    assert not obj.enabled
    import pytest
    with pytest.raises(ValueError):
        obj.configure('true', lambda _: None)
    assert not obj.publish('unknown')


def test_failed_post_does_not_consume_cooldown(tmp_path):
    native = backend()
    obj = SystemNotifications(tmp_path/'notifications.json', native)
    obj.configure(True, lambda _: None)
    native.post.return_value = False
    assert not obj.publish('model')
    native.post.return_value = True
    assert obj.publish('model')
