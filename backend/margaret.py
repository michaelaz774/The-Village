"""Demo data: Margaret Chen profile."""
from datetime import datetime
from models import Elder, ProfileFact, VillageMember, MedicalInfo, Medication, WellbeingBaseline


MARGARET = Elder(
    id="margaret-chen-001",
    name="Margaret Chen",
    age=78,
    phone="+1-412-555-0142",
    photo_url="/margaret.jpg",
    address="412 Oak Street, Pittsburgh, PA 15213",

    profile=[
        ProfileFact(
            id="pf-001",
            fact="Husband Harold passed away 2 years ago",
            category="family",
            context="They were married for 52 years",
            learned_at=datetime.now()
        ),
        ProfileFact(
            id="pf-002",
            fact="Used to play gin rummy with Harold every evening",
            category="interests",
            context="This was their daily ritual for decades",
            learned_at=datetime.now()
        ),
        ProfileFact(
            id="pf-003",
            fact="Daughter Susan lives in Philadelphia",
            category="family",
            context="About 5 hours away, busy with her own family",
            learned_at=datetime.now()
        ),
        ProfileFact(
            id="pf-004",
            fact="Has a grandson Jake who visits occasionally",
            category="family",
            context="Margaret lights up when talking about him",
            learned_at=datetime.now()
        ),
        ProfileFact(
            id="pf-005",
            fact="Takes metoprolol for blood pressure",
            category="medical",
            context="Daily morning medication",
            learned_at=datetime.now()
        )
    ],

    village=[
        VillageMember(
            id="vm-001",
            name="Susan Chen",
            role="family",
            relationship="daughter",
            phone="+1-215-555-0198",
            availability="evenings",
            notes="Works full-time, feels guilty about not calling more"
        ),
        VillageMember(
            id="vm-002",
            name="Tom Bradley",
            role="neighbor",
            relationship="next-door neighbor",
            phone="+1-412-555-0156",
            availability="afternoons",
            notes="Retired teacher, brings Margaret's mail often"
        ),
        VillageMember(
            id="vm-003",
            name="Dr. Maria Martinez",
            role="medical",
            relationship="primary care physician",
            phone="+1-412-555-0200",
            availability="office hours",
            notes="Has been Margaret's doctor for 15 years"
        ),
        VillageMember(
            id="vm-004",
            name="Jane Thompson",
            role="volunteer",
            relationship="companion volunteer",
            phone="+1-412-555-0177",
            availability="Tuesdays and Thursdays",
            notes="Also loves card games, matched based on interests"
        )
    ],

    medical=MedicalInfo(
        primary_doctor="Dr. Maria Martinez",
        practice_name="Oakland Family Medicine",
        practice_phone="+1-412-555-0200",
        medications=[
            Medication(
                name="Metoprolol",
                dosage="25mg",
                frequency="Once daily, morning",
                next_refill="2026-01-19"
            )
        ],
        conditions=["Hypertension", "Mild osteoarthritis (knee)"]
    ),

    wellbeing_baseline=WellbeingBaseline(
        typical_mood="Generally positive, occasionally melancholy about Harold",
        social_frequency="Talks to Susan weekly, sees Tom a few times a week",
        cognitive_baseline="Sharp, good memory, occasionally forgets small things",
        physical_limitations=["Knee pain limits long walks", "Gets tired easily"],
        known_concerns=["Tends to isolate when feeling down", "Doesn't drink enough water"]
    )
)

# Export as both MARGARET and margaret_elder for compatibility
margaret_elder = MARGARET
