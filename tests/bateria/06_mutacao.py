import pandas as pd
lista = []
for x in range(4):
    lista.append(x * 10)
df = pd.DataFrame({"peso": [300.0, 310.0]})
df["kg_dobro"] = df["peso"] * 2
df.loc[0, "peso"] = 999
config = {"a": 1}
config["b"] = 2
