# Midnight Club L.A. Recompiled v1.0.1

Atualização da v1.0.0. Quem já tem a v1.0.0 atualiza **sem a ISO e sem perder os saves**.

## Para atualizar

Baixe **Midnight-Club-LA-Recompiled-Windows-x64.zip**, extraia e abra **Midnight Club L.A. Recompiled.exe**. Use **Localizar instalação**, escolha a pasta da sua v1.0.0 e clique em **Atualizar para a v1.0.1**.

- Seus saves e o `mcla.toml` não são alterados. Antes de começar, o programa guarda um ZIP dos saves e os arquivos do runtime anteriores na pasta `backups`.
- A ISO não é necessária. Feche o jogo antes e tenha cerca de 2 GB livres para a cópia temporária da tradução.
- Instalação nova: selecione sua ISO e uma subpasta, como na v1.0.0.

## Novidades

- **Mais tradução PT-BR:** 302 textos novos (o catálogo passou de 2.513 para 2.815 registros). Fim de corrida, posições, polícia e perseguições, celular, menus de pausa e opções, modo foto, partes da garagem e avisos de aposta, valer o carro e conteúdo adicional. Nomes próprios, carros, músicas e ruas continuam no original.
- **Opção de idioma no instalador:** "Traduzir o jogo para português (PT-BR)", marcada por padrão. Desmarcada, o jogo fica inteiro em inglês.
- **Adesivos (vinyls) aparecem fora da garagem.** O jogo passa a ler de volta os resultados de renderização um quadro depois (`readback_resolve = fast`), o que custa pouco. Quem já ajustou esse valor no `mcla.toml` continua com o seu.
- **Documentação mais clara sobre APIs:** FSR 4.1.2 e Frame Generation por IA só existem no DirectX 12. Em Vulkan o FSR é o 3.1 e a Frame Generation ainda não gera quadros.
- Controle `readback_resolve_box_filter` no SDK, desligado por padrão, para quem quiser experimentar (não melhorou os adesivos nos testes).

## Limitações conhecidas

- Os adesivos têm a resolução original do jogo: o jogo os monta numa textura de 512×512. Isso não mudou.
- Pode aparecer uma linha verde discreta na borda em alta velocidade com Frame Generation; desligá-lo eliminou o artefato nos testes relatados.
- A cobertura da tradução ainda pode exigir revisão durante a campanha.
- As melhorias não foram testadas no Linux.
- O DLSS da NVIDIA não está implementado.

## Validação

A atualização foi testada em uma instalação simulada da v1.0.0, montada com o pacote e o runtime reais da v1.0.0: saves e `mcla.toml` ficaram idênticos byte a byte, e os 80 recursos de texto traduzidos ficaram idênticos aos de uma instalação nova. Instalações novas com e sem tradução também foram testadas, pelo caminho de teste do instalador (sem a extração da ISO).

Esta versão foi compilada de forma incremental, sem uma reconstrução limpa completa como na v1.0.0, e não foi reinstalada em um Windows limpo. Os arquivos `release/runtime-manifest.json` e `release/source-audit.json` descrevem exatamente o que foi conferido.

## Arquivos

- **Windows-x64.zip:** pacote do jogador; nenhuma ISO, dado extraído ou save incluído.
- **SHA256SUMS.txt:** hashes para conferir os downloads.

Créditos e licenças GPL/terceiros acompanham a distribuição. Projeto comunitário sem afiliação ou endosso da Rockstar Games ou AMD.
