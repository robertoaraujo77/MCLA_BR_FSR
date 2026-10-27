# Compilar o código correspondente à v1.0.1

Estas instruções são para desenvolvedores. Jogadores devem usar o ZIP da release e sua própria ISO.

## Revisões e dependências

- A base do projeto é `eaf3ad4b8701de537ea55411f7b413ad98bf73f1` do fork creditado.
- ReXGlue: `f5337cdc947ff6d4c4196737e2c807a48f2a1fc2`.
- `patches/rexglue-release.patch` reúne as modificações do SDK usadas nesta distribuição. Ele substitui a aplicação sequencial dos antigos patches da base.
- Alterações locais de FFmpeg acompanham um patch separado; revisões de todos os submódulos estão em `patches/dependencies.json`.
- Provedores AMD oficiais: revisão e hashes fixados em `scripts/amd-fsr-manifest.json`. Não são algoritmos de autoria deste fork.

O ZIP de fontes completo inclui o SDK já modificado e seus submódulos. Nesse caso, o preparador verifica o manifesto e usa esses fontes sem tentar cloná-los novamente. No checkout Git enxuto, ele obtém a revisão fixada e aplica os patches.

## Ferramentas Windows x64

Visual Studio Build Tools 2022 com C++, Clang 20.1.8, CMake 3.25 ou superior, Ninja, Git, Python 3.11+ e Vulkan SDK para o caminho FSR Vulkan. O script de preparação usa downloads de fontes e dependências; o instalador do jogador já leva os componentes prontos.

Use um caminho curto, por exemplo `C:\src\mcla`, e um terminal **x64 Native Tools** do Visual Studio. O compilador de shaders da dependência AMD tem limites próprios de caminho.

```powershell
.\scripts\build_release.ps1 -Iso "D:\Jogos\MCLA.iso" -ClangDirectory "C:\LLVM\bin"
```

O script prepara o SDK fixado, aplica os patches consolidados, verifica os provedores AMD, compila/instala o SDK, extrai sua ISO, gera a tradução, executa o codegen e compila o jogo. O resultado fica em `out/build/win-amd64-release`.

A ISO, o código gerado a partir dela, os recursos traduzidos resultantes, saves e caches não acompanham o Git. O header `src/ptbr_menu.h` já corresponde ao binário; não o substitua por uma geração de catálogo de outra revisão.

## Instalador/configurador

Baixe do site oficial do Python o pacote **Windows embeddable x64 Python 3.12** e extraia-o em uma pasta de ferramentas. Os avisos/licenças desse pacote devem acompanhar a distribuição. Os arquivos VC Runtime redistribuídos exigem também os respectivos avisos e condições Microsoft.

```powershell
python installer/package.py --runtime out/build/win-amd64-release --python C:\tools\python-embed-312 --version 1.0.1
powershell -NoProfile -File installer/source/build.ps1
```

O pacote usa uma lista explícita de arquivos de runtime e entradas de tradução. Não empacota diretórios de saves, logs ou mcla.toml. A UI WPF e o backend de preparação estão em `installer/source`. O compilador C# do .NET Framework do Windows gera o executável único em `installer/dist`.

O instalador aplica os dados da ISO local; não executa esta compilação C++ no computador do jogador.

## Proveniência e validação

`release/runtime-manifest.json` registra os hashes do conteúdo da versão testada. Eles identificam os binários distribuídos, mas não prometem builds bit a bit idênticos: timestamps e versões das ferramentas podem mudar o resultado.

A revisão foi conferida contra os fontes da aplicação usados no build final. Em seguida, o ZIP de fontes foi extraído em um diretório novo e os scripts recompilaram o SDK, as bibliotecas FidelityFX, o jogo a partir da ISO local e o instalador/configurador. A validação ocorreu no Windows do mantenedor, com ferramentas já instaladas; não foi uma reinstalação limpa do sistema operacional nem uma promessa de hashes binários idênticos.

Mantenha créditos, licença GPL e licenças dos componentes de terceiros. O código correspondente deve acompanhar ou ser disponibilizado junto da distribuição binária conforme as respectivas licenças.
