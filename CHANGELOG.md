# Changelog

## Unreleased

### ⚠️ Breaking

- **Entity states are now stable slugs instead of English labels.** Sensor and
  select states used to be display text baked into the device classes; they are
  now lowercase identifiers translated by Home Assistant at display time. The UI
  reads the same or better, but **automations, scripts, template sensors and
  dashboard conditions that compare against the old strings will stop matching**,
  and history before the upgrade keeps the old values.

  | Entity | Before | After |
  | --- | --- | --- |
  | `select.*_litter_type` | `Bentonite`, `Mixed` | `bentonite`, `mixed` |
  | `select.*_safe_time` | `1 min` … `30 min` | `min_1` … `min_30` |
  | `select.*_action` (C08) | `Clean: start` | `clean_start` |
  | `select.*_action` (litter box) | `Cleaning`, `Pause` | `cleaning`, `pause` |
  | `select.*_garbage` | `Change Bag`, `Reset` | `change_bag`, `reset` |
  | `select.*_box_full_sensitivity` | `Level 1` … `Level 4` | `level_1` … `level_4` |
  | `select.*_mode` (PurePro) | `Flowing mode`, `Eco-mode`, `Smart mode` | `flowing`, `eco`, `smart` |
  | `sensor.cat_*_gender_label` | `Male`, `Neutered male` | `male`, `neutered_male` |

  Values that were already lowercase (`auto`, `manual`, `idle`, `running`,
  `need_reset`, `start`, `pause`, `time`, `empty`) are unchanged.

### Added
- Sign-in by email address, alongside the existing phone number. The config flow
  now starts by asking which one you use.
- Optional server region selector on both sign-in forms. Leaving it on automatic
  keeps the old behaviour of probing every region; choosing one turns a wrong
  password into a single failed login instead of four.
- Italian translation. Entity **names** and enum **states** are both translated
  now (English and Italian), via `has_entity_name` + `translation_key`. Entity
  names lose their hardcoded device-name prefix — Home Assistant composes
  "<device> <entity>" itself — so `Caronte gender_label` becomes `Caronte Gender`
  / `Caronte Sesso`. A test walks every device class and fails if any entity key
  is missing a name or state translation.
- `translations/en.json`, without which none of the config-flow text rendered —
  custom integrations do not read `strings.json` at runtime.
- Docker Compose development stack with debug logging and a remote debugger.

### Fixed
- Devices shared with the account after setup stayed invisible forever: an empty
  device selection was read as "show nothing" rather than "not narrowed down".
- Countdown sensors crashed on every refresh for devices that do not report
  them. The API sends the key with a `null` value, so `dict.get(key, 0)` handed
  back `None` and `int(None)` raised. Affected `deodorant_countdown`,
  `litter_remaining_days`, `total_clean_time` and `last_sync`.
  Countdowns now report **unknown** instead of a misleading `0`; counters still
  default to `0`.
- An account with no devices could be added twice, because the unique ID was
  claimed after the entry was created rather than before.
- Password fields in the config flow were plain text instead of masked.
- The login failure log line included the encrypted password.
- Entity IDs were built with the integration domain (`catlink.c08_4413_state`)
  instead of the platform domain, which Home Assistant warns about once per
  entity per refresh and stops accepting in 2027.5.0. Each entity class now
  declares its own platform domain. The object-id half is unchanged, so existing
  entity IDs keep working exactly as before. ([#61](https://github.com/hasscc/catlink/issues/61))
- Scooper Pro Ultra (`VISUAL_PRO_ULTRA`) had a full device class but was missing
  from `SUPPORTED_DEVICE_TYPES`, so it was labelled "Limited support", never
  pre-selected in the config flow, and in practice never added.
  ([#57](https://github.com/hasscc/catlink/issues/57))

## 2.1.1 - 2026-02-06

### Added
- Open-X/C08 device support (thanks to this nice repo: https://github.com/eulemitkeule/pycatlink)
- Limited Scooper Pro Ultra support
- Reset litter and reset deodorant buttons for litterbox
- Config flow coverage for discovery, reauthentication, and options
- Test suite additions and GitHub Actions workflow for tests

### Fixed
- Device detail parsing fallback when API payloads are incomplete
- Home Assistant 2026.2.0 compatibility issues

### Changed
- Device and entity organization with new helpers and logs mixin
