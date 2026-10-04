def converter(texto):
    try:
        return int(texto)
    except ValueError:
        return None

valores = [converter(t) for t in ["1", "dois", "3"]]
try:
    resultado = 10 / 0
except ZeroDivisionError as e:
    mensagem = str(e)
finally:
    fim = "sempre"
