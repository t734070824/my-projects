import matplotlib.pyplot as plt

plt.style.use('ggplot')
fig,ax = plt.subplots()

x_values = range(1, 1001)
y_values = [x**2 for x in x_values]

# Scatter plot
ax.scatter(x_values, y_values, c=y_values, cmap=plt.cm.Blues,s=10)

# Set chart title and label axes.
ax.set_title("Square Numbers", fontsize=24)
ax.set_xlabel("Value", fontsize=14)
ax.set_ylabel("Square of Value", fontsize=14)
# Set size of tick labels.
ax.tick_params(axis='both', labelsize=14)
# Set axis limits and ticks

ax.axis([0, 1100, 0, 1_100_000])

plt.show()