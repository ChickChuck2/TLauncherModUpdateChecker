# Guia Completo: Otimização de Performance & Guia Multijogador (Forge 1.20.1)

Este documento registra todas as alterações analíticas realizadas no modpack **UltimateMinePack** para solucionar problemas graves de carregamento de inventário e chunks, além de um guia técnico com recomendações para servidores e partidas multijogador.

---

## 1. Modificações de Performance Aplicadas

### 1.1 Eliminação do Congelamento de 1 Minuto no Inventário
* **Problema Identificado**:
  * O Just Enough Items (JEI) estava configurado com `TooltipSearchMode = ENABLED`. Em modpacks com mais de 200 mods, o JEI lia e indexava o texto de dezenas de milhares de itens de forma síncrona na thread principal ao abrir o inventário pela primeira vez.
  * O Minecraft vanilla 1.20.1 possui um gargalo nativo de reconstrução das árvores de busca de abas criativas.
* **Ajustes Aplicados**:
  1. **JEI** (`D:\Games\.minecraft\versions\UltimateMinePack\config\jei\jei-client.ini`):
     ```ini
     TooltipSearchMode = REQUIRE_PREFIX
     ```
     *Efeito*: O inventário agora abre instantaneamente (1 a 2 segundos). Para pesquisar itens pelo texto de seus tooltips, basta digitar `#` antes do termo (ex: `#energia`, `#forge:ingots`).
  2. **ModernFix** (`D:\Games\.minecraft\versions\UltimateMinePack\config\modernfix-mixins.properties`):
     ```properties
     mixin.perf.blast_search_trees.force=true
     ```
     *Efeito*: Desativa a reconstrução congelante da árvore de busca vanilla sem afetar o funcionamento do JEI ou do EMI.

---

### 1.2 Novos Mods Adicionados Nativamente ao TLauncher
*(Nenhum arquivo `.jar` foi baixado manualmente; os metadados oficiais com hash SHA-1 e tamanho foram injetados em `TLauncherAdditional.json` para que o TLauncher realize o download oficial de forma segura ao iniciar).*

