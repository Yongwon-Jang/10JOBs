import pytest

from ten_jobs.algorithms.devices import DeviceError, DeviceHub


def test_switch_on_off_toggle():
    hub = DeviceHub()
    assert hub.apply({'device': 'light_living', 'action': 'on'}).on
    assert not hub.apply({'device': 'light_living', 'action': 'toggle'}).on


def test_aircon_temperature_range():
    hub = DeviceHub()
    ac = hub.apply({'device': 'aircon', 'action': 'set', 'value': 22})
    assert ac.on and ac.value == 22
    with pytest.raises(DeviceError):
        hub.apply({'device': 'aircon', 'action': 'set', 'value': 40})


def test_curtain_percent_and_on_off():
    hub = DeviceHub()
    assert hub.apply({'device': 'curtain', 'action': 'on'}).value == 100
    c = hub.apply({'device': 'curtain', 'action': 'set', 'value': 0})
    assert c.value == 0 and not c.on


def test_switch_rejects_value_and_unknown_inputs():
    hub = DeviceHub()
    with pytest.raises(DeviceError):
        hub.apply({'device': 'tv', 'action': 'set', 'value': 3})
    with pytest.raises(DeviceError):
        hub.apply({'device': 'fridge', 'action': 'on'})
    with pytest.raises(DeviceError):
        hub.apply({'device': 'tv', 'action': 'explode'})
    with pytest.raises(DeviceError):
        hub.apply({'device': 'aircon', 'action': 'set', 'value': 'cold'})


def test_all_off_for_leaving_home():
    hub = DeviceHub()
    for d in ('light_living', 'tv', 'curtain'):
        hub.apply({'device': d, 'action': 'on'})
    hub.apply({'device': 'tv', 'action': 'all_off'})
    assert not any(d['on'] for d in hub.snapshot())
