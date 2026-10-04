import pandas as pd
lista = []
for i in range(3000):
    lista = lista + [i]
linhas = []
for i in range(300):
    linhas.append({"i": i})
    df = pd.DataFrame(linhas)
