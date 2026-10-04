import warnings
import pandas as pd
warnings.warn("um aviso de teste")
df = pd.DataFrame({"a": [1, 2]})
serie = df["a"]
serie[0] = 50
print("fim")
