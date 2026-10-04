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

## Junto com a viper

A extensão traz também o que a [viper](https://github.com/GF-Linux/viper), a biblioteca de funções
próprias, precisa no editor. Assim nada é configurado à mão em cada máquina:

- **snippet:** digite `replacement` e aperte Tab. A chamada nasce como
  `replacement(lista, 'palavra', lambda x: condição)`, e o Tab passa de um campo para o próximo;
- **o nome dos parâmetros em cinza** dentro das chamadas, pelo Pylance
  (`python.analysis.inlayHints.callArgumentNames: all`);
- **os snippets primeiro** na lista de sugestões, só em arquivos Python. Sem isso, o Tab pegaria a
  sugestão do Pylance, sem o `lambda`.

São valores padrão: se você mudar qualquer um nas suas configurações, vale o seu.

Parte do projeto [True Coral](https://github.com/GF-Linux/truecoral).
