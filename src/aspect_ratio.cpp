// Complete Edition aspect constant identified by LARecomp's graphics hooks:
// https://github.com/mzzvxm/LARecomp/blob/main/src/mc_engine/hooks/graphics.cpp
// The four loads at 82233EB4, 82214BB8, 822E5E68 and 8223E5E0 in our generated
// code all read 8201E7EC. Patch that data once, before the guest thread resumes.
#include "generated/default/mcla_init.h"
#include <bit>
#include <atomic>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <rex/ui/window.h>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif
#include <rex/cvar.h>
#include <rex/logging.h>
#include <rex/runtime.h>
#include <rex/system/xmemory.h>

REXCVAR_DEFINE_STRING(mcla_aspect_ratio, "auto", "MCLA",
    "Display aspect: auto (monitor in fullscreen, window otherwise), 16:9 or 43:18. Restart required.")
    .allowed({"auto", "16:9", "43:18"})
    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);

REXCVAR_DEFINE_BOOL(mcla_hud_aspect, true, "MCLA",
    "Keep the HUD in a centered 16:9 safe area on an ultrawide display");

REXCVAR_DEFINE_BOOL(mcla_hud_edges, true, "MCLA",
    "Anchor the proportional minimap and speedometer to ultrawide screen edges");

REXCVAR_DEFINE_BOOL(mcla_gps_full_width, true, "MCLA",
    "Experimental: draw GPS movies without the driving HUD safe-area transform");

REXCVAR_DEFINE_BOOL(mcla_world_icon_aspect, true, "MCLA",
    "Experimental: keep world-marker movies outside the HUD safe-area compression");

REXCVAR_DEFINE_BOOL(mcla_panel_aspect, true, "MCLA",
    "Experimental: keep native pause panels outside the HUD safe-area compression");

REXCVAR_DEFINE_BOOL(mcla_phone_aspect, true, "MCLA",
    "Experimental: keep the Sidekick movie outside the HUD safe-area compression");

REXCVAR_DEFINE_BOOL(mcla_garage_aspect, true, "MCLA",
    "Experimental: preserve garage movie proportions in ultrawide");

REXCVAR_DEFINE_BOOL(mcla_gps_icon_aspect, true, "MCLA",
    "Experimental: render the GPS native icon batch without HUD compression");


