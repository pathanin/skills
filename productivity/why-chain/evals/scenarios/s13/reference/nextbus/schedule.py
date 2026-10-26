class Schedule:
    def __init__(self, service_date, trips):
        self.service_date = service_date
        self.trips = sorted(trips, key=lambda trip: trip.arrival)

    def __iter__(self):
        return iter(self.trips)
