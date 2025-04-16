from enum import Enum


class HomeLocation(Enum):
    CHARACTER = "locations/home/character"
    REALM = "locations/home/realm"
    TOWN = "locations/home/town"
    SECT = "locations/home/sect"
    ABODE = "locations/home/abode"
    INVENTORY = "locations/home/inventory"


class TownLocation(Enum):
    DEMON_SPIRE = "locations/town/demon_spire"