namespace {
bool g_wide = false;  // Set before the guest thread starts.
double g_hud_correction = 1.0;  // (16/9) / the selected presentation aspect.
thread_local bool g_ui_phase = false;
thread_local uint32_t g_adjusted_device = 0;
thread_local float g_original_scale = 0, g_original_offset = 0;
thread_local float g_hud_anchor_x = 0;
std::atomic<uint32_t> g_speedometer_context{0};
thread_local unsigned g_gps_draw_depth = 0;

uint32_t ReadWord(const uint8_t* base, uint32_t address) {
  return (uint32_t(base[address]) << 24) | (uint32_t(base[address + 1]) << 16) |
         (uint32_t(base[address + 2]) << 8) | base[address + 3];
}
void WriteWord(uint8_t* base, uint32_t address, uint32_t value) {
  for (int i = 0; i < 4; ++i) base[address + i] = uint8_t(value >> (24 - 8 * i));
}
float ReadFloat(const uint8_t* base, uint32_t address) {
  return std::bit_cast<float>(ReadWord(base, address));
}
void WriteFloat(uint8_t* base, uint32_t address, float value) {
  WriteWord(base, address, std::bit_cast<uint32_t>(value));
}
void DirtyViewport(uint8_t* base, uint32_t device) {
  // sub_824162D8 marks X scale / offset dirty with these bits in device+16.
  WriteWord(base, device + 20, ReadWord(base, device + 20) | 0x06000000u);
}
void RestoreHudViewport(uint8_t* base) {
  if (!g_adjusted_device) return;
  WriteFloat(base, g_adjusted_device + 10504, g_original_scale);
  WriteFloat(base, g_adjusted_device + 10508, g_original_offset);
  DirtyViewport(base, g_adjusted_device);
  g_adjusted_device = 0;
}
void ApplyHudViewport(uint8_t* base, uint32_t device) {
  if (!g_wide || !g_ui_phase || g_gps_draw_depth ||
      !REXCVAR_GET(mcla_hud_aspect) || device < 0x10000) return;
  // Affect the final UI, never its smaller minimap/gauge render textures.
  const float width = ReadFloat(base, device + 12656);
  const float x = ReadFloat(base, device + 12648);
  if (std::abs(width - 1280.0f) > 0.1f || std::abs(x) > 0.1f) return;
  const float correction = float(g_hud_correction);
  g_original_scale = ReadFloat(base, device + 10504);
  g_original_offset = ReadFloat(base, device + 10508);
  g_adjusted_device = device;
  WriteFloat(base, device + 10504, g_original_scale * correction);
  WriteFloat(base, device + 10508,
             640.0f + (g_original_offset - 640.0f) * correction + g_hud_anchor_x);
  DirtyViewport(base, device);
  static thread_local bool logged = false;
  if (!logged) {
    REXLOG_INFO("ultrawide HUD: centered 16:9 viewport correction applied");
    logged = true;
  }
}

// HUDMAPMOVIE owns the complete minimap (including its symbols). The gauge
// movie is private to the HUD; its script context is passed to mcSpeedometer's
// constructor, rather than being registered with the UI manager.
int HudMovieSide(const uint8_t* base, uint32_t movie) {
  if (!g_wide || !g_ui_phase || !REXCVAR_GET(mcla_hud_aspect) ||
      !REXCVAR_GET(mcla_hud_edges) || movie < 0x10000) return 0;
  const uint32_t context = ReadWord(base, movie + 56);
  if (context && context == g_speedometer_context.load(std::memory_order_relaxed)) return 1;
  const uint32_t manager = ReadWord(base, 0x8286D804);
  if (manager < 0x10000) return 0;
  const uint32_t buckets = ReadWord(base, manager + 60);
  const uint32_t count = ReadWord(base, manager + 64) >> 16;
  if (buckets < 0x10000 || count > 256) return 0;
  for (uint32_t i = 0; i < count; ++i) {
    uint32_t node = ReadWord(base, buckets + i * 4);
    for (uint32_t guard = 0; node >= 0x10000 && node != 0xFFFFFFFF && guard < 256;
         ++guard, node = ReadWord(base, node + 12)) {
      const uint32_t holder = ReadWord(base, node + 8);
      if (holder < 0x10000 || ReadWord(base, holder) != movie) continue;
      const uint32_t name = ReadWord(base, node);
      return name >= 0x10000 &&
          !std::strcmp(reinterpret_cast<const char*>(base + name), "HUDMAPMOVIE") ? -1 : 0;
    }
  }
  return 0;
}

const char* GpsMovieName(const uint8_t* base, uint32_t movie) {
  if (!g_wide || !REXCVAR_GET(mcla_gps_full_width) || movie < 0x10000) return nullptr;
  const uint32_t manager = ReadWord(base, 0x8286D804);
  if (manager < 0x10000) return nullptr;
  const uint32_t buckets = ReadWord(base, manager + 60);
  const uint32_t count = ReadWord(base, manager + 64) >> 16;
  if (buckets < 0x10000 || count > 256) return nullptr;
  for (uint32_t i = 0; i < count; ++i) {
    uint32_t node = ReadWord(base, buckets + i * 4);
    for (unsigned guard = 0; node >= 0x10000 && node != 0xFFFFFFFF && guard < 256;
         ++guard, node = ReadWord(base, node + 12)) {
      const uint32_t holder = ReadWord(base, node + 8);
      if (holder < 0x10000 || ReadWord(base, holder) != movie) continue;
      const uint32_t name_address = ReadWord(base, node);
      if (name_address < 0x10000) return nullptr;
      const char* name = reinterpret_cast<const char*>(base + name_address);
      const bool gps = !std::strcmp(name, "NAVSYS2DMOVIE") || !std::strcmp(name, "NAVSYSMOVIE") ||
          !std::strcmp(name, "NAVSYSTARGETICONMOVIE");
      const bool world_icon = REXCVAR_GET(mcla_world_icon_aspect) &&
          (!std::strcmp(name, "3DICONSMOVIE0") || !std::strcmp(name, "3DICONSMOVIE1") ||
           !std::strcmp(name, "3DICONSMOVIE2"));
      const bool panel = REXCVAR_GET(mcla_panel_aspect) &&
          !std::strcmp(name, "PAUSEMOVIE");
      const bool phone = REXCVAR_GET(mcla_phone_aspect) && !std::strcmp(name, "SIDEKICKMOVIE");
      const bool garage = REXCVAR_GET(mcla_garage_aspect) && !std::strcmp(name, "GARAGEMOVIE");
      return gps || world_icon || panel || phone || garage ? name : nullptr;
    }
  }
  return nullptr;
}
}

