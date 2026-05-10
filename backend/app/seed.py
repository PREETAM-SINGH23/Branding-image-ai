from sqlalchemy.orm import Session

from app.models import Account, Dealership, User
from app.security import hash_password

# Demo brands + dealerships for Studio. Accounts upserted by slug; dealers upserted by (account, code).
BRANDS_SEED: list[dict] = [
    {
        "name": "Volkswagen",
        "slug": "volkswagen",
        "dealerships": [
            ("VW-Apple", "VW-Apple", "123 Auto Row, Mumbai", "+91 22 4000 1001", "https://vw-apple.example.com"),
            ("VW-KUN", "VW-KUN", "45 Ring Road, Delhi", "+91 11 4000 1002", "https://vw-kun.example.com"),
            ("VW-Lally", "VW-Lally", "9 MG Road, Bengaluru", "+91 80 4000 1003", "https://vw-lally.example.com"),
            ("VW-Motor", "VW-Motor", "2 NH Bypass, Kochi", "+91 48 4000 1004", "https://vw-motor.example.com"),
            ("VW-City", "VW-City", "88 Sector 18, Noida", "+91 120 4000 1005", "https://vw-city.example.com"),
            ("VW-Ridge", "VW Ridge Motors", "Baner Road, Pune", "+91 20 4000 1006", "https://vw-ridge.example.com"),
            ("VW-Pulse", "VW Pulse Arena", "Salt Lake, Kolkata", "+91 33 4000 1007", "https://vw-pulse.example.com"),
        ],
    },
    {
        "name": "Tata",
        "slug": "tata",
        "dealerships": [
            ("TATA-North", "Tata North Hub", "Plot 1, Gurugram", "+91 124 5000 2001", "https://tata-north.example.com"),
            ("TATA-South", "Tata South Hub", "OMR, Chennai", "+91 44 5000 2002", "https://tata-south.example.com"),
            ("TATA-East", "Tata East Plaza", "Salt Lake, Kolkata", "+91 33 5000 2003", "https://tata-east.example.com"),
            ("TATA-West", "Tata West Select", "Baner, Pune", "+91 20 5000 2004", "https://tata-west.example.com"),
            ("TATA-Central", "Tata Central One", "MG Road, Hyderabad", "+91 40 5000 2005", "https://tata-central.example.com"),
        ],
    },
    {
        "name": "Kia",
        "slug": "kia",
        "dealerships": [
            ("KIA-Metro", "Kia Metro", "Ring Road, Pune", "+91 20 6000 3001", "https://kia-metro.example.com"),
            ("KIA-Lakeside", "Kia Lakeside", "Lake View, Hyderabad", "+91 40 6000 3002", "https://kia-lakeside.example.com"),
            ("KIA-Sky", "Kia Skyline", "Sector 18, Noida", "+91 120 6000 3003", "https://kia-sky.example.com"),
            ("KIA-River", "Kia Riverfront", "Panjim, Goa", "+91 832 6000 3004", "https://kia-river.example.com"),
            ("KIA-Urban", "Kia Urban Drive", "Indiranagar, Bengaluru", "+91 80 6000 3005", "https://kia-urban.example.com"),
        ],
    },
    {
        "name": "Hyundai",
        "slug": "hyundai",
        "dealerships": [
            ("HYU-Central", "Hyundai Central", "FC Road, Pune", "+91 20 6100 4101", "https://hyu-central.example.com"),
            ("HYU-Bay", "Hyundai Bay", "Marine Drive, Kochi", "+91 48 6100 4102", "https://hyu-bay.example.com"),
            ("HYU-Sky", "Hyundai Sky Tower", "Connaught Place, Delhi", "+91 11 6100 4103", "https://hyu-sky.example.com"),
            ("HYU-Nova", "Hyundai Nova", "Vijayawada", "+91 866 6100 4104", "https://hyu-nova.example.com"),
            ("HYU-Prime", "Hyundai Prime Motoring", "Jaipur", "+91 141 6100 4105", "https://hyu-prime.example.com"),
        ],
    },
    {
        "name": "Toyota",
        "slug": "toyota",
        "dealerships": [
            ("TOY-Platinum", "Toyota Platinum", "Sector 62, Noida", "+91 120 6200 5101", "https://toy-platinum.example.com"),
            ("TOY-Garden", "Toyota Garden City", "Indiranagar, Bengaluru", "+91 80 6200 5102", "https://toy-garden.example.com"),
            ("TOY-Crown", "Toyota Crown Motors", "Banjara Hills, Hyderabad", "+91 40 6200 5103", "https://toy-crown.example.com"),
            ("TOY-Harbor", "Toyota Harbor", "Marine Lines, Mumbai", "+91 22 6200 5104", "https://toy-harbor.example.com"),
            ("TOY-Highland", "Toyota Highland", "Dehradun", "+91 135 6200 5105", "https://toy-highland.example.com"),
        ],
    },
    {
        "name": "Honda",
        "slug": "honda",
        "dealerships": [
            ("HON-Civic", "Honda Civic Motors", "Link Road, Mumbai", "+91 22 6300 6101", "https://hon-civic.example.com"),
            ("HON-Ridge", "Honda Ridge", "Salt Lake, Kolkata", "+91 33 6300 6102", "https://hon-ridge.example.com"),
            ("HON-Prime", "Honda Prime", "Sitapura, Jaipur", "+91 141 6300 6103", "https://hon-prime.example.com"),
            ("HON-Edge", "Honda Edge", "Guwahati", "+91 361 6300 6104", "https://hon-edge.example.com"),
            ("HON-Metro", "Honda Metro Lane", "Lucknow", "+91 522 6300 6105", "https://hon-metro.example.com"),
        ],
    },
    {
        "name": "Maruti Suzuki",
        "slug": "maruti-suzuki",
        "dealerships": [
            ("MS-Arena", "Maruti Arena Hub", "Vaishali, Ghaziabad", "+91 120 6400 7101", "https://ms-arena.example.com"),
            ("MS-Nexa", "Nexa Select", "Jubilee Hills, Hyderabad", "+91 40 6400 7102", "https://ms-nexa.example.com"),
            ("MS-True", "Maruti True Value Plus", "Chandigarh", "+91 172 6400 7103", "https://ms-true.example.com"),
            ("MS-Drive", "Maruti Drive Inn", "Nashik", "+91 253 6400 7104", "https://ms-drive.example.com"),
            ("MS-Highway", "Maruti Highway Motors", "Surat", "+91 261 6400 7105", "https://ms-highway.example.com"),
        ],
    },
    {
        "name": "Mahindra",
        "slug": "mahindra",
        "dealerships": [
            ("MAH-Rise", "Mahindra Rise", "Sitapura, Jaipur", "+91 141 6500 8101", "https://mah-rise.example.com"),
            ("MAH-Peak", "Mahindra Peak", "Vijayawada", "+91 866 6500 8102", "https://mah-peak.example.com"),
            ("MAH-Forge", "Mahindra Forge", "Coimbatore", "+91 422 6500 8103", "https://mah-forge.example.com"),
            ("MAH-Trail", "Mahindra Trailhead", "Nagpur", "+91 712 6500 8104", "https://mah-trail.example.com"),
            ("MAH-Wave", "Mahindra Wave", "Visakhapatnam", "+91 891 6500 8105", "https://mah-wave.example.com"),
        ],
    },
    {
        "name": "Skoda",
        "slug": "skoda",
        "dealerships": [
            ("SKO-Vertex", "Škoda Vertex", "Saket, New Delhi", "+91 11 6600 9101", "https://sko-vertex.example.com"),
            ("SKO-Apex", "Škoda Apex", "Baner, Pune", "+91 20 6600 9102", "https://sko-apex.example.com"),
            ("SKO-Crystal", "Škoda Crystal", "Ahmedabad", "+91 79 6600 9103", "https://sko-crystal.example.com"),
            ("SKO-Motion", "Škoda Motion", "Mysuru", "+91 821 6600 9104", "https://sko-motion.example.com"),
            ("SKO-Edge", "Škoda Edge", "Thiruvananthapuram", "+91 471 6600 9105", "https://sko-edge.example.com"),
        ],
    },
    {
        "name": "Mercedes-Benz",
        "slug": "mercedes-benz",
        "dealerships": [
            ("MB-Star", "Mercedes-Benz Star", "Bandra Kurla Complex, Mumbai", "+91 22 6700 1101", "https://mb-star.example.com"),
            ("MB-Luxe", "Mercedes-Benz Luxe", "UB City, Bengaluru", "+91 80 6700 1102", "https://mb-luxe.example.com"),
            ("MB-Urban", "Mercedes-Benz Urban", "Cyber City, Gurugram", "+91 124 6700 1103", "https://mb-urban.example.com"),
            ("MB-Signature", "Mercedes-Benz Signature", "Kochi", "+91 48 6700 1104", "https://mb-signature.example.com"),
            ("MB-One", "Mercedes-Benz One", "Chandigarh", "+91 172 6700 1105", "https://mb-one.example.com"),
        ],
    },
]

