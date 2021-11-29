from collections import namedtuple
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
import json
from math import asin, cos, pow, radians, sin, sqrt

from ..aeroplan import AeroplanStatus, FareBrand
from ..locations import Airport


SegmentCalculation = namedtuple("SegmentCalculation", (
    "distance",
    "app", "app_earning_rate", "app_bonus_factor", "app_bonus",
    "sqm", "sqm_earning_rate",
))
EarthRadiusMi = 3959.0


@dataclass
class Airline:

    id: str
    name: str
    region: str
    website: str
    logo: str
    star_alliance_member: bool
    earns_app: bool
    earns_sqm: bool
    earning_rates: dict

    def __eq__(self, other):
        return self.id == other.id

    def _distance(self, origin: Airport, destination: Airport):
        """Calculate the distance from origin to destination. If there isn't a pre-recorded
        Aeroplan distance, calculate the haversine distance.
        """

        if distance := origin.distances.get(destination.iata_code):
            return distance.distance or distance.old_distance
        else:
            d_lat = radians(destination.latitude - origin.latitude)
            d_lon = radians(destination.longitude - origin.longitude)
            origin_lat = radians(origin.latitude)
            destination_lat = radians(destination.latitude)

            a = pow(sin(d_lat / 2), 2) + pow(sin(d_lon / 2), 2) * cos(origin_lat) * cos(destination_lat)
            c = 2 * asin(sqrt(a))

            return EarthRadiusMi * c

    def calculate(
        self,
        origin: Airport,
        destination: Airport,
        fare_brand: FareBrand,
        fare_class: str,
        ticket_number: str,
        aeroplan_status: AeroplanStatus,
    ):
        distance = self._distance(origin, destination)
        if not distance:
            return SegmentCalculation(distance, 0, 0, 0, 0, 0, 0)

        app_earning_rate = self.earning_rates.get(fare_class, None) or self.earning_rates.get(fare_brand.name, 0)
        app_bonus_factor = aeroplan_status.bonus_factor
        app = max(distance * app_earning_rate, aeroplan_status.min_earning_value) if self.earns_app else 0
        app_bonus = min(app, distance) * app_bonus_factor

        sqm_earning_rate = self.earning_rates.get(fare_class, None) or self.earning_rates.get(fare_brand.name, 0)
        sqm = max(distance * sqm_earning_rate, aeroplan_status.min_earning_value) if self.earns_sqm else 0

        return SegmentCalculation(
            distance,
            int(app),
            app_earning_rate,
            app_bonus_factor,
            int(app_bonus),
            int(sqm),
            sqm_earning_rate,
        )


class AirCanadaAirline(Airline):
    pass


@cache
def _load_airline_partners():
    with resources.open_text("ac_calc.airlines", "partners.json") as f:
        partners = json.load(f)

    return tuple((
        Airline(**partner)
        for partner in partners
    ))


AirCanada = AirCanadaAirline(
    id="air-canada",
    name="Air Canada",
    region="Canada & U.S.",
    website="http://www.aircanda.com",
    logo=None,
    star_alliance_member=True,
    earns_app=True,
    earns_sqm=True,
    earning_rates={
        "Domestic": {
            "*": {
                "Basic": 0.10,
                "Standard": 0.25,
                "Flex": 1.0,
                "Comfort": 1.15,
                "Latitude": 1.25,
                "Premium Economy (Lowest)": 1.25,
                "Premium Economy (Flexible)": 1.25,
                "Business (Lowest)": 1.50,
                "Business (Flexible)": 1.50,
            },
        },
        "Transborder": {
            "*": {
                "Basic": 0.25,
                "Standard": 0.50,
                "Flex": 1.0,
                "Comfort": 1.15,
                "Latitude": 1.25,
                "Premium Economy (Lowest)": 1.25,
                "Premium Economy (Flexible)": 1.25,
                "Business (Lowest)": 1.50,
                "Business (Flexible)": 1.50,
            },
        },
        "International": {
            "*": {
                "Basic": 0.25,
                "Standard": 0.50,
                "Flex": 1.0,
                "Comfort": 1.15,
                "Latitude": 1.25,
                "Premium Economy (Lowest)": 1.25,
                "Premium Economy (Flexible)": 1.25,
                "Business (Lowest)": 1.50,
                "Business (Flexible)": 1.50,
            },
        },
    },
)


AIRLINES = (AirCanada,) + _load_airline_partners()


DEFAULT_AIRLINE, DEFAULT_AIRLINE_INDEX = AirCanada, 0
