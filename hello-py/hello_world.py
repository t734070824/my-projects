print("hekllo world")
print(0.2 + 0.1)
print(0.2 + 0.2)


import this

cars = ["BMW", "Mercedes", "Toyota"]
cars.sort(reverse=True)

print(len(cars))

square = [value ** 2 for value in range(100)]
print(square)

print(0 == False)


alien_0 = {
    'color': 'green',
    'points': 5
}
print(alien_0)
del alien_0['points']
print(alien_0)

print(alien_0.get("123") == None)


def greet_user():
    print("Hello")

greet_user()

def greet_user(username):
    print("Hello " + username.title() + "!")

greet_user("jesse")


def describe_pet(animal_type, pet_name):
    print("I have a " + animal_type + " named " + pet_name.title() + ".")

describe_pet("dog", "willie")

def describe_pet(pet_name, animal_type="dog"):
    print("I have a " + animal_type + " named " + pet_name.title() + ".")

describe_pet("willie")


def format_name(first, last):
    full_name = first + " " + last
    return full_name.title()


formatted_name = format_name("jesse", "chen")
print(formatted_name)


def get_formatted_name(first, last):
    full_name = first + " " + last
    return full_name.title()

def get_formatted_name(first, last, middle=""):
    if middle:
        full_name = first + " " + middle + " " + last
    else:
        full_name = first + " " + last
    return full_name.title()

print(get_formatted_name("jesse", "chen"))
print(get_formatted_name("jesse", "chen", "yong"))

def make_pizza(*toppings):
    print("Making a pizza with the following toppings:")
    for topping in toppings:
        print("- " + topping)

make_pizza("pepperoni")
make_pizza("pepperoni", "mushrooms", "green peppers")

def build_profile(first, last, **user_info):
    profile = {}
    profile['first_name'] = first
    profile['last_name'] = last
    for key, value in user_info.items():
        profile[key] = value
    return profile

user_profile = build_profile("jesse", "chen", location="beijing", field="computer science")
print(user_profile)

print("=================")
from random import randint
print(randint(1, 6))



