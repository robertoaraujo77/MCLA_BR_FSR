// Generated from localization/pt-BR/host-menu-texts.json. UTF-8 input for the Flash text API.
#pragma once
inline std::string MclaLocalizeMenuText(std::string text) {
  if (!REXCVAR_GET(mcla_ptbr)) return text;
  struct Pair { const char* en; const char* pt; };
  static const Pair pairs[] = {
    {"LOADING", "CARREGANDO"},
    {"SAVE GAME", "SALVAR JOGO"},
    {"YES", "SIM"},
    {"NO", "N\303\203O"},
    {"ON", "LIGADO"},
    {"OFF", "DESLIGADO"},
    {"DISPLAY", "V\303\215DEO"},
    {"PERFORMANCE", "DESEMPENHO"},
    {"CONTROLS", "CONTROLES"},
    {"FPS TARGET", "LIMITE DE FPS"},
    {"HUD UPDATES", "ATUALIZA\303\207\303\203O DO HUD"},
    {"UNCAPPED", "SEM LIMITE"},
    {"EVERY FRAME", "A CADA QUADRO"},
    {"VSYNC", "VSYNC"},
    {"FULLSCREEN", "TELA CHEIA"},
    {"RESOLUTION", "RESOLU\303\207\303\203O"},
    {"ASPECT RATIO", "PROPOR\303\207\303\203O"},
    {"GRAPHICS API", "API GR\303\201FICA"},
    {"DISPLAY GAMMA", "GAMA DA TELA"},
    {"PEAK BRIGHTNESS", "BRILHO M\303\201XIMO"},
    {"PAPER WHITE", "BRANCO DE REFER\303\212NCIA"},
    {"HIGHLIGHTS", "REALCES"},
    {"MOTION BLUR", "DESFOQUE DE MOVIMENTO"},
    {"DEPTH OF FIELD", "PROFUNDIDADE DE CAMPO"},
    {"SINGLE TILE RENDERING", "BLOCO \303\232NICO"},
    {"GPU WAIT YIELD", "ESPERA DA GPU"},
    {"SHADOWS", "SOMBRAS"},
    {"FOLIAGE SHADOWS", "SOMBRAS DA VEGETA\303\207\303\203O"},
    {"CITY DETAIL DISTANCE", "DETALHE DA CIDADE"},
    {"TRAFFIC DETAIL DISTANCE", "DETALHE DO TR\303\201FEGO"},
    {"TRAFFIC DISTANCE", "DIST\303\202NCIA DO TR\303\201FEGO"},
    {"PEDESTRIANS", "PEDESTRES"},
    {"PARKED CARS", "CARROS PARADOS"},
    {"RACE SHADOWS", "SOMBRAS EM CORRIDA"},
    {"SIMPLE CAR SHADOWS", "SOMBRAS SIMPLES"},
    {"DISTANT TREES", "\303\201RVORES DISTANTES"},
    {"FULLSCREEN BLUR", "DESFOQUE DE TELA"},
    {"ANTI ALIASING", "ANTISSERRILHADO"},
    {"FSR MODE", "MODO FSR"},
    {"FRAME GENERATION", "GERA\303\207\303\203O DE QUADROS"},
    {"FSR SHARPNESS", "NITIDEZ DO FSR"},
    {"BUTTON PROMPTS", "\303\215CONES DOS BOT\303\225ES"},
    {"INTRO", "INTRODU\303\207\303\203O"},
    {"HIDE MOUSE POINTER", "OCULTAR CURSOR"},
    {"RESTART GAME", "REINICIAR JOGO"},
    {"QUIT GAME", "SAIR DO JOGO"},
    {"NEXT START", "REINICIAR"},
    {"RESTART NEEDED", "REINICIE"},
    {"UNAVAILABLE", "INDISPON\303\215VEL"},
    {"NOT AVAILABLE", "INDISPON\303\215VEL"},
    {"DX12 ONLY", "SOMENTE DX12"},
    {"NATIVE (720P)", "NATIVO (720P)"},
    {"AUTO", "AUTO"},
    {"NORMAL", "NORMAL"},
    {"FAST", "R\303\201PIDA"},
    {"SKIP (NO LOGO)", "PULAR (SEM LOGO)"},
    {"PC MONITOR", "MONITOR"},
    {"BRIGHT", "BRILHANTE"},
    {"BRIGHTER", "MAIS BRILHANTE"},
    {"BRIGHTEST", "BRILHO INTENSO"},
    {"NATIVE AA", "AA NATIVO"},
    {"QUALITY", "QUALIDADE"},
    {"BALANCED", "EQUILIBRADO"},
    {"NONE", "NENHUMA"},
    {"AUTOMATIC", "AUTOM\303\201TICO"},
    {"PRESS AGAIN", "PRESSIONE NOVAMENTE"},
  };
  auto exact = [&](const std::string& value) {
    for (const auto& pair : pairs) if (value == pair.en) return std::string(pair.pt);
    return value;
  };
  const auto translated = exact(text);
  if (translated != text) return translated;
  const auto bracket = text.find(" (");
  if (bracket != std::string::npos) {
    std::string result = exact(text.substr(0, bracket));
    size_t pos = bracket;
    while (pos < text.size()) {
      const auto end = text.find(')', pos);
      if (end == std::string::npos) return result + text.substr(pos);
      result += " (" + exact(text.substr(pos + 2, end - pos - 2)) + ")";
      pos = end + 1;
      if (pos < text.size() && text.substr(pos, 2) != " (") return result + text.substr(pos);
    }
    return result;
  }
  const auto rate = text.find(" PER SECOND");
  if (rate != std::string::npos) return text.substr(0, rate) + " POR SEGUNDO";
  return text;
}
