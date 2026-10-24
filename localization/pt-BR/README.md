# Tradução PT-BR

Arquivos públicos de tradução, sem dumps de texto original ou arquivos do jogo:

- `native-texts.json`: traduções indexadas pelo identificador nativo; SHA-256 do texto original e dos quatro recursos de idioma para validar a edição suportada.
- `dialogue-pt-BR.json`: 317 falas identificadas por hash, sem os textos originais.
- `subtitle-files.json`: índices e hashes dos 76 recursos de legendas.
- `host-menu-texts.json`: rótulos dos menus criados pelo código deste fork.

O build central executa `localization/build_ptbr.py` e `localization/generate_menu.py`. O primeiro usa somente a cópia do jogo fornecida localmente para criar `out/localization/pt-BR/game/`. Verifica hashes de origem, tags, recursos finais e preservação dos outros idiomas. Uma falha não substitui o arquivo traduzido anterior. Os demais arquivos do jogo usam hardlinks ou cópias; não devem ser editados no diretório de saída.

Menus, dicas, telefone, missões e customização foram conferidos durante os testes. As falas identificadas foram traduzidas e verificadas no arquivo; ainda é necessária a conferência visual de toda a campanha. Não inclui dublagem. Nomes próprios e o velocímetro em MPH são preservados.

Para gerar manualmente, depois de preparar o SDK e extrair sua ISO:

```powershell
python localization/build_ptbr.py
python localization/generate_menu.py
```

O executável localiza a tradução automaticamente ao iniciar com `mcla_ptbr = true`. Saves e configurações pessoais não fazem parte da tradução nem do repositório.
