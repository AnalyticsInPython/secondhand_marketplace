"""Nationality weights and name pools keyed to them.

UX_SPEC §9 fixes the four largest shares -- "US ~35%, China ~18%, South Korea
~10%, India ~8%, remainder spread across ~30 countries" -- and leaves the tail to
us.

The reason names live next to nationalities rather than in a generic faker: a
Korean flag over "Jessica Miller" is the first thing anyone notices in a demo, and
the seller card on the item detail screen puts nationality and name side by side.
So every country maps to a *name system*, and a user's name is drawn from the
system their nationality points at.

Name systems are deliberately coarse. They are not an ethnographic claim; they are
a way of making the generated corpus survive a glance. Several countries share a
system, and any of these pools can be swapped without touching anything else.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Nationality weights  (UX_SPEC §9)
#
# The first four are the spec's. The tail is ours, weighted loosely towards
# Columbia's actual international mix. Raw weights, normalised at use.
# ---------------------------------------------------------------------------

NATIONALITY_WEIGHTS: "dict[str, float]" = {
    # --- fixed by §9 ---
    "US": 35.0,
    "CN": 18.0,
    "KR": 10.0,
    "IN": 8.0,
    # --- the ~29% tail, ours ---
    "CA": 2.0,
    "TW": 1.7,
    "BR": 1.6,
    "JP": 1.5,
    "GB": 1.4,
    "FR": 1.2,
    "MX": 1.2,
    "DE": 1.1,
    "TR": 1.0,
    "SG": 1.0,
    "HK": 1.0,
    "IT": 0.9,
    "ES": 0.8,
    "RU": 0.8,
    "NG": 0.8,
    "ID": 0.8,
    "TH": 0.7,
    "VN": 0.7,
    "PH": 0.7,
    "AU": 0.6,
    "CO": 0.6,
    "CL": 0.5,
    "AR": 0.5,
    "IL": 0.5,
    "EG": 0.5,
    "PK": 0.5,
    "BD": 0.4,
    "GH": 0.4,
    "KE": 0.4,
    "NL": 0.4,
    "SE": 0.3,
    "CH": 0.3,
    "PL": 0.3,
    "GR": 0.3,
    "ZA": 0.3,
    "PT": 0.2,
}

# §6.1: the nationality dropdown pins "the 4 most common at Columbia" to the top.
PINNED_NATIONALITIES: "tuple[str, ...]" = ("US", "CN", "KR", "IN")

NATIONALITY_NAMES: "dict[str, str]" = {
    "US": "United States", "CN": "China", "KR": "South Korea", "IN": "India",
    "CA": "Canada", "TW": "Taiwan", "BR": "Brazil", "JP": "Japan",
    "GB": "United Kingdom", "FR": "France", "MX": "Mexico", "DE": "Germany",
    "TR": "Turkey", "SG": "Singapore", "HK": "Hong Kong", "IT": "Italy",
    "ES": "Spain", "RU": "Russia", "NG": "Nigeria", "ID": "Indonesia",
    "TH": "Thailand", "VN": "Vietnam", "PH": "Philippines", "AU": "Australia",
    "CO": "Colombia", "CL": "Chile", "AR": "Argentina", "IL": "Israel",
    "EG": "Egypt", "PK": "Pakistan", "BD": "Bangladesh", "GH": "Ghana",
    "KE": "Kenya", "NL": "Netherlands", "SE": "Sweden", "CH": "Switzerland",
    "PL": "Poland", "GR": "Greece", "ZA": "South Africa", "PT": "Portugal",
}

# ---------------------------------------------------------------------------
# Name systems
# ---------------------------------------------------------------------------

_SYSTEM_OF: "dict[str, str]" = {
    "US": "anglo", "CA": "anglo", "GB": "anglo", "AU": "anglo", "ZA": "anglo",
    "CN": "chinese", "TW": "chinese", "HK": "chinese", "SG": "chinese",
    "KR": "korean",
    "IN": "indian", "PK": "indian", "BD": "indian",
    "JP": "japanese",
    "BR": "portuguese", "PT": "portuguese",
    "MX": "hispanic", "ES": "hispanic", "CO": "hispanic", "CL": "hispanic",
    "AR": "hispanic",
    "FR": "french",
    "DE": "german", "CH": "german", "NL": "german", "SE": "german",
    "TR": "turkish",
    "RU": "russian", "PL": "russian",
    "NG": "west_african", "GH": "west_african", "KE": "west_african",
    "EG": "arabic", "IL": "arabic",
    "TH": "thai",
    "VN": "vietnamese",
    "ID": "indonesian",
    "PH": "filipino",
    "IT": "italian",
    "GR": "greek",
}

GIVEN_NAMES: "dict[str, tuple[str, ...]]" = {
    "anglo": (
        "James", "Emma", "Michael", "Olivia", "Daniel", "Sophia", "Ryan",
        "Hannah", "Ethan", "Grace", "Nathan", "Chloe", "Marcus", "Zoe",
        "Caleb", "Nora", "Julian", "Ruby", "Owen", "Tessa", "Elliot", "Maya",
    ),
    "chinese": (
        "Wei", "Yuxin", "Hao", "Jiayi", "Ziyu", "Xinyi", "Chen", "Mengyao",
        "Tianyu", "Ruoxi", "Bo", "Yuhan", "Jian", "Siyu", "Kaiwen", "Lingxi",
        "Zhihao", "Qian", "Yifan", "Xiaoyu",
    ),
    "korean": (
        "Jiwoo", "Minjun", "Seoyeon", "Doyoon", "Hyerin", "Jaewon", "Yuna",
        "Dongwoo", "Sohee", "Junho", "Eunseo", "Taeyang", "Hyunwoo", "Chaewon",
        "Sungmin", "Jimin", "Haeun", "Woojin", "Nayeon", "Kyungsoo",
    ),
    "indian": (
        "Aarav", "Ananya", "Rohan", "Priya", "Vinayak", "Ishita", "Karthik",
        "Meera", "Aditya", "Sneha", "Rahul", "Divya", "Arjun", "Kavya",
        "Siddharth", "Nikita", "Imran", "Zara", "Farhan", "Ayesha",
    ),
    "japanese": (
        "Haruto", "Yui", "Sota", "Aoi", "Ren", "Sakura", "Kenta", "Mio",
        "Riku", "Hina", "Takumi", "Nanami",
    ),
    "portuguese": (
        "Lucas", "Beatriz", "Matheus", "Camila", "Rafael", "Larissa", "Tiago",
        "Mariana", "Gustavo", "Ines", "Bruno", "Carolina",
    ),
    "hispanic": (
        "Mateo", "Valentina", "Santiago", "Isabela", "Diego", "Lucia",
        "Andres", "Camila", "Javier", "Renata", "Tomas", "Daniela",
    ),
    "french": (
        "Louis", "Camille", "Hugo", "Chloe", "Antoine", "Manon", "Theo",
        "Juliette", "Nicolas", "Elise",
    ),
    "german": (
        "Lukas", "Lena", "Jonas", "Anna", "Felix", "Marie", "Niklas", "Sophie",
        "Erik", "Klara", "Sven", "Ingrid",
    ),
    "turkish": (
        "Mehmet", "Elif", "Emre", "Zeynep", "Kaan", "Defne", "Baris", "Ece",
    ),
    "russian": (
        "Dmitri", "Anastasia", "Ivan", "Ekaterina", "Sergei", "Olga",
        "Nikolai", "Yulia", "Piotr", "Zofia",
    ),
    "west_african": (
        "Chinedu", "Amara", "Emeka", "Ngozi", "Kwame", "Abena", "Tunde",
        "Folake", "Kofi", "Akosua", "Wanjiru", "Njoroge",
    ),
    "arabic": (
        "Omar", "Layla", "Youssef", "Nour", "Karim", "Rania", "Tamar", "Noa",
        "Eitan", "Maya",
    ),
    "thai": ("Somchai", "Ploy", "Nattapong", "Kanya", "Anan", "Siriporn"),
    "vietnamese": ("Minh", "Linh", "Duc", "Thao", "Quang", "Mai"),
    "indonesian": ("Budi", "Sari", "Agus", "Dewi", "Rizki", "Putri"),
    "filipino": ("Jose", "Maria", "Angelo", "Bianca", "Paolo", "Trisha"),
    "italian": ("Marco", "Giulia", "Luca", "Chiara", "Matteo", "Francesca"),
    "greek": ("Nikos", "Eleni", "Dimitris", "Sofia", "Yannis", "Katerina"),
}

FAMILY_NAMES: "dict[str, tuple[str, ...]]" = {
    "anglo": (
        "Miller", "Bennett", "Carter", "Hayes", "Brooks", "Reed", "Foster",
        "Sullivan", "Walsh", "Fletcher", "Ellis", "Grant", "Whitfield",
        "Doyle", "Marsh", "Barnes", "Quinn", "Sinclair",
    ),
    "chinese": (
        "Wang", "Li", "Zhang", "Liu", "Chen", "Yang", "Huang", "Zhao", "Wu",
        "Zhou", "Xu", "Sun", "Ma", "Zhu", "Hu", "Guo", "Lin", "He",
    ),
    "korean": (
        "Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon", "Jang",
        "Lim", "Han", "Oh", "Seo", "Shin", "Kwon", "Hwang",
    ),
    "indian": (
        "Sharma", "Patel", "Iyer", "Reddy", "Nair", "Gupta", "Menon", "Rao",
        "Desai", "Chatterjee", "Kulkarni", "Bose", "Khan", "Ahmed", "Siddiqui",
    ),
    "japanese": (
        "Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito", "Nakamura",
        "Kobayashi",
    ),
    "portuguese": (
        "Silva", "Santos", "Oliveira", "Souza", "Costa", "Pereira", "Almeida",
        "Ferreira", "Ribeiro",
    ),
    "hispanic": (
        "Garcia", "Rodriguez", "Martinez", "Lopez", "Hernandez", "Torres",
        "Ramirez", "Vargas", "Castillo", "Mendoza", "Rojas", "Navarro",
    ),
    "french": (
        "Dubois", "Lefevre", "Moreau", "Laurent", "Bernard", "Rousseau",
        "Girard", "Fontaine",
    ),
    "german": (
        "Muller", "Schmidt", "Weber", "Fischer", "Wagner", "Becker", "Hoffmann",
        "Bakker", "Lindqvist", "Zimmermann",
    ),
    "turkish": ("Yilmaz", "Demir", "Kaya", "Celik", "Sahin", "Arslan"),
    "russian": (
        "Ivanov", "Petrova", "Sokolov", "Volkov", "Novak", "Kowalski",
        "Morozova", "Lebedev",
    ),
    "west_african": (
        "Okafor", "Adeyemi", "Mensah", "Boateng", "Nwosu", "Achebe", "Osei",
        "Kamau", "Mwangi", "Otieno",
    ),
    "arabic": ("Hassan", "Mansour", "Haddad", "Nasser", "Levi", "Shapiro", "Cohen"),
    "thai": ("Srisai", "Chaiyaporn", "Wattana", "Rattanakul"),
    "vietnamese": ("Nguyen", "Tran", "Pham", "Le", "Vo"),
    "indonesian": ("Wijaya", "Santoso", "Hartono", "Kusuma"),
    "filipino": ("Santos", "Reyes", "Cruz", "Bautista", "Villanueva"),
    "italian": ("Rossi", "Ferrari", "Esposito", "Bianchi", "Romano"),
    "greek": ("Papadopoulos", "Georgiou", "Nikolaidis", "Vasilakis"),
}


def system_for(nationality: str) -> str:
    """Which name pool a nationality draws from. Falls back to anglo."""
    return _SYSTEM_OF.get(nationality, "anglo")


def draw_name(rng, nationality: str) -> "tuple[str, str]":
    """A (given, family) pair consistent with the nationality."""
    system = system_for(nationality)
    return (
        rng.choice(GIVEN_NAMES[system]),
        rng.choice(FAMILY_NAMES[system]),
    )


def _check() -> None:
    assert set(NATIONALITY_WEIGHTS) == set(NATIONALITY_NAMES), (
        "weights and display names disagree about the country list"
    )
    for code in NATIONALITY_WEIGHTS:
        assert len(code) == 2 and code.isupper(), "not an alpha-2 code: %r" % code
    for pinned in PINNED_NATIONALITIES:
        assert pinned in NATIONALITY_WEIGHTS
    # Every country resolves to a system that actually has both pools.
    for code in NATIONALITY_WEIGHTS:
        system = system_for(code)
        assert system in GIVEN_NAMES, "%s -> missing given pool %s" % (code, system)
        assert system in FAMILY_NAMES, "%s -> missing family pool %s" % (code, system)
    assert set(GIVEN_NAMES) == set(FAMILY_NAMES), "a name system is half-defined"
    # §9's four fixed shares survived editing.
    assert NATIONALITY_WEIGHTS["US"] == 35.0
    assert NATIONALITY_WEIGHTS["CN"] == 18.0
    assert NATIONALITY_WEIGHTS["KR"] == 10.0
    assert NATIONALITY_WEIGHTS["IN"] == 8.0


_check()


if __name__ == "__main__":
    total = sum(NATIONALITY_WEIGHTS.values())
    print("Nationalities — %d countries, %d name systems\n"
          % (len(NATIONALITY_WEIGHTS), len(GIVEN_NAMES)))
    print("%-5s %-18s %7s  %s" % ("CODE", "COUNTRY", "SHARE", "NAME SYSTEM"))
    for code, w in sorted(NATIONALITY_WEIGHTS.items(), key=lambda kv: -kv[1]):
        pin = " *" if code in PINNED_NATIONALITIES else "  "
        print("%-5s %-18s %6.1f%%%s %s"
              % (code, NATIONALITY_NAMES[code], 100 * w / total, pin, system_for(code)))
    print("\n* pinned to the top of the sign-up dropdown (§6.1)")
