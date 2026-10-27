# Como as melhorias foram feitas

## Base e autoria

O trabalho parte de mcla-recomp e do fork de RenanQueiroz, com ReXGlue. A recompilação estática e as bibliotecas existentes são trabalhos dos autores creditados; as alterações deste projeto não substituem essa autoria.

## Tradução PT-BR

Textos de recursos e strings usadas pelo código foram catalogados e substituídos por traduções. Há 2.815 registros nativos e 317 linhas de diálogo, incluindo 76 recursos de legendas. A preparação aplica as alterações aos dados extraídos da ISO do usuário. Não há redistribuição do arquivo de recursos original neste repositório.

A revisão incluiu acentos, largura dos rótulos, contadores/variáveis, mensagens do telefone, missões e garagem. Nomes próprios e marcas foram preservados. A existência de uma linha traduzida no catálogo não garante que todas as situações da campanha já tenham sido verificadas em tela.

## Proporção e interface

Foram ajustados os caminhos de desenho para preservar tamanho e proporção dos elementos de interface: HUD, telefone, painéis, garagem e GPS. O HUD pode ir aos cantos da saída ultrawide. Ícones do GPS e o cursor móvel receberam correções próprias para evitar deformação e deslocamento da seleção.

O modo automático calcula a proporção a partir da saída/janela na inicialização. O logo original do menu do jogo foi mantido.

## FSR e Frame Generation

A integração fornece modos de reconstrução e seleciona provedores conforme a API e o hardware. O caminho DX12 foi testado com FSR 4.1.2 e FG AMD 4.0.2 por IA. Vulkan mantém FSR 3.1: o FSR 4.1.2 e a Frame Generation por IA da AMD só existem para DirectX 12 no SDK, e em Vulkan a Frame Generation ainda não gera quadros. Foram feitos ajustes de apresentação, transições de pausa e bordas durante os testes. Artefatos residuais continuam documentados no README.

Os algoritmos e provedores são da AMD; este projeto integra e configura esses componentes.

## Instalador e configurador

A interface Windows usa WPF e C#. Um pacote interno com manifesto SHA-256 contém runtime e ferramentas de preparação. A ISO é fornecida pelo jogador; a preparação extrai dados, aplica traduções e grava uma instalação com somente os arquivos necessários para jogar e configurar.

Instalação e configuração usam o mesmo executável. O atalho opcional inicia mcla.exe diretamente. Configurações existentes são lidas localmente; arquivos pessoais do mantenedor não fazem parte do pacote.

## Validação

As correções foram desenvolvidas com assistência de ferramentas de programação por IA e conferidas em testes visuais pelo mantenedor, incluindo DX12, Vulkan, ultrawide, pausa, telefone, GPS e garagem. Isso não substitui testes em outras GPUs ou durante toda a campanha.
