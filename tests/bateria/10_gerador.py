def contar(ate):
    i = 0
    while i < ate:
        yield i
        i += 1

total = 0
for valor in contar(4):
    total += valor