1. **Clumps** (ID CurseForge: `256717` | Versão: `12.0.0.4`):
   * **Função**: Agrupa milhares de orbes de experiência flutuantes em uma única entidade.
   * **Benefício**: Evita quedas brutais de FPS e congelamento de chunks quando você derrota chefes ou farmas mobs (ex: Cataclysm, Mowzie's Mobs, Born in Chaos).
   * **Verificação TLauncher**: Confirmado no repositório `rescl.tlauncher.org`.
2. **FTB Chunks (Forge)** (ID CurseForge: `314906` | Versão: `2001.3.8`):
   * **Função**: Reivindicação de territórios (claims), carregamento de chunks (force loading) e mapa com suporte a equipes.
   * **Benefício**: Essencial para partidas multijogador. Integra-se perfeitamente com os mods já instalados no pack (`FTB Library`, `FTB Teams` e `FTB Quests`).
   * **Verificação TLauncher**: Confirmado no repositório `rescl.tlauncher.org`.

---

## 2. Diagnóstico de Chunks & Solução Definitiva

### 2.1 Por que as Chunks Demoram para Carregar?
O modpack possui uma combinação extremamente densa de geração de mundo procedural:
* **Dynamic Trees** (+ 8 addons de árvores dinâmicas)
* **Terralith**
* **Biomes O' Plenty**
* **Oh The Biomes We've Gone**

Quando o jogador se desloca rapidamente (correndo, voando ou a cavalo), o processador precisa calcular ramificações matemáticas de galhos e raízes de árvores dinâmicas enquanto calcula as camadas de relevo dos três mods de biomas em tempo real.

### 2.2 Procedimento Recomendado: Pré-Geração com Chunky (Já Instalado!)
O modpack **já possui o mod Chunky instalado**. Para que as chunks carreguem instantaneamente sem travar o processador durante o jogo:
1. Inicie o mundo (ou o servidor).
2. Execute os seguintes comandos no chat (ou console):
   ```text
   /chunky radius 2500
   /chunky start
   ```
3. O Chunky gerará um raio de 2500 blocos em volta do ponto inicial.
4. Para checar o progresso:
   ```text
   /chunky progress
   ```
5. Quando finalizar, todas as chunks estarão salvas no disco. Ao jogar, o jogo apenas lerá os dados salvos em vez de tentar calcular a matemática pesada em tempo real.

---

## 3. Guia de Otimização para Multijogador (Servidores e Coop)

Para jogar com amigos sem perda de pacotes, lag de tick (TPS baixo) ou desconexões inesperadas:

### 3.1 Proteção e Gestão de Territórios
* **FTB Chunks + FTB Teams**:
  * Já integrado ao seu modpack.
  * Abra o mapa do FTB Chunks (tecla padrão `M` ou pelo botão superior esquerdo do inventário).
  * Clique com o botão esquerdo para reivindicar chunks (impede que creepers, explosões ou outros jogadores destruam suas construções).
  * `Shift + Clique` permite forçar o carregamento da chunk (para manter fornalhas e máquinas industriais funcionando mesmo longe).

### 3.2 Comunicação por Voz em Tempo Real
* **Simple Voice Chat**:
  * Já instalado no modpack (`Simple Voice Chat`).
  * Para servidores multijogador, certifique-se de que a porta **UDP 24454** esteja aberta e encaminhada no firewall/roteador do servidor para que a voz posicional funcione perfeitamente.

### 3.3 Monitoramento de Lag em Tempo Real (Spark)
* O mod **spark** já está instalado no modpack!
* Se o servidor ou jogo começar a engasgar, você pode rodar:
  ```text
  /spark tps
  /spark health
  ```
* Para descobrir qual mod ou entidade específica está causando lag:
  ```text
  /spark profiler start
  ```
  Aguarde 60 segundos e rode:
  ```text
  /spark profiler stop
  ```
  O mod gerará um link online com gráficos detalhados indicando exatamente a linha de código ou entidade que está pesando no processador.

### 3.4 Parâmetros de Inicialização de Memória (JVM Flags)
Para um modpack com ~243 mods, configure no TLauncher ou no script do servidor:
* **Memória**: Mínimo **8 GB**, Recomendado **10 GB** (ex: `-Xms8G -Xmx10G`).
* **Garbage Collector Recomendado (G1GC otimizado)**:
  ```text
  -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1ReservePercent=15 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1
  ```

---

## 4. Estratégia Definitiva de Camadas (Layers) de Resource Packs

No Minecraft, a ordem do arquivo options.txt funciona de **baixo para cima**:
* Itens no **início** da lista (anilla) têm **menor prioridade** (são a base).
* Itens no **final** da lista têm **maior prioridade** (sobrescrevem os anteriores).

A ordem ideal configurada para evitar texturas quebradas e modelos 3D anulados foi:

`
[TOPO - Maior Prioridade: Sobrescreve tudo abaixo]
 21. FreshAnimations (Animações de mobs via EMF/ETF - precisa estar acima dos mobs)
 20. Better_Cats (Modelos de gatos)
 19. BetterDragonRemastered (Modelo do Ender Dragon)
 18. Better Beds (Camas 3D)
 17. Better Lanterns (Lanternas 3D)
 16. Farm 3D (Plantações 3D)
 15. Better 3D Blocks (Blocos de construção 3D)
 14. Enchanting Reimagined (Addon: Mesa de encantamento)

---

## 4. Estratégia Definitiva de Camadas (Layers) de Resource Packs

No Minecraft, a ordem do arquivo options.txt funciona de **baixo para cima**:
* Itens no **início** da lista ( anilla) têm **menor prioridade** (são a base).
* Itens no **final** da lista têm **maior prioridade** (sobrescrevem os anteriores).

A ordem ideal configurada para evitar texturas quebradas e modelos 3D anulados foi:

`
[TOPO - Maior Prioridade: Sobrescreve tudo abaixo]
 21. FreshAnimations (Animações de mobs via EMF/ETF - precisa estar acima dos mobs)
 20. Better_Cats (Modelos de gatos)
 19. BetterDragonRemastered (Modelo do Ender Dragon)
 18. Better Beds (Camas 3D)
 17. Better Lanterns (Lanternas 3D)
 16. Farm 3D (Plantações 3D)
 15. Better 3D Blocks (Blocos de construção 3D)
 14. Enchanting Reimagined (Addon: Mesa de encantamento)
 13. Furnaces Reimagined (Addon: Fornalhas)
 12. Torches Reimagined (Addon: Tochas 3D)
 11. Chests Reimagined (Addon: Baús)
 10. Reimagined Base (Textura base geral do mundo)
  9. Dramatic Skys (Céu e atmosfera)
  8 a 0. Recursos nativos de Mods e Vanilla (Base de tudo)
[BASE - Menor Prioridade]
`

---

## 5. Recurso Interativo na GUI: Arrastar para Enviar (Sync Pack ZIP)

Adicionamos na interface gráfica principal um card interativo com suporte a **Drag-and-Drop nativo do Windows** e **Área de Transferência (Clipboard)**:

### Como Usar:
1. **Arrastar e Soltar (Drag & Drop)**:
   * Clique com o botão esquerdo sobre o card **"Arrastar para Enviar / Compartilhar Modpack"** e **arraste o cursor para fora** da janela (para uma pasta do Windows Explorer, Área de Trabalho, Discord, Telegram ou WhatsApp).
   * O Windows transferirá o arquivo `.zip` nativamente!
2. **Copiar com um Clique (Ctrl + V)**:
   * Clique no botão **"📋 Copiar ZIP (Ctrl+V)"** (ou simplesmente dê um clique no card).
   * O arquivo `.zip` é colocado na Área de Transferência como um arquivo real (`CF_HDROP`). Basta ir no Discord ou em qualquer pasta e apertar **Ctrl + V**!
3. **O que vem dentro do ZIP**:
   * `TLauncherAdditional.json` (com todos os mods oficiais catalogados)
   * A pasta `config/` inteira (com as otimizações de inventário, JEI, ModernFix, etc.)
   * O arquivo `options.txt` (com as camadas de Resource Packs corrigidas)
   * Pastas `defaultconfigs/` e `kubejs/` (se existirem).
   * Compactado em nível leve em **poucos milissegundos**, pronto para sincronizar qualquer amigo sem precisar enviar gigabytes de `.jar`!