# Demo dealers that ship with layered ``template.png`` frames (see ``assets/Dealership-panels/``).
DEMO_PANEL_TEMPLATE_PATHS: dict[str, str] = {
    "VW-Apple": "../assets/Dealership-panels/VW-dealers/VW-Autobhan/template.png",
    "TATA-North": "../assets/Dealership-panels/Tata-dealers/Bellad-tata/template.png",
}


def _sync_demo_panel_template_paths(db: Session) -> None:
    """Point sample dealers at packaged overlay PNGs so Brand overlay template matches expected creatives."""
    for code, rel in DEMO_PANEL_TEMPLATE_PATHS.items():
        row = db.query(Dealership).filter(Dealership.code == code).first()
        if row:
            row.panel_image_path = rel
    db.commit()


def _ensure_demo_accounts(db: Session) -> None:
    """Create seed accounts (and initial dealers) when the account slug is missing."""
    for acc in BRANDS_SEED:
        existing = db.query(Account).filter(Account.slug == acc["slug"]).first()
        if existing:
            continue
        a = Account(name=acc["name"], slug=acc["slug"], logo_path=None)
        db.add(a)
        db.flush()
        for code, name, addr, phone, web in acc["dealerships"]:
            db.add(
                Dealership(
                    account_id=a.id,
                    code=code,
                    name=name,
                    address_line=addr,
                    phone=phone,
                    website=web,
                    panel_image_path=None,
                )
            )
    db.commit()


def _ensure_demo_dealerships(db: Session) -> None:
    """Add any seed dealerships missing for each account (matched by dealer code)."""
    for acc in BRANDS_SEED:
        account = db.query(Account).filter(Account.slug == acc["slug"]).first()
        if not account:
            continue
        for code, name, addr, phone, web in acc["dealerships"]:
            exists = (
                db.query(Dealership)
                .filter(Dealership.account_id == account.id, Dealership.code == code)
                .first()
            )
            if exists:
                continue
            db.add(
                Dealership(
                    account_id=account.id,
                    code=code,
                    name=name,
                    address_line=addr,
                    phone=phone,
                    website=web,
                    panel_image_path=None,
                )
            )
    db.commit()


def seed_if_empty(db: Session) -> None:
    if not db.query(User).first():
        admin = User(
            email="admin@example.com",
            hashed_password=hash_password("admin123"),
            is_active=True,
        )
        db.add(admin)
        db.commit()

    _ensure_demo_accounts(db)
    _ensure_demo_dealerships(db)
    _sync_demo_panel_template_paths(db)
