import pandas as pd

lista = [3, 7, 10, 15]
dobro = [x * 2 for x in lista]

total = 0
for x in lista:
    total = total + x

n = 0
while n < 10000:
    n = n + 1

i = 0
while True:
    i = i + 1
    if i == 5:
        break

df = pd.DataFrame({"peso": [312.5, 298.0, None]})
media = df["peso"].mean()
print(media)
