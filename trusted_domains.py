TRUSTED_DOMAINS = {
    "sante": [
        "who.int",
        "cdc.gov",
        "thelancet.com",
    ],
    "economie": [
        "worldbank.org",
        "imf.org",
        "oecd.org",
    ],
    "organisations_officielles": [
        "un.org",
        "africa-union.org",
        "eac.int",
    ],
    "international_fr": [
        "rfi.fr",
        "lemonde.fr",
        "afp.com",
    ],
    "international_en": [
        "reuters.com",
        "apnews.com",
        "bbc.com",
    ],
    "regional_afrique": [
        "jeuneafrique.com",
        "theeastafrican.co.ke",
        "allafrica.com",
    ],
}


def get_domains_for_categories(categories: list[str]) -> list[str]:
    """
    Retourne la liste combinée (dédupliquée) des domaines de confiance
    pour une ou plusieurs catégories données.
    """
    domains = set()
    for category in categories:
        domains.update(TRUSTED_DOMAINS.get(category, []))
    return list(domains)

