"""The quote fields the agent collects, grouped in the order you'd enter them in Goodshuffle Pro.

Edit this list to match your own Goodshuffle workflow. `required=True` fields must be
filled before a lead is marked "Ready to quote".
"""

FIELD_GROUPS = [
    ("Client", [
        ("client_name", "Client name", True),
        ("company", "Company / organization", False),
        ("email", "Email", True),
        ("phone", "Phone", True),
    ]),
    ("Event", [
        ("event_name", "Event name", False),
        ("event_type", "Event type (wedding, corporate, party...)", True),
        ("event_date", "Event date", True),
        ("event_time", "Event start / end time", False),
        ("guest_count", "Guest count", True),
        ("seating_style", "Seating style (seated dinner, cocktail, ceremony...)", False),
        ("budget", "Budget", False),
    ]),
    ("Venue & site", [
        ("venue_name", "Venue name", False),
        ("venue_address", "Venue address", True),
        ("surface", "Setup surface (grass, concrete, asphalt, deck)", True),
        ("site_access", "Site access / obstacles (slopes, gates, trees, power lines)", False),
        ("power_available", "Power available on site?", False),
        ("permits", "Permits / venue requirements", False),
    ]),
    ("Rental items", [
        ("tent", "Tent (size / style)", True),
        ("sidewalls", "Sidewalls", False),
        ("tables", "Tables (type / qty)", False),
        ("chairs", "Chairs (type / qty)", False),
        ("linens", "Linens", False),
        ("lighting", "Lighting", False),
        ("flooring_dancefloor", "Flooring / dance floor / staging", False),
        ("climate", "Heating / cooling", False),
        ("other_items", "Other items", False),
    ]),
    ("Logistics", [
        ("delivery_window", "Delivery / setup date & time window", False),
        ("pickup_window", "Pickup / teardown date & time window", False),
        ("onsite_contact", "On-site contact (name / phone)", False),
        ("referral_source", "How they heard about us", False),
        ("notes", "Other notes", False),
    ]),
]

ALL_FIELDS = [(key, label, req) for _, items in FIELD_GROUPS for key, label, req in items]
FIELD_KEYS = [k for k, _, _ in ALL_FIELDS]
REQUIRED_KEYS = [k for k, _, r in ALL_FIELDS if r]
LABELS = {k: label for k, label, _ in ALL_FIELDS}


def missing_required(fields):
    return [k for k in REQUIRED_KEYS if not (fields.get(k) or "").strip()]
