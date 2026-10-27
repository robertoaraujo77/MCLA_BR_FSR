# Configuração

O configurador está no mesmo executável do instalador. Para uma instalação reconhecida, ele carrega as opções locais; você não precisa preparar novamente a ISO para mudar gráficos.

## Gráficos

- **Resolução de renderização:** 1× = 720p, 2× = 1440p, 3× = 2160p de referência vertical. A largura acompanha a proporção. É diferente do tamanho da janela/saída do monitor.
- **Proporção automática:** usa a tela em fullscreen ou a área da janela na inicialização. Também há 16:9 e 21:9 manuais.
- **API gráfica:** Automático deixa o runtime escolher. **FSR 4.1.2 e Frame Generation por IA só funcionam no DirectX 12**; para usá-los, selecione DirectX 12. Em Vulkan o modo FSR usa o FSR 3.1 e a Frame Generation não gera quadros, então deixe-a desligada.
- **MSAA:** padrão inicial. Para usar os modos FSR, selecione FSR no antisserrilhado.
- **Native AA:** sem redução de resolução pelo FSR. Qualidade, Equilibrado e Desempenho reduzem a resolução usada na reconstrução, com diferentes compromissos de imagem e custo.
- **Frame Generation:** desligado inicialmente. Requer DirectX 12. Segundo a documentação da AMD, a versão por IA exige Windows 11 e uma GPU Radeon RX 9000 ou mais nova; o FSR 4.1.2 aceita também a série RX 7000. Não aumenta a taxa da simulação do jogo. Em Vulkan não há geração de quadros. Verifique o provedor efetivo no registro.
- **VSync e FPS:** comece com os padrões. Ajuste conforme a tela e a estabilidade desejada.
- **Sombras, efeitos, detalhe e densidade:** os perfis são atalhos opcionais; não são aplicados sem sua escolha.

Clique em **Salvar configurações** e reinicie o jogo para aplicar. As opções do menu do próprio jogo continuam disponíveis.

## Perfil e controles

O nome inicial é **User**. Escolha até 15 caracteres ASCII aceitos pelo campo. Alterar o nome pode selecionar outra pasta de perfil; os saves antigos não são apagados.

Os ícones começam como Xbox. Você pode selecionar PlayStation ou Automático. A escolha muda as indicações visuais e não substitui a configuração física do controle.

## Saves e dados

Os dados pertencem à instalação do jogador. A aba mostra o caminho e permite exportar um ZIP com o jogo fechado. Os backups das configurações ficam em `config-backups`; não acompanham o pacote distribuído.
