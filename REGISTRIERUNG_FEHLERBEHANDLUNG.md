# Registrierung mit Fehlerbehandlung

## Überblick

Die Event-Registrierung wurde um eine robuste Fehlerbehandlung erweitert. Wenn die Erstellung eines `EventMember`-Objekts fehlschlägt, wird keine Order/Rechnung erstellt und der Benutzer erhält eine entsprechende Fehlermeldung.

## Problemstellung

### Vorheriger Ablauf (fehleranfällig)

```
1. Order erstellen
2. OrderItems erstellen
3. Invoice erstellen
4. EventMember erstellen ← FEHLER HIER
   → Order bleibt als "verwaistes" Objekt bestehen
```

### Neuer Ablauf (robust)

```
1. Validierung (no_duplicate_check)
2. EventMember für alle Cart-Items erstellen
   → Bei Fehler: Abbruch, keine Order-Erstellung
3. Order erstellen
4. OrderItems erstellen
5. Invoice erstellen
```

## Geänderte Dateien

### 1. `events/views.py`

#### `make_event_registration()` (Zeile ~1077)

**Änderungen:**
- Try/Except-Block um den gesamten Create-Prozess
- `new_member` wird initial auf `None` gesetzt
- Explizite Prüfung: `if new_member is None: raise ValueError(...)`
- Bei Exception: Logging + Fehlermeldung via `messages.error` + `return False`
- Direkter Zugriff auf `new_member.label` statt `EventMember.objects.latest("date_created").label`
- `return True` bei Erfolg

**Beispiel:**
```python
def make_event_registration(request, form, event):
    new_member = None
    
    try:
        personal_data_dict = get_personal_form_data(form)
        if event.registration_form == "s":
            s_data_dict = get_additional_form_data(form, event, "s")
            new_member = EventMember.objects.create(
                event=event, **personal_data_dict, **s_data_dict
            )
        # ... weitere registration_form-Typen ...
        
        if new_member is None:
            raise ValueError("EventMember wurde nicht erstellt")
            
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Fehler bei der Event-Registrierung: {e}")
        
        messages.error(
            request,
            "Bei der Registrierung ist ein Fehler aufgetreten. Bitte versuche es erneut.",
            fail_silently=True,
        )
        return False
    
    # ... weitere Verarbeitung ...
    
    return True
```

#### `handle_form_submission()` (Zeile ~1237)

**Änderungen:**
- Prüft Rückgabewert von `make_event_registration`
- Gibt `False` zurück, wenn Registrierung fehlschlägt

```python
def handle_form_submission(request, form, event):
    if form.is_valid():
        # ... Validierung ...
        if no_duplicate_check(personal_data_dict.get("email"), event):
            if newsletter:
                add_to_newsletter(personal_data_dict.get("email"))
            # Rückgabewert prüfen
            if not make_event_registration(request, form, event):
                return False
        # ...
    return form.is_valid()
```

### 2. `shop/views.py`

#### `OrderCreateView.form_valid()` (Zeile ~204)

**Änderungen:**
- Import von `make_event_registration` hinzugefügt
- Schritt 1: Validierung aller Cart-Items
- Schritt 2: EventMember erstellen (vor Order-Erstellung!)
- Schritt 3: Nur bei Erfolg Order + Invoice erstellen

```python
def form_valid(self, form):
    cart = self.cart
    email = form.cleaned_data.get("email")
    
    # Schritt 1: Validierung
    for item in cart:
        if not no_duplicate_check(email, item["event"]):
            messages.error(self.request, f"Für '{item['event'].name}' existiert bereits eine Anmeldung...")
            return self.form_invalid(form)
    
    # Schritt 2: EventMember erstellen
    for item in cart:
        if not make_event_registration(self.request, form, item["event"]):
            return self.form_invalid(form)
    
    # Schritt 3: Order erstellen (nur wenn Schritt 1+2 erfolgreich)
    if len(split_cart(cart)[0]) > 0:
        order = create_order(form, email)
        # ... OrderItems, Invoice ...
    
    cart.clear()
    return super().form_valid(form)
```

## Fehlerbehandlung

### Fehlerfälle

| Fehler | Verhalten |
|--------|-----------|
| `EventMember.objects.create()` schlägt fehl | Exception wird gefangen, Fehlermeldung angezeigt, keine Order |
| `new_member` ist `None` nach Create | `ValueError` wird ausgelöst, gleiche Behandlung wie oben |
| Duplicate Email | Fehlermeldung vor EventMember-Erstellung, keine Order |
| Datenbank-Fehler | Exception wird gefangen, Logging, Fehlermeldung |

### Benutzer-Feedback

- **Fehlermeldung:** "Bei der Registrierung ist ein Fehler aufgetreten. Bitte versuche es erneut."
- **Verhalten:** Formular bleibt mit eingegebenen Daten erhalten
- **Logging:** Fehler werden im Logger protokolliert (für Debugging)

## Testing

### Manuelle Tests

1. **Normalfall:** Registrierung funktioniert → Order + Invoice + EventMember erstellt
2. **Duplicate Email:** Fehlermeldung vor Order-Erstellung
3. **DB-Fehler simulieren:** z.B. Constraint-Verletzung → Keine Order erstellt

### Empfohlene Testfälle

```python
# Test: Erfolgreiche Registrierung mit Order
def test_successful_registration_with_order():
    # ...

# Test: Fehler bei EventMember-Erstellung
def test_failed_member_creation_no_order():
    # ...

# Test: Duplicate Email
def test_duplicate_email_no_order():
    # ...
```

## Logging

Fehler werden geloggt für späteres Debugging:

```python
logger = logging.getLogger(__name__)
logger.error(f"Fehler bei der Event-Registrierung: {e}")
```

Logging-Konfiguration in `settings.py` sicherstellen:

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/path/to/django/debug.log',
        },
    },
    'loggers': {
        'events.views': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

## Rückwärtskompatibilität

- Die Änderungen sind rückwärtskompatibel
- Bestehende Registrierungen funktionieren weiterhin
- Nur der Fehlerfall wird neu behandelt

## Offene Punkte / TODO

- [ ] Unit-Tests für Fehlerfälle hinzufügen
- [ ] Integration-Tests für Shop-Flow hinzufügen
- [ ] Logging-Konfiguration prüfen/ergänzen
- [ ] Ggf. spezifischere Fehlermeldungen für verschiedene Exception-Typen