// Use the common dispatcher: GPS can select the 82720478 render path as well
// as 82720908 / 82720C58. Keep the whole selected call, including viewport
// changes and scissor emission, outside the driving HUD safe-area transform.
extern "C" REX_FUNC(sub_82721258) {
  const char* name = GpsMovieName(base, ctx.r3.u32);
  if (name) {
    const bool was_compressed = g_adjusted_device != 0;
    RestoreHudViewport(base);
    ++g_gps_draw_depth;
    static thread_local unsigned count = 0;
    if (count++ < 12) {
      REXLOG_INFO("GPS proportion test: {} render mode {} ui={}", name, ctx.r4.u32, g_ui_phase);
    }
    static thread_local unsigned world_count = 0;
    if (!std::strncmp(name, "3DICONS", 7) && world_count++ < 12) {
      REXLOG_INFO("World icon aspect: {} mode {} ui={} safe_area={}",
                  name, ctx.r4.u32, g_ui_phase, was_compressed);
    }
  }
  __imp__sub_82721258(ctx, base);
  if (name) {
    RestoreHudViewport(base);
    --g_gps_draw_depth;
    ApplyHudViewport(base, ReadWord(base, 0x82839254));
  }
}

extern "C" REX_FUNC(sub_82241EA0) {
  const uint32_t context = ctx.r4.u32;
  __imp__sub_82241EA0(ctx, base);
  g_speedometer_context.store(context, std::memory_order_relaxed);
  REXLOG_INFO("ultrawide HUD: speedometer context {:08X}", context);
}

template <typename Draw>
void DrawAnchoredHudMovie(PPCContext& ctx, uint8_t* base, Draw draw) {
  const int side = HudMovieSide(base, ctx.r3.u32);
  const float saved_anchor = g_hud_anchor_x;
  if (side) {
    RestoreHudViewport(base);
    // Move the proportional HUD from its 16:9 safe area to the selected
    // display edges. At 3440x1440 this remains exactly the validated shift.
    g_hud_anchor_x = side * (640.0f * (1.0f - float(g_hud_correction)));
    ApplyHudViewport(base, ReadWord(base, 0x82839254));
    static thread_local unsigned logged = 0;
    const unsigned bit = side < 0 ? 1u : 2u;
    if (!(logged & bit)) {
      REXLOG_INFO("ultrawide HUD: {} anchored to {} edge, viewport shift {:.3f}",
                  side < 0 ? "minimap" : "speedometer", side < 0 ? "left" : "right",
                  g_hud_anchor_x);
      logged |= bit;
    }
  }
  draw(ctx, base);
  if (side) {
    RestoreHudViewport(base);
    g_hud_anchor_x = saved_anchor;
    ApplyHudViewport(base, ReadWord(base, 0x82839254));
  }
}

extern "C" REX_FUNC(sub_82720908) {
  DrawAnchoredHudMovie(ctx, base, __imp__sub_82720908);
}

extern "C" REX_FUNC(sub_82720C58) {
  DrawAnchoredHudMovie(ctx, base, __imp__sub_82720C58);
}

// Called only on the game's rendering thread, at existing render markers.
void MclaAspectPhase(uint8_t* base, uint32_t phase) {
  RestoreHudViewport(base);
  g_ui_phase = phase == 0x20000000;
  ApplyHudViewport(base, ReadWord(base, 0x82839254));
}

// XDK floating-point SetViewport: its unmodified logical viewport remains in
// device+12648; only the GPU X transform is corrected, after the original
// function has computed it. Later 3D passes restore the original transform.
extern "C" REX_FUNC(sub_824162D8) {
  RestoreHudViewport(base);
  const uint32_t device = ctx.r3.u32;
  __imp__sub_824162D8(ctx, base);
  ApplyHudViewport(base, device);
}

// The pause / GPS UI begins by copying the tonemapped scene into its tiled
// MSAA target (82227428 -> 822E5358 -> 823083F8). That copy must cover the
// entire frame. Squashing it leaves uncleared EDRAM visible at both sides.
extern "C" REX_FUNC(sub_822E5358) {
  RestoreHudViewport(base);
  const bool was_ui = g_ui_phase;
  g_ui_phase = false;
  __imp__sub_822E5358(ctx, base);
  g_ui_phase = was_ui;
  ApplyHudViewport(base, ReadWord(base, 0x82839254));
  static thread_local bool logged = false;
  if (g_wide && was_ui && !logged) {
    REXLOG_INFO("ultrawide pause: scene copy kept at full viewport width");
    logged = true;
  }
}

