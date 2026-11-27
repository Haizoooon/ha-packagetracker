# Beispielautomationen

Alle Beispiele setzen voraus, dass die Integration eingerichtet ist. Die Events enthalten die vollständigen Paketdaten, sodass keine Template-Sensoren nötig sind.

## 1. Push-Benachrichtigung bei Zustellung

```yaml
alias: Paket zugestellt
description: Sendet eine Push-Nachricht mit Produkt, Händler und Paketdienst.
trigger:
  - platform: event
    event_type: package_tracker_package_delivered
action:
  - action: notify.mobile_app_handy
    data:
      title: Paket zugestellt
      message: >-
        {{ trigger.event.data.product_name }} von
        {{ trigger.event.data.merchant }} wurde zugestellt.
        Paketdienst: {{ trigger.event.data.carrier_name or 'unbekannt' }}.
      data:
        url: "{{ trigger.event.data.tracking_url }}"
        tag: "package_{{ trigger.event.data.package_id }}"
mode: queued
```

## 2. Licht bei „in Zustellung“

```yaml
alias: Paket in Zustellung – Flurlicht
trigger:
  - platform: event
    event_type: package_tracker_package_out_for_delivery
action:
  - action: light.turn_on
    target:
      entity_id: light.flur
    data:
      brightness_pct: 40
      color_name: green
  - delay: "00:10:00"
  - action: light.turn_off
    target:
      entity_id: light.flur
```

## 3. Morgendliche Dashboard-Benachrichtigung

```yaml
alias: Heute kommt ein Paket
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
      title: Lieferung heute
      message: >-
        {{ state_attr('sensor.package_tracker_next_delivery', 'product_name') }}
        von {{ state_attr('sensor.package_tracker_next_delivery', 'merchant') }}
        wird heute erwartet
        {% if state_attr('sensor.package_tracker_next_delivery', 'delivery_window') %}
        ({{ state_attr('sensor.package_tracker_next_delivery', 'delivery_window') }})
        {% endif %}.
```

## 4. Verspätung melden

```yaml
alias: Paket verspätet
trigger:
  - platform: event
    event_type: package_tracker_package_delayed
action:
  - action: notify.mobile_app_handy
    data:
      title: Paket verspätet
      message: >-
        {{ trigger.event.data.product_name }} von
        {{ trigger.event.data.merchant }} verspätet sich.
        {% if trigger.event.data.expected_delivery %}
        Neuer Termin: {{ trigger.event.data.expected_delivery }}.
        {% endif %}
```

## 5. Neues Paket → Übersicht aktualisieren

```yaml
alias: Neues Paket erkannt
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
      title: Neues Paket
      message: >-
        {{ trigger.event.data.product_name or 'Ein Paket' }}
        von {{ trigger.event.data.merchant or 'einem Händler' }}
        wurde erkannt.
```

## 6. Abholung in der Packstation

```yaml
alias: Paket abholbereit
trigger:
  - platform: event
    event_type: package_tracker_package_ready_for_pickup
action:
  - action: notify.mobile_app_handy
    data:
      title: Paket abholbereit
      message: >-
        {{ trigger.event.data.product_name }} liegt zur Abholung bereit.
        {% if trigger.event.data.tracking_url %}
        Tracking: {{ trigger.event.data.tracking_url }}
        {% endif %}
```

## 7. Bedingung: nur DHL-Pakete

```yaml
alias: DHL-Paket zugestellt
trigger:
  - platform: event
    event_type: package_tracker_package_delivered
condition:
  - condition: template
    value_template: "{{ trigger.event.data.carrier == 'dhl' }}"
action:
  - action: notify.mobile_app_handy
    data:
      title: DHL-Paket zugestellt
      message: "{{ trigger.event.data.product_name }}"
```

## 8. Bedingung: Produkt enthält „Maus“

```yaml
condition:
  - condition: template
    value_template: >-
      {{ 'maus' in (trigger.event.data.product_name or '') | lower }}
```

## 9. Tracking aktualisieren, wenn das Haus aktiv wird

```yaml
alias: Tracking beim Nachhausekommen aktualisieren
trigger:
  - platform: state
    entity_id: person.max
    to: home
action:
  - action: package_tracker.refresh_tracking
mode: single
```

> Aufräumen alter Pakete übernimmt die Option „Zugestellte Pakete aufbewahren“. `delete_all_data` ist ein manuelles Notfallwerkzeug und sollte nicht automatisch laufen.

## 10. Gmail-Sync nach dem Aufwachen

```yaml
alias: Pakete nach dem Aufwachen synchronisieren
trigger:
  - platform: state
    entity_id: input_boolean.haus_aktiv
    to: "on"
action:
  - action: package_tracker.sync
```

## 11. Geräte-Trigger im UI nutzen

Im Automation-Editor:

1. Trigger → **Gerät** → **Package Tracker**.
2. Trigger-Typ wählen, z. B. **Paket zugestellt**.
3. Optional eine Paket-ID als Filter eintragen.
4. Aktion wählen; die Event-Daten stehen als `trigger.event.data` zur Verfügung.

Die Geräte-Conditions (Paketdienst, Händler, Produkt, Lieferung heute, Status) lassen sich ebenfalls direkt im UI auswählen.
