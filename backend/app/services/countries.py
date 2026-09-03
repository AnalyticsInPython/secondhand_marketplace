"""Nationality reference — ISO 3166-1 alpha-2.

Nationality is a fixed dropdown, never free text, so that equality is a valid
comparison and the same-country filter stays honest. The four most common at
Columbia are pinned to the top of the picker (UX_SPEC.md §6.1).
"""

from __future__ import annotations

PINNED = ["US", "CN", "KR", "IN"]

_COUNTRIES: list[tuple[str, str]] = [
    ("AF", "Afghanistan"), ("AL", "Albania"), ("DZ", "Algeria"), ("AD", "Andorra"),
    ("AO", "Angola"), ("AG", "Antigua and Barbuda"), ("AR", "Argentina"), ("AM", "Armenia"),
    ("AU", "Australia"), ("AT", "Austria"), ("AZ", "Azerbaijan"), ("BS", "Bahamas"),
    ("BH", "Bahrain"), ("BD", "Bangladesh"), ("BB", "Barbados"), ("BY", "Belarus"),
    ("BE", "Belgium"), ("BZ", "Belize"), ("BJ", "Benin"), ("BT", "Bhutan"),
    ("BO", "Bolivia"), ("BA", "Bosnia and Herzegovina"), ("BW", "Botswana"), ("BR", "Brazil"),
    ("BN", "Brunei"), ("BG", "Bulgaria"), ("BF", "Burkina Faso"), ("BI", "Burundi"),
    ("CV", "Cabo Verde"), ("KH", "Cambodia"), ("CM", "Cameroon"), ("CA", "Canada"),
    ("CF", "Central African Republic"), ("TD", "Chad"), ("CL", "Chile"), ("CN", "China"),
    ("CO", "Colombia"), ("KM", "Comoros"), ("CG", "Congo"), ("CD", "Congo (DRC)"),
    ("CR", "Costa Rica"), ("CI", "Côte d'Ivoire"), ("HR", "Croatia"), ("CU", "Cuba"),
    ("CY", "Cyprus"), ("CZ", "Czechia"), ("DK", "Denmark"), ("DJ", "Djibouti"),
    ("DM", "Dominica"), ("DO", "Dominican Republic"), ("EC", "Ecuador"), ("EG", "Egypt"),
    ("SV", "El Salvador"), ("GQ", "Equatorial Guinea"), ("ER", "Eritrea"), ("EE", "Estonia"),
    ("SZ", "Eswatini"), ("ET", "Ethiopia"), ("FJ", "Fiji"), ("FI", "Finland"),
    ("FR", "France"), ("GA", "Gabon"), ("GM", "Gambia"), ("GE", "Georgia"),
    ("DE", "Germany"), ("GH", "Ghana"), ("GR", "Greece"), ("GD", "Grenada"),
    ("GT", "Guatemala"), ("GN", "Guinea"), ("GW", "Guinea-Bissau"), ("GY", "Guyana"),
    ("HT", "Haiti"), ("HN", "Honduras"), ("HK", "Hong Kong"), ("HU", "Hungary"),
    ("IS", "Iceland"), ("IN", "India"), ("ID", "Indonesia"), ("IR", "Iran"),
    ("IQ", "Iraq"), ("IE", "Ireland"), ("IL", "Israel"), ("IT", "Italy"),
    ("JM", "Jamaica"), ("JP", "Japan"), ("JO", "Jordan"), ("KZ", "Kazakhstan"),
    ("KE", "Kenya"), ("KI", "Kiribati"), ("XK", "Kosovo"), ("KW", "Kuwait"),
    ("KG", "Kyrgyzstan"), ("LA", "Laos"), ("LV", "Latvia"), ("LB", "Lebanon"),
    ("LS", "Lesotho"), ("LR", "Liberia"), ("LY", "Libya"), ("LI", "Liechtenstein"),
    ("LT", "Lithuania"), ("LU", "Luxembourg"), ("MO", "Macao"), ("MG", "Madagascar"),
    ("MW", "Malawi"), ("MY", "Malaysia"), ("MV", "Maldives"), ("ML", "Mali"),
    ("MT", "Malta"), ("MH", "Marshall Islands"), ("MR", "Mauritania"), ("MU", "Mauritius"),
    ("MX", "Mexico"), ("FM", "Micronesia"), ("MD", "Moldova"), ("MC", "Monaco"),
    ("MN", "Mongolia"), ("ME", "Montenegro"), ("MA", "Morocco"), ("MZ", "Mozambique"),
    ("MM", "Myanmar"), ("NA", "Namibia"), ("NR", "Nauru"), ("NP", "Nepal"),
    ("NL", "Netherlands"), ("NZ", "New Zealand"), ("NI", "Nicaragua"), ("NE", "Niger"),
    ("NG", "Nigeria"), ("KP", "North Korea"), ("MK", "North Macedonia"), ("NO", "Norway"),
    ("OM", "Oman"), ("PK", "Pakistan"), ("PW", "Palau"), ("PS", "Palestine"),
    ("PA", "Panama"), ("PG", "Papua New Guinea"), ("PY", "Paraguay"), ("PE", "Peru"),
    ("PH", "Philippines"), ("PL", "Poland"), ("PT", "Portugal"), ("QA", "Qatar"),
    ("RO", "Romania"), ("RU", "Russia"), ("RW", "Rwanda"), ("KN", "Saint Kitts and Nevis"),
    ("LC", "Saint Lucia"), ("VC", "Saint Vincent and the Grenadines"), ("WS", "Samoa"),
    ("SM", "San Marino"), ("ST", "São Tomé and Príncipe"), ("SA", "Saudi Arabia"),
    ("SN", "Senegal"), ("RS", "Serbia"), ("SC", "Seychelles"), ("SL", "Sierra Leone"),
    ("SG", "Singapore"), ("SK", "Slovakia"), ("SI", "Slovenia"), ("SB", "Solomon Islands"),
    ("SO", "Somalia"), ("ZA", "South Africa"), ("KR", "South Korea"), ("SS", "South Sudan"),
    ("ES", "Spain"), ("LK", "Sri Lanka"), ("SD", "Sudan"), ("SR", "Suriname"),
    ("SE", "Sweden"), ("CH", "Switzerland"), ("SY", "Syria"), ("TW", "Taiwan"),
    ("TJ", "Tajikistan"), ("TZ", "Tanzania"), ("TH", "Thailand"), ("TL", "Timor-Leste"),
    ("TG", "Togo"), ("TO", "Tonga"), ("TT", "Trinidad and Tobago"), ("TN", "Tunisia"),
    ("TR", "Türkiye"), ("TM", "Turkmenistan"), ("TV", "Tuvalu"), ("UG", "Uganda"),
    ("UA", "Ukraine"), ("AE", "United Arab Emirates"), ("GB", "United Kingdom"),
    ("US", "United States"), ("UY", "Uruguay"), ("UZ", "Uzbekistan"), ("VU", "Vanuatu"),
    ("VA", "Vatican City"), ("VE", "Venezuela"), ("VN", "Vietnam"), ("YE", "Yemen"),
    ("ZM", "Zambia"), ("ZW", "Zimbabwe"),
]

_BY_CODE: dict[str, str] = dict(_COUNTRIES)


def is_valid(code: str | None) -> bool:
    return bool(code) and code.upper() in _BY_CODE


def name_of(code: str) -> str:
    return _BY_CODE.get(code.upper(), code.upper())


def all_countries() -> list[dict]:
    """Pinned first, then everything alphabetically — the order the picker shows."""
    pinned = [{"code": c, "name": _BY_CODE[c], "pinned": True} for c in PINNED]
    rest = [
        {"code": code, "name": name, "pinned": False}
        for code, name in sorted(_COUNTRIES, key=lambda cn: cn[1])
        if code not in PINNED
    ]
    return pinned + rest
