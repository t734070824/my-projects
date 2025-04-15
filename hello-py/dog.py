class Dog:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def bark(self):
        return f"{self.name} says Woof!"
    
    def sit(self):
        return f"{self.name} is sitting."
    
    def roll_over(self):
        return f"{self.name} rolled over."
    







my_dog = Dog("Willie", 6)
print(f"My dog's name is {my_dog.name}.")

print(f"My dog is {my_dog.age} years old.")
print(my_dog.bark())
print(my_dog.sit())