# Configuração

O configurador está no mesmo executável do instalador. Para uma instalação reconhecida, ele carrega as opções locais; você não precisa preparar novamente a ISO para mudar gráficos.

## Gráficos

- **Resolução de renderização:** 1× = 720p, 2× = 1440p, 3× = 2160p de referência vertical. A largura acompanha a proporção. É diferente do tamanho da janela/saída do monitor.
- **Proporção automática:** usa a tela em fullscreen ou a área da janela na inicialização. Também há 16:9 e 21:9 manuais.
- **API automática:** deixa o runtime escolher. Se quiser testar os provedores AMD por IA validados aqui, selecione DirectX 12 e hardware compatível.
- **MSAA:** padrão inicial. Para usar os modos FSR, selecione FSR no antisserrilhado.
- **Native AA:** sem redução de resolução pelo FSR. Qualidade, Equilibrado e Desempenho reduzem a resolução usada na reconstrução, com diferentes compromissos de imagem e custo.
- **Frame Generation:** desligado inicialmente. Requer o caminho DirectX 12 compatível; não aumenta a taxa da simulação do jogo. Verifique o provedor efetivo no registro.
- **VSync e FPS:** comece com os padrões. Ajuste conforme a tela e a estabilidade desejada.
- **Sombras, efeitos, detalhe e densidade:** os perfis são atalhos opcionais; não são aplicados sem sua escolha.

Clique em **Salvar configurações** e reinicie o jogo para aplicar. As opções do menu do próprio jogo continuam disponíveis.

## Perfil e controles

O nome inicial é **User**. Escolha até 15 caracteres ASCII aceitos pelo campo. Alterar o nome pode selecionar outra pasta de perfil; os saves antigos não são apagados.

Os ícones começam como Xbox. Você pode selecionar PlayStation ou Automático. A escolha muda as indicações visuais e não substitui a configuração física do controle.

## Saves e dados

Os dados pertencem à instalação do jogador. A aba mostra o caminho e permite exportar um ZIP com o jogo fechado. Os backups das configurações ficam em `config-backups`; não acompanham o pacote distribuído.
