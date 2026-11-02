"""Load a few sample leads so you can see the dashboard before connecting Gmail.

    python seed_demo.py          (remove them later with: python seed_demo.py --clear)
"""
import sys
import uuid

import db
from fields import missing_required

db.init()

if "--clear" in sys.argv:
    with db.connect() as c:
        ids = [r[0] for r in c.execute("SELECT id FROM leads WHERE thread_id LIKE 'test-demo-%'")]
        c.executemany("DELETE FROM messages WHERE lead_id=?", [(i,) for i in ids])
        c.execute("DELETE FROM leads WHERE thread_id LIKE 'test-demo-%'")
    print(f"Removed {len(ids)} demo leads.")
    sys.exit()

DEMOS = [
    dict(
        name="Maria Alvarez", email="maria.alvarez@example.com", subject="Wedding tent – June 2027",
        status="ready_to_quote",
        summary="Backyard wedding, 140 guests, seated dinner, Sat June 12 2027 in Westfield. All details in.",
        msgs=[
            ("inbound", "Hi there! My fiancé and I are getting married June 12, 2027 at my parents' house in Westfield. "
                        "We need a tent for around 140 people with tables and chairs, and maybe some string lights. "
                        "Could you send me a quote?\n\nThanks,\nMaria"),
            ("outbound", "Hi Maria,\n\nCongratulations to you both! A backyard wedding in June sounds lovely. A few quick "
                         "questions so we can put together the right setup:\n\n1. What's the full address?\n"
                         "2. Will the tent go on grass, or on a driveway/patio?\n3. Are you picturing a seated dinner "
                         "or more of a cocktail-style reception?\n4. Best phone number to reach you?\n\nBest,\nSam"),
            ("inbound", "It's 42 Orchard Lane, Westfield NJ. Tent would go on the back lawn (grass, pretty flat). "
                        "Seated dinner with a dance floor. My cell is 908-555-0142. Budget is around $9k for rentals."),
        ],
        fields=dict(client_name="Maria Alvarez", email="maria.alvarez@example.com", phone="908-555-0142",
                    event_type="Wedding", event_date="Sat, June 12 2027", guest_count="~140",
                    seating_style="Seated dinner + dance floor", budget="~$9,000 rentals",
                    venue_name="Private residence", venue_address="42 Orchard Lane, Westfield NJ",
                    surface="Grass, mostly flat", tent="Sized for 140 seated + dance floor (recommend 40x80 frame)",
                    tables="Rounds or banquets for 140", chairs="140", lighting="String/bistro lights",
                    flooring_dancefloor="Dance floor"),
        draft="Hi Maria,\n\nPerfect, thank you! Here's what I have:\n\n- Saturday, June 12, 2027 at 42 Orchard Lane, Westfield\n"
              "- ~140 guests, seated dinner with a dance floor\n- Tent on the back lawn, with tables, chairs and string lights\n\n"
              "I'll put together a detailed quote with a recommended tent layout and send it over shortly.\n\nBest,\nSam",
    ),
    dict(
        name="Derek Huang", email="dhuang@brightpathlogistics.example", subject="Company picnic rentals",
        status="collecting",
        summary="Corporate summer picnic for ~250 employees in August; needs venue details and surface.",
        msgs=[
            ("inbound", "Hello, we're planning our annual company picnic for about 250 employees sometime in mid August. "
                        "We'll need a couple of large tents for shade plus tables and chairs. What do you have available?\n\n"
                        "Derek Huang\nOffice Manager, BrightPath Logistics"),
        ],
        fields=dict(client_name="Derek Huang", company="BrightPath Logistics", email="dhuang@brightpathlogistics.example",
                    event_type="Corporate picnic", guest_count="~250", tent="Large shade tents (2+)",
                    tables="For 250", chairs="For 250", event_date="Mid-August (date TBD)"),
        draft="Hi Derek,\n\nThanks for reaching out, a company picnic for 250 sounds like a great day. We'd be glad to help "
              "with shade tents, tables and chairs. A few details so we can recommend the right setup:\n\n"
              "1. Do you have a specific date in mind?\n2. Where will the picnic be held (park, office campus)? An address helps.\n"
              "3. Will the tents go on grass or pavement?\n4. What's the best phone number to reach you?\n\nBest,\nSam",
    ),
    dict(
        name="Priya Shah", email="priya.shah@example.com", subject="Re: Graduation party quote",
        status="needs_you",
        summary="⚠ Event is this Saturday and she's asking for a discount — Graduation party, 60 guests, 20x30 tent.",
        msgs=[
            ("inbound", "Hi, any chance you still have a 20x30 tent for this Saturday? It's a graduation party, about 60 people, "
                        "in our driveway at 18 Birch St. Also, is there any discount if we pick it up ourselves? Phone 732-555-0199."),
        ],
        fields=dict(client_name="Priya Shah", email="priya.shah@example.com", phone="732-555-0199",
                    event_type="Graduation party", event_date="This Saturday", guest_count="~60",
                    venue_address="18 Birch St", surface="Driveway (asphalt/concrete)", tent="20x30"),
        draft="Hi Priya,\n\nThanks for reaching out, and congratulations to your graduate! Since your party is this weekend, "
              "Sam will check availability and follow up with you personally today.\n\nBest,\nSam",
    ),
]

for d in DEMOS:
    lead_id = db.create_lead(f"test-demo-{uuid.uuid4()}", d["email"], d["name"], d["subject"])
    for direction, body in d["msgs"]:
        db.add_message(lead_id, f"test-{uuid.uuid4()}", direction,
                       f'{d["name"]} <{d["email"]}>' if direction == "inbound" else "Sam", db.now(), body)
    db.update_lead(lead_id, status=d["status"], summary=d["summary"], fields=d["fields"],
                   missing=missing_required(d["fields"]), draft_body=d["draft"])
print(f"Added {len(DEMOS)} demo leads. Start the dashboard with: python run.py")
