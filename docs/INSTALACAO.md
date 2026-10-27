# Instalação

## Antes de começar

Use Windows de 64 bits e sua ISO da edição **Complete Edition para Xbox 360**. Reserve espaço para a ISO, os dados preparados e os arquivos temporários. A disponibilidade de DX12/Vulkan e das opções AMD depende da GPU e do driver.

## Preparar

1. Extraia o pacote e execute **Midnight Club L.A. Recompiled.exe**.
2. Em **Procurar ISO**, escolha seu arquivo `.iso`.
3. Use uma pasta vazia para o jogo. O destino não pode ser a própria pasta do instalador; uma subpasta é permitida. Não coloque a ISO dentro do destino.
4. Opcionalmente configure gráficos, nome do jogador e botões nas abas correspondentes.
5. Deixe marcado **Traduzir o jogo para português (PT-BR)**, que é o padrão e o recomendado. Desmarque se preferir o jogo em inglês.
6. Deixe marcado **Criar atalho na Área de Trabalho** se quiser iniciar diretamente o jogo.
7. Clique em **Preparar meu jogo** e acompanhe o registro. Aguarde a conclusão.

O instalador verifica o pacote, extrai sua ISO, aplica a tradução (se estiver marcada), instala o runtime e grava as configurações escolhidas. As ferramentas internas ficam no cache de preparação; fontes de edição não são copiadas para a pasta do jogador.

## Idioma

A escolha de idioma é feita na instalação. Com a tradução marcada, os menus, o telefone, as missões, a garagem e as legendas ficam em português. Sem ela, o jogo fica inteiro em inglês, inclusive os menus do projeto. Para trocar depois, reinstale com a ISO na mesma pasta: os saves ficam em `userdata` e não são apagados.

## Atualizar uma instalação existente

Abra o novo **Midnight Club L.A. Recompiled.exe** e use **Localizar instalação** (ou abra-o de dentro da pasta do jogo). Quando houver uma versão mais nova, o botão principal passa a ser **Atualizar para a vX**.

- **A ISO não é necessária.**
- **Seus saves e o `mcla.toml` não são alterados.** Antes de começar, o programa guarda um ZIP dos saves em `backups` (sem o cache de shaders).
- Troca os arquivos do jogo e acrescenta as traduções novas sobre as que você já tem. Os arquivos do runtime anteriores ficam em `backups`.
- Feche o jogo antes e tenha cerca de 2 GB livres: a atualização da tradução faz uma cópia temporária de `xarchive_cache.rpf` e só a substitui depois de verificada.
- Uma instalação feita sem tradução não recebe tradução na atualização. Para mudar, reinstale com a ISO.

Com a instalação já na versão mais nova, o botão vira **Reinstalar com a ISO**, que refaz os dados do jogo e também mantém os saves.

## Depois

O mesmo **Midnight Club L.A. Recompiled.exe** fica na pasta do jogo para configurar e jogar. O **mcla.exe** e o atalho da Área de Trabalho iniciam diretamente o jogo. Não mova apenas o mcla.exe: ele precisa dos dados e bibliotecas ao lado dele.

A aba **Saves e dados** mostra o local real dos dados. Feche o jogo antes de exportar um backup ZIP. Faça backup antes de trocar de versão ou de nome do jogador.

## Problemas

- **Pasta já ocupada:** escolha uma pasta vazia ou uma instalação reconhecida pelo programa.
- **Preparação interrompida:** consulte a aba Registro e copie as mensagens. Confira espaço livre e se a ISO corresponde à edição esperada.
- **Instalação não encontrada:** use Localizar instalação e selecione a pasta que contém mcla.exe.
- **Configuração não salva:** feche o jogo e tente novamente.
- **Defeitos com FG:** desligue Frame Generation e reinicie para comparar.

Não compartilhe sua ISO, arquivos extraídos nem saves pessoais em relatórios. Registros podem conter caminhos locais: revise antes de publicar.
