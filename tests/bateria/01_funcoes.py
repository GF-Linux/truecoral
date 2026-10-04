def dobro(n):
    resultado = n * 2
    return resultado

a = dobro(3)
b = dobro(10)
c = dobro(a)

def fatorial(n):
    if n <= 1:
        return 1
    return n * fatorial(n - 1)

f = fatorial(5)
