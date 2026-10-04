# True Coral para VS Code

O que cada linha do seu código Python fez de verdade, ao lado da linha: o que ela guardou, quantas
voltas cada laço deu e por onde saiu, quantas vezes cada condição deu True ou False, o que o print
escreveu e, se der erro, onde e por quê — em português.

- **Quando:** ao salvar (Ctrl+S). Ao editar, as marcações somem até o próximo salvamento.
- **Detalhes:** passe o mouse na linha.
- **Erro:** chip vermelho, sublinhado e entrada no painel de Problemas.
- **O código roda de verdade**, com limite de tempo (padrão 10 s) para laço infinito. O `input()` fica desligado.

Comandos: `True Coral: analisar este arquivo` · `limpar as marcações` · `ligar ou desligar ao salvar`.
Configuração: `truecoral.pythonPath`, `truecoral.tempo`, `truecoral.aoSalvar`.

Parte do projeto [True Coral](https://github.com/GF-Linux/truecoral).
