comando = "parar"
match comando:
    case "andar":
        acao = 1
    case "parar":
        acao = 0
    case _:
        acao = -1