// XDK scissor emitter, after viewport/scissor intersection and before per-tile
// clipping. Match the UI's X transform so Flash text and ACCEPT aren't clipped
// at their old 16:9 coordinates. The original logical rectangle stays intact.
extern "C" REX_FUNC(sub_82413660) {
  if (g_adjusted_device && ctx.r3.u32 == g_adjusted_device && g_ui_phase) {
    const double correction = g_hud_correction;
    const double left = 640.0 + (ctx.r4.s32 - 640.0) * correction + g_hud_anchor_x;
    const double right = 640.0 + (ctx.r6.s32 - 640.0) * correction + g_hud_anchor_x;
    // The left anchor can produce -0.000002 from float rounding: floor gives
    // -1, which the XDK emitter packs as unsigned 14-bit 16383. Keep both
    // ends inside this 1280-wide viewport and snap subpixel rounding noise.
    ctx.r4.s64 = std::clamp(int32_t(std::floor(left + 0.0001)), 0, 1280);
    ctx.r6.s64 = std::clamp(int32_t(std::ceil(right - 0.0001)), 0, 1280);
    static thread_local bool logged = false;
    if (!logged) {
      REXLOG_INFO("ultrawide UI: scissor follows the corrected viewport");
      logged = true;
    }
  }
  __imp__sub_82413660(ctx, base);
}

namespace {
struct DisplaySize {
  uint32_t width = 0, height = 0;
  const char* source = "unavailable";
};

DisplaySize DetectAspectDisplay(rex::ui::Window* window) {
  const bool fullscreen = rex::cvar::GetFlagByName("fullscreen") == "true";
#ifdef _WIN32
  HWND handle = window ? static_cast<HWND>(window->GetNativeWindowHandle()) : nullptr;
  // Client pixels exclude borders and the title bar. DPI scaling affects
  // both axes equally, so this ratio also works on a scaled desktop.
  if (!fullscreen && handle) {
    RECT client{};
    if (GetClientRect(handle, &client) && client.right > 0 && client.bottom > 0) {
      return {uint32_t(client.right), uint32_t(client.bottom), "window client"};
    }
  }
  const HMONITOR monitor = handle ? MonitorFromWindow(handle, MONITOR_DEFAULTTONEAREST)
      : MonitorFromPoint(POINT{0, 0}, MONITOR_DEFAULTTOPRIMARY);
  MONITORINFOEXW info{};
  info.cbSize = sizeof(info);
  if (GetMonitorInfoW(monitor, &info)) {
    // Query the monitor's current mode, rather than its DPI-virtualized
    // desktop coordinates or the desktop bounding box across all monitors.
    DEVMODEW mode{};
    mode.dmSize = sizeof(mode);
    if (EnumDisplaySettingsW(info.szDevice, ENUM_CURRENT_SETTINGS, &mode) &&
        mode.dmPelsWidth && mode.dmPelsHeight) {
      return {mode.dmPelsWidth, mode.dmPelsHeight, "window monitor"};
    }
    return {uint32_t(info.rcMonitor.right - info.rcMonitor.left),
            uint32_t(info.rcMonitor.bottom - info.rcMonitor.top), "monitor bounds"};
  }
#endif
  if (window && window->GetActualPhysicalWidth() && window->GetActualPhysicalHeight()) {
    return {window->GetActualPhysicalWidth(), window->GetActualPhysicalHeight(), "window surface"};
  }
  return {};
}
}  // namespace

