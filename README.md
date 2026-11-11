# HAWB for Home Assistant

A Home Assistant integration that connects straight to the [HAWB](https://github.com/TheZubaidi/HAWB) agent on a Windows PC. **No MQTT broker needed.** Home Assistant finds the PC by itself (zeroconf), you type a six-digit pairing code once, and every sensor, button, switch and setting HAWB offers shows up as a native entity. You also get a real media player and a notify entity.

Use this **or** HAWB's MQTT mode for a given PC, not both, or you will see every entity twice.

## Install

1. In HACS, add this repository as a custom repository (category **Integration**), then install **HAWB**. Restart Home Assistant.
   Manual install: copy `custom_components/hawb` into your Home Assistant `config/custom_components` folder.
2. On the PC, open HAWB's settings, **Connection**, and switch on **Home Assistant integration**. Save. Allow HAWB through Windows Firewall on private networks when asked.
3. In Home Assistant, a **HAWB** device appears under **Settings, Devices & services** ("Discovered"). If it does not, press **Add integration**, choose HAWB and enter the PC's address.
4. In HAWB's settings press **Show pairing code** and type the code into Home Assistant. Codes work once and expire after five minutes.

## What you get

| In Home Assistant | From the PC |
|---|---|
| Sensors, binary sensors | CPU, memory, disks, battery, network, active window, webcam/microphone in use, and so on |
| Buttons, switches, numbers, selects, text | Lock, sleep, volume, mute, speak, play a URL, custom commands |
| `media_player.<pc>` | What is playing, play/pause/next/previous, volume, mute, play media or text-to-speech from Home Assistant's media browser |
| `notify.<pc>_notify` | `notify.send_message` shows a Windows toast |
| `hawb.send_rich_notification` | Toasts with image, icon, up to five buttons, reply box and tag |
| Event entities | Notification button presses and replies, hotkeys |

Disabling a sensor in HAWB removes its entity from Home Assistant, and enabling it brings it back.

### Rich notification example

```yaml
action: hawb.send_rich_notification
target:
  entity_id: notify.desk_pc_notify
data:
  title: Front door
  message: Someone is at the door
  image: http://homeassistant.local:8123/local/door.jpg
  actions:
    - action: open_door
      title: Open
```

Press events arrive on the PC's *Notification action* event entity.

## Security

* The port is closed until you switch the integration on in HAWB, and only answers Home Assistant instances paired with a code.
* Pairing codes are random, single use, expire after five minutes and are thrown away after five wrong guesses.
* HAWB stores only a hash of each token. **Remove all pairings** in HAWB's settings cuts every Home Assistant off at once.
* The connection is plain `ws://` on your local network, like MQTT without TLS. Do not expose the port to the internet.

## Protocol

The wire format is described at the top of [`crates/hawb-agent/src/localapi.rs`](https://github.com/TheZubaidi/HAWB/blob/main/crates/hawb-agent/src/localapi.rs). Protocol version 1.
