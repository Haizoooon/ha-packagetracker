# Automation examples

All examples assume the integration is configured. Events contain the full parcel data, so no template sensors are required.

## 1. Push notification on delivery

```yaml
alias: Parcel delivered
description: Send a push message with product, merchant and carrier.
trigger:
  - platform: event
    event_type: package_tracker_package_delivered
action:
  - action: notify.mobile_app_phone
    data:
      title: Parcel delivered
      message: >-
        {{ trigger.event.data.product_name }} from
        {{ trigger.event.data.merchant }} was delivered.
        Carrier: {{ trigger.event.data.carrier_name or 'unknown' }}.
      data:
        url: "{{ trigger.event.data.tracking_url }}"
        tag: "package_{{ trigger.event.data.package_id }}"
mode: queued
```

## 2. Hallway light on “out for delivery”

```yaml
alias: Parcel out for delivery – hallway light
trigger:
  - platform: event
    event_type: package_tracker_package_out_for_delivery
action:
  - action: light.turn_on
    target:
      entity_id: light.hallway
    data:
      brightness_pct: 40
      color_name: green
  - delay: "00:10:00"
  - action: light.turn_off
    target:
      entity_id: light.hallway
```

## 3. Morning dashboard notification

```yaml
alias: Delivery today
trigger:
  - platform: time
    at: "07:30:00"
condition:
  - condition: state
    entity_id: binary_sensor.package_tracker_delivery_today
    state: "on"
action:
  - action: persistent_notification.create
    data:
      title: Delivery today
      message: >-
        {{ state_attr('sensor.package_tracker_next_delivery', 'product_name') }}
        from {{ state_attr('sensor.package_tracker_next_delivery', 'merchant') }}
        is expected today
        {% if state_attr('sensor.package_tracker_next_delivery', 'delivery_window') %}
        ({{ state_attr('sensor.package_tracker_next_delivery', 'delivery_window') }})
        {% endif %}.
```

## 4. Report a delay

```yaml
alias: Parcel delayed
trigger:
  - platform: event
    event_type: package_tracker_package_delayed
action:
  - action: notify.mobile_app_phone
    data:
      title: Parcel delayed
      message: >-
        {{ trigger.event.data.product_name }} from
        {{ trigger.event.data.merchant }} is delayed.
        {% if trigger.event.data.expected_delivery %}
        New estimate: {{ trigger.event.data.expected_delivery }}.
        {% endif %}
```

## 5. New parcel detected → refresh overview

```yaml
alias: New parcel detected
trigger:
  - platform: event
    event_type: package_tracker_package_found
action:
  - action: homeassistant.update_entity
    target:
      entity_id:
        - sensor.package_tracker_packages
        - sensor.package_tracker_packages_in_transit
  - action: persistent_notification.create
    data:
      title: New parcel
      message: >-
        {{ trigger.event.data.product_name or 'A parcel' }}
        from {{ trigger.event.data.merchant or 'a merchant' }}
        was detected.
```

## 6. Ready for pickup

```yaml
alias: Parcel ready for pickup
trigger:
  - platform: event
    event_type: package_tracker_package_ready_for_pickup
action:
  - action: notify.mobile_app_phone
    data:
      title: Parcel ready for pickup
      message: >-
        {{ trigger.event.data.product_name }} is ready for pickup.
        {% if trigger.event.data.tracking_url %}
        Tracking: {{ trigger.event.data.tracking_url }}
        {% endif %}
```

## 7. Condition: DHL only

```yaml
alias: DHL parcel delivered
trigger:
  - platform: event
    event_type: package_tracker_package_delivered
condition:
  - condition: template
    value_template: "{{ trigger.event.data.carrier == 'dhl' }}"
action:
  - action: notify.mobile_app_phone
    data:
      title: DHL parcel delivered
      message: "{{ trigger.event.data.product_name }}"
```

## 8. Condition: product contains “mouse”

```yaml
condition:
  - condition: template
    value_template: >-
      {{ 'mouse' in (trigger.event.data.product_name or '') | lower }}
```

## 9. Refresh tracking when arriving home

```yaml
alias: Refresh tracking when waking up
trigger:
  - platform: state
    entity_id: person.max
    to: home
action:
  - action: package_tracker.refresh_tracking
mode: single
```

> Retention of old parcels is handled by the “Keep delivered parcels” option. `delete_all_data` is a manual emergency tool and should not run automatically.

## 10. Sync Gmail when the house becomes active

```yaml
alias: Sync parcels when waking up
trigger:
  - platform: state
    entity_id: input_boolean.house_active
    to: "on"
action:
  - action: package_tracker.sync
```

## 11. Use device triggers in the UI

1. Trigger → **Device** → **Package Tracker**.
2. Choose a trigger type, e.g. **Parcel delivered**.
3. Optionally enter a parcel ID as a filter.
4. Choose an action; the event data is available as `trigger.event.data`.

Device conditions (carrier, merchant, product, delivery today, status) can also be selected directly in the UI.
