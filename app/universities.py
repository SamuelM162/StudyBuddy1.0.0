UNIVERSITIES = [
    {
        "value": "Comenius University Bratislava",
        "label_en": "Comenius University Bratislava",
        "label_sk": "Univerzita Komenského v Bratislave",
    },
    {
        "value": "Slovak University of Technology in Bratislava",
        "label_en": "Slovak University of Technology in Bratislava",
        "label_sk": "Slovenská technická univerzita v Bratislave",
    },
    {
        "value": "University of Economics in Bratislava",
        "label_en": "University of Economics in Bratislava",
        "label_sk": "Ekonomická univerzita v Bratislave",
    },
    {
        "value": "Slovak University of Agriculture in Nitra",
        "label_en": "Slovak University of Agriculture in Nitra",
        "label_sk": "Slovenská poľnohospodárska univerzita v Nitre",
    },
    {
        "value": "Constantine the Philosopher University in Nitra",
        "label_en": "Constantine the Philosopher University in Nitra",
        "label_sk": "Univerzita Konštantína Filozofa v Nitre",
    },
    {
        "value": "University of Zilina",
        "label_en": "University of Zilina",
        "label_sk": "Žilinská univerzita v Žiline",
    },
    {
        "value": "Technical University of Kosice",
        "label_en": "Technical University of Kosice",
        "label_sk": "Technická univerzita v Košiciach",
    },
    {
        "value": "Pavol Jozef Safarik University in Kosice",
        "label_en": "Pavol Jozef Safarik University in Kosice",
        "label_sk": "Univerzita Pavla Jozefa Šafárika v Košiciach",
    },
    {
        "value": "Matej Bel University",
        "label_en": "Matej Bel University",
        "label_sk": "Univerzita Mateja Bela",
    },
    {
        "value": "University of Ss. Cyril and Methodius in Trnava",
        "label_en": "University of Ss. Cyril and Methodius in Trnava",
        "label_sk": "Univerzita sv. Cyrila a Metoda v Trnave",
    },
    {
        "value": "Trnava University",
        "label_en": "Trnava University",
        "label_sk": "Trnavská univerzita v Trnave",
    },
    {
        "value": "Alexander Dubcek University of Trencin",
        "label_en": "Alexander Dubcek University of Trencin",
        "label_sk": "Trenčianska univerzita Alexandra Dubčeka v Trenčíne",
    },
    {
        "value": "Catholic University in Ruzomberok",
        "label_en": "Catholic University in Ruzomberok",
        "label_sk": "Katolícka univerzita v Ružomberku",
    },
    {
        "value": "J. Selye University",
        "label_en": "J. Selye University",
        "label_sk": "Univerzita J. Selyeho",
    },
    {
        "value": "Academy of Performing Arts in Bratislava",
        "label_en": "Academy of Performing Arts in Bratislava",
        "label_sk": "Vysoká škola múzických umení v Bratislave",
    },
    {
        "value": "Academy of Fine Arts and Design in Bratislava",
        "label_en": "Academy of Fine Arts and Design in Bratislava",
        "label_sk": "Vysoká škola výtvarných umení v Bratislave",
    },
    {
        "value": "University of Veterinary Medicine and Pharmacy in Kosice",
        "label_en": "University of Veterinary Medicine and Pharmacy in Kosice",
        "label_sk": "Univerzita veterinárskeho lekárstva a farmácie v Košiciach",
    },
    {
        "value": "Other / Iná",
        "label_en": "Other / Iná",
        "label_sk": "Other / Iná",
    },
]

UNIVERSITY_VALUES = {item["value"] for item in UNIVERSITIES}


def is_valid_university(value: str) -> bool:
    return value in UNIVERSITY_VALUES
