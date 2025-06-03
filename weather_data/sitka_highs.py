from pathlib import Path
import csv
import matplotlib.pyplot as plt
from datetime import datetime

path = Path('sitka_weather_2014.csv')
lines = path.read_text().splitlines()

reader = csv.reader(lines)

header_row = next(reader)



date, highs, lows = [],[],[]
for row in reader:
    highs.append(int(row[1]))
    lows.append(int(row[3]))
    date.append(datetime.strptime(row[0], '%Y-%m-%d'))


plt.style.use('ggplot')
fig, ax = plt.subplots()

ax.plot(date, highs, color='red', alpha=0.5, linewidth=3)
ax.plot(date, lows, color='blue', alpha=0.5, linewidth=3)

ax.fill_between(date, highs, lows, facecolor='blue', alpha=0.1)


ax.set_title("Daily high and low temperatures, 2014", fontsize=24)
ax.set_xlabel('', fontsize=16)
fig.autofmt_xdate()
ax.set_ylabel("Temperature (F)", fontsize=16)
ax.tick_params(labelsize=16)

plt.show()



