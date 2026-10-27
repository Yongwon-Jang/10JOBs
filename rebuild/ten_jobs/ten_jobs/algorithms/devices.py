"""Smart home device state machine (lights, air conditioner, TV, curtain ...).

The app sends JSON commands; this module validates them and returns the new state,
so the ROS node only has to publish what this module decides.

    {"device": "light_living", "action": "on"}
    {"device": "aircon", "action": "set", "value": 24}
"""
from dataclasses import dataclass, field


class DeviceError(ValueError):
    pass


@dataclass
class Device:
    name: str
    kind: str                  # switch | thermostat | curtain
    on: bool = False
    value: int | None = None   # temperature (°C) or curtain open %
    min_value: int | None = None
    max_value: int | None = None

    def to_dict(self):
        out = {'device': self.name, 'kind': self.kind, 'on': self.on}
        if self.value is not None:
            out['value'] = self.value
        return out


def default_devices():
    return {d.name: d for d in [
        Device('light_living', 'switch'),
        Device('light_room', 'switch'),
        Device('tv', 'switch'),
        Device('aircon', 'thermostat', value=26, min_value=18, max_value=30),
        Device('curtain', 'curtain', value=0, min_value=0, max_value=100),
    ]}


@dataclass
class DeviceHub:
    devices: dict = field(default_factory=default_devices)

    def apply(self, command: dict) -> Device:
        name = command.get('device')
        action = command.get('action')
        device = self.devices.get(name)
        if device is None:
            raise DeviceError(f'unknown device: {name}')

        if action == 'on':
            device.on = True
            if device.kind == 'curtain':
                device.value = device.max_value
        elif action == 'off':
            device.on = False
            if device.kind == 'curtain':
                device.value = device.min_value
        elif action == 'toggle':
            return self.apply({'device': name, 'action': 'off' if device.on else 'on'})
        elif action == 'set':
            if device.kind == 'switch':
                raise DeviceError(f'{name} does not take a value')
            try:
                value = int(command['value'])
            except (KeyError, TypeError, ValueError):
                raise DeviceError('value must be an integer') from None
            if not device.min_value <= value <= device.max_value:
                raise DeviceError(f'{name} value must be {device.min_value}~{device.max_value}')
            device.value = value
            device.on = device.kind == 'thermostat' or value > device.min_value
        elif action == 'all_off':
            for d in self.devices.values():
                d.on = False
                if d.kind == 'curtain':
                    d.value = d.min_value
            return device
        else:
            raise DeviceError(f'unknown action: {action}')
        return device

    def snapshot(self):
        return [d.to_dict() for d in self.devices.values()]
