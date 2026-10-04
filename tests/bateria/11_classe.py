class Animal:
    def __init__(self, nome, peso):
        self.nome = nome
        self.peso = peso

    def engordar(self, kg):
        self.peso = self.peso + kg
        return self.peso

boi = Animal("br-01", 300)
novo = boi.engordar(10)
