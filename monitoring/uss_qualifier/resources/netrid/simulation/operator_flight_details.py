import random
import string

from faker import Faker
from uas_standards.ansi_cta_2063_a import SerialNumber
from uas_standards.interuss.automated_testing.rid.v1 import injection


class OperatorFlightDataGenerator:
    """A class to generate fake data detailing operator name, operation name and operator location, it can be customized for locales and locations"""

    def __init__(self, random: random.Random):
        self.fake = Faker()
        self.random = random

    def generate_serial_number(self):
        return str(SerialNumber.generate_valid())

    def generate_registration_number(self, prefix="CHE"):
        registration_number = prefix + "".join(
            self.random.choices(string.ascii_lowercase + string.digits, k=13)
        )
        return registration_number

    def generate_operation_description(self):
        operation_description = [
            "Electricity Grid Inspection",
            "Wind farm survey",
            "Solar Panel Inspection",
            "Traffic Monitoring",
            "Emergency services / rescue",
            "Delivery operation, see more details at https://deliveryops.com/operation",
            "News recording, live event",
            "Crop spraying / Agricultural Inspection",
        ]
        return self.random.choice(operation_description)

    def generate_operator_location(self, centroid):
        # TODO: Inject operator location altitude
        operator_location = injection.LatLngPoint(lat=centroid.y, lng=centroid.x)
        return operator_location

    def generate_operator_id(self, prefix="OP-"):
        operator_id = prefix + "".join(
            self.random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        return operator_id

    def generate_company_name(self):
        return self.fake.company()
