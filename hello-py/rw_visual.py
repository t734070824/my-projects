import matplotlib.pyplot as plt
from random_walk import RandomWalk

rw = RandomWalk()
rw.fill_walk()

plt.style.use('ggplot')
fig, ax = plt.subplots()

ax.scatter(rw.x_values, rw.y_values, s=15)
ax.set_aspect('equal')

plt.show()  