void MclaApplyAspectRatio(rex::ui::Window* window) {
  constexpr uint32_t address = 0x8201E7EC;
  auto* runtime = rex::Runtime::instance();
  auto* memory = runtime ? runtime->memory() : nullptr;
  if (!memory) return;
  auto* heap = memory->LookupHeap(address);
  auto* data = memory->TranslateVirtual<uint8_t*>(address);
  if (!heap || !data) return;
  const uint32_t original = ReadWord(data, 0);
  const std::string selection = REXCVAR_GET(mcla_aspect_ratio);
  DisplaySize detected{};
  uint32_t guest_width = selection == "43:18" ? 1720 : 1280;
  constexpr uint32_t guest_height = 720;
  if (selection == "auto") {
    detected = DetectAspectDisplay(window);
    if (detected.width && detected.height) {
      // Keep the validated 720-line guest mode: internal render resolution
      // and FSR quality remain independent. The kernel's video-mode width
      // field accepts at most 4095. Narrow displays retain 16:9 letterboxing.
      const double ratio = double(detected.width) / detected.height;
      guest_width = uint32_t(std::clamp(std::lround(ratio * guest_height), 1280L, 4095L));
    } else {
      REXLOG_WARN("automatic aspect: no valid display size; using 16:9");
    }
  }
  double ratio = double(guest_width) / guest_height;
  const uint32_t bits = std::bit_cast<uint32_t>(float(ratio));
  if (original != 0x3FE38E39u) {
    REXLOG_ERROR("aspect ratio: unexpected game constant {:08X}; keeping 16:9", original);
    guest_width = 1280;
    ratio = 16.0 / 9.0;
  } else if (bits != original) {
    uint32_t old_protection = 0;
    if (!heap->Protect(address, 4, rex::memory::kMemoryProtectRead |
                                    rex::memory::kMemoryProtectWrite, &old_protection)) {
      REXLOG_ERROR("aspect ratio: could not write the game constant; keeping 16:9");
      guest_width = 1280;
      ratio = 16.0 / 9.0;
    } else {
      WriteWord(data, 0, bits);
      if (!heap->Protect(address, 4, old_protection)) {
        REXLOG_WARN("aspect ratio: could not restore data page protection");
      }
    }
  }
  g_wide = guest_width > 1280;
  g_hud_correction = 1280.0 / guest_width;
  // Do not replace the saved selection with the detected ratio. AUTO must
  // detect the current display again on every launch (including menu restart).
  rex::cvar::SetFlagFromCommandLine("video_mode_width", std::to_string(guest_width));
  rex::cvar::SetFlagFromCommandLine("video_mode_height", "720");
  rex::cvar::SetFlagFromCommandLine("present_letterbox", "true");
  REXLOG_INFO("aspect ratio: selection={} detected={}x{} source={} guest={}x{} ratio={:.6f} HUD={:.6f}",
              selection, detected.width, detected.height, detected.source,
              guest_width, guest_height, ratio, g_hud_correction);
}


// mcHudMapLocal builds symbol transforms on the game thread and renders the
// queued instances later, outside the registered GPS movie dispatcher. Mode
// 0 belongs to the minimap, 1 to GPS, and 2 to the overhead map. Only bypass
// the driving HUD transform for the GPS symbol batch; its positions already
// use the widescreen map camera. Keep the road/background and panel passes.
extern "C" REX_FUNC(sub_82236558) {
  const uint32_t owner = ctx.r3.u32;
  const bool gps = g_wide && REXCVAR_GET(mcla_gps_icon_aspect) &&
      owner >= 0x10000 && ReadWord(base, owner + 456) == 1;
  if (gps) {
    static thread_local bool logged = false;
    if (!logged) {
      REXLOG_INFO("GPS native symbols: bypass HUD compression, ui={} adjusted={}",
                  g_ui_phase, g_adjusted_device != 0);
      logged = true;
    }
    RestoreHudViewport(base);
    ++g_gps_draw_depth;
  }
  __imp__sub_82236558(ctx, base);
  if (gps) {
    RestoreHudViewport(base);
    --g_gps_draw_depth;
    ApplyHudViewport(base, ReadWord(base, 0x82839254));
  }
}



// mcUIClass has separate models for navsys_cursor and navsys_cursor_BG.
// The render interface uses this+4, hence +68 selects the foreground model
// (object+72) at 822278D0. The earlier +72 call selects its background.
// Draw the movable ring with the GPS viewport, matching both the size and
// screen position of the native icon batch. Keep its world matrix untouched.
extern "C" REX_FUNC(sub_82723940) {
  const bool cursor = g_wide && REXCVAR_GET(mcla_gps_icon_aspect) &&
      ctx.lr == 0x822278D4;
  if (cursor) {
    static thread_local bool logged = false;
    if (!logged) {
      REXLOG_INFO("GPS foreground cursor: original world matrix, ui={} adjusted={}",
                  g_ui_phase, g_adjusted_device != 0);
      logged = true;
    }
    RestoreHudViewport(base);
    ++g_gps_draw_depth;
  }
  __imp__sub_82723940(ctx, base);
  if (cursor) {
    RestoreHudViewport(base);
    --g_gps_draw_depth;
    ApplyHudViewport(base, ReadWord(base, 0x82839254));
  }
}
