# True Coral

**A coral verdadeira.** A falsa coral imita a perigosa e engana quem olha; a verdadeira é o que
parece. O True Coral mostra, linha por linha, o que o seu código fez de verdade: o que cada linha
guardou, quantas voltas cada laço deu e por onde saiu, quantas vezes cada condição deu True ou
False, o que o print escreveu e, se der erro, onde e por quê — em português.

Dois jeitos de ver, o mesmo motor por trás:

- **no VS Code** — ao salvar, cada linha ganha os chips ao lado; o detalhe aparece ao passar o mouse;
  erro vira sublinhado vermelho e entra no painel de Problemas (`vscode/`);
- **no terminal** — `coral arquivo.py` desenha o arquivo com os mesmos chips.

| marcação | o que diz |
|---|---|
| `= valor · tipo` | o que a linha guardou; num laço, a evolução até o valor final |
| `↻ N voltas · …` | quantas voltas o laço deu e por onde saiu: fim, condição falsa, break ou limite |
| `True ×a · False ×b` | quantas vezes a condição deu cada resposta |
| `› texto` | o que o print escreveu (e `retorna None`, apagado, à parte) |
| `! …` | um fato que merece atenção: vazios (NaN) num DataFrame, um NaN |
| `✕ Erro` | onde parou, com a explicação em português e a mensagem original |
| `· não rodou` | linha que o caminho do programa nunca alcançou |

**O código roda de verdade.** Se ele apaga ou grava arquivo, isso acontece. Há limite de tempo
(padrão 10 s): um laço infinito para ali e é marcado como tal. O `input()` fica desligado.

## Como funciona

```
motor.py  (Python, só biblioteca padrão)  →  JSON  →  coral, no terminal
                                                   →  a extensão do VS Code, que só desenha
```

O motor roda com o Python do seu projeto (o `.venv` da pasta, o ambiente escolhido no VS Code ou
o `python3`) e acompanha cada linha com `sys.settrace`. A extensão é fina de propósito: se o
Python mudar, o conserto é no motor — que é Python e tem teste.

Status: 0.1.0, em teste. Testado no Fedora 44 com Python 3.14 e VS Code 1.140.
