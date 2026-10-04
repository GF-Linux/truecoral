# Mudanças

## 0.2.0

Correções que a bateria de testes (`tests/bateria/`) encontrou:

- **laço dentro de laço**: o laço de fora contava as voltas do de dentro. Agora a volta é contada no
  próprio cabeçalho, e o laço que roda várias vezes diz quantas: `↻ 3 execuções · 9 voltas no total
  · saiu pelo break · linha 5 ×3`
- **laço só longo não é "infinito"**: um `for` que bate no limite de tempo diz "parou no limite antes
  de terminar"; o "laço infinito?" fica para o `while` cuja condição nunca deu False

Novidades:

- **erro tratado**: `⚡ ValueError → tratado na linha 4` onde o erro nasceu — o `try/except` deixa de ser
  invisível
- **o que a função devolveu**: `↩ 2 → 6 → 24 → 120` no `return` (e no `yield`), e `chamada 5×` no `def`
- listas e textos grandes são resumidos em tempo constante (`reprlib`): uma lista que cresce dentro do
  laço não é mais relida inteira a cada volta

## 0.1.0

O motor, o comando `coral` e a extensão do VS Code.
