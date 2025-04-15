class Car:
    def __init__(self, make, model, year):
        self.make = make
        self.model = model
        self.year = year
        self.odometer_reading = 0

    def start(self):
        print(f"{self.year} {self.make} {self.model} is starting.")

    def stop(self):
        print(f"{self.year} {self.make} {self.model} is stopping.")