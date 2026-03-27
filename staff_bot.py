"""
╔══════════════════════════════════════════════════════════════════╗
  ███╗   ██╗██╗ ██████╗ ██╗  ██╗████████╗███╗   ███╗ ██████╗
  ████╗  ██║██║██╔════╝ ██║  ██║╚══██╔══╝████╗ ████║██╔════╝
  ██╔██╗ ██║██║██║  ███╗███████║   ██║   ██╔████╔██║██║
  ██║╚██╗██║██║██║   ██║██╔══██║   ██║   ██║╚██╔╝██║██║
  ██║ ╚████║██║╚██████╔╝██║  ██║   ██║   ██║ ╚═╝ ██║╚██████╗
  ╚═╝  ╚═══╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚═╝ ╚═════╝
         Bot de Staff — NightMc Network v3.1
  Token  →  STAFF_TOKEN en Railway / hardcode para testing
  Prefijo → st!
╚══════════════════════════════════════════════════════════════════╝
"""
import discord
from discord import ui
from discord.ext import commands, tasks
import asyncio
import datetime
import json
import os
import re
import difflib

TOKEN = os.getenv("STAFF_TOKEN", "")

# ╔═══════════════════════════════════════════════════════════════╗
#   ⚙️  CONFIGURACIÓN
# ╚═══════════════════════════════════════════════════════════════╝
CANAL_STRIKES      = "🔺│strikes"
CAT_APPEAL         = "🔺 STRIKE APPEALS"
LOGS_CANAL         = "all-logs"
LOGS_TICKETS       = "🎫│logs-tickets"
CANAL_VALORACIONES = "🎫│valoraciones"
CANAL_INACTIVIDAD  = "📬│inactividad"
CANAL_REUNIONES    = "💼│reuniones"
CANAL_BANS         = "🚫│bans"
CANAL_PUNTOS       = "🔥│puntos"
CANAL_RACHAS       = "🏅│rachas"          # ← NUEVO: canal de rachas

SANCIONES_FILE    = "sanciones_data.json"
NOTAS_FILE        = "notas_data.json"
PUNTOS_FILE       = "puntos_data.json"
SOTW_FILE         = "sotw_data.json"
BANS_CACHE_FILE   = "bans_cache.json"
RACHAS_FILE       = "rachas_data.json"   # ← NUEVO

# Cache en memoria: {canal_id: [(autor_id, texto, timestamp), ...]}
_bans_recientes: dict[int, list] = {}

ROL_HEAD   = "Head staff"
ROL_HIGH   = "High Staff"
STAFF_TEAM = "Staff team"
ROL_SOTW   = "SOTW"
ROL_SOTM   = "SOTM"
ROLES_SUPERIORES = ["High Staff", "Head staff"]
ROLES_STAFF_ALL  = ["Low staff", "Medium Staff", "High Staff", "Head staff", "Staff team"]

WARNS_PARA_STRIKE   = 3
STRIKES_PARA_DEMOTE = 3

SEP    = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FOOTER = "© Powered by NightMC  ✦  Staff Team"

COLOR_BASE   = 0x2b2d31
COLOR_OK     = 0x57f287
COLOR_DANGER = 0xed4245
COLOR_WARN   = 0xfee75c
COLOR_BLUE   = 0x5865f2
COLOR_STRIKE = 0xff6b35
COLOR_GOLD   = 0xf1c40f
COLOR_PURPLE = 0x9b59b6   # ← Para rachas

BANNER_STAFF = "https://i.imgur.com/bWZ8WOz.png"

# ╔═══════════════════════════════════════════════════════════════╗
#   🤖  BOT
# ╚═══════════════════════════════════════════════════════════════╝
intents = discord.Intents.default()
intents.message_content = True
intents.members         = True

bot = commands.Bot(command_prefix="st!", intents=intents, help_command=None)

# ╔═══════════════════════════════════════════════════════════════╗
#   💾  PERSISTENCIA JSON
# ╚═══════════════════════════════════════════════════════════════╝
def _load(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _cargar_datos()      -> dict: return _load(SANCIONES_FILE)
def _guardar_datos(d):            _save(SANCIONES_FILE, d)
def _cargar_notas()      -> dict: return _load(NOTAS_FILE)
def _guardar_notas(d):            _save(NOTAS_FILE, d)
def _cargar_puntos()     -> dict: return _load(PUNTOS_FILE)
def _guardar_puntos(d):           _save(PUNTOS_FILE, d)
def _cargar_sotw()       -> dict: return _load(SOTW_FILE)
def _guardar_sotw(d):             _save(SOTW_FILE, d)
def _cargar_rachas()     -> dict: return _load(RACHAS_FILE)   # ← NUEVO
def _guardar_rachas(d):           _save(RACHAS_FILE, d)        # ← NUEVO

def _sumar_punto(uid: int, cantidad: float = 0.1):
    data = _cargar_puntos()
    key  = str(uid)
    if key not in data:
        data[key] = {"total": 0.0, "semana": 0.0, "evidencias": 0, "ultima_evidencia": 0}
    data[key]["total"]            = round(data[key]["total"]      + cantidad, 2)
    data[key]["semana"]           = round(data[key]["semana"]     + cantidad, 2)
    data[key]["evidencias"]       = data[key]["evidencias"] + 1
    data[key]["ultima_evidencia"] = datetime.datetime.now().timestamp()
    _guardar_puntos(data)
    return data[key]

def _get_staff_data(data: dict, uid: int) -> dict:
    key = str(uid)
    if key not in data:
        data[key] = {"warns": [], "strikes": []}
    return data[key]

# ╔═══════════════════════════════════════════════════════════════╗
#   🏅  SISTEMA DE RACHAS — HELPERS                    (NUEVO)
# ╚═══════════════════════════════════════════════════════════════╝
def _hoy() -> str:
    """Fecha de hoy en formato YYYY-MM-DD (UTC)."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")

def _ayer() -> str:
    """Fecha de ayer en formato YYYY-MM-DD (UTC)."""
    return (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

def _get_racha(data: dict, uid: int) -> dict:
    key = str(uid)
    if key not in data:
        data[key] = {"racha": 0, "max_racha": 0, "ultimo_dia": "", "total_dias": 0}
    r = data[key]
    r.setdefault("max_racha", 0)
    r.setdefault("total_dias", 0)
    return r

def _actualizar_racha(uid: int) -> dict:
    """
    Llama esto cuando el staff sube una evidencia válida.
    - Si ya contó hoy → no hace nada.
    - Si ayer contó → incrementa racha.
    - Si rompió → resetea a 1.
    Devuelve el dict de racha actualizado.
    """
    data = _cargar_rachas()
    r    = _get_racha(data, uid)
    hoy  = _hoy()

    if r["ultimo_dia"] == hoy:
        # Ya contó hoy, no duplicar
        return r

    if r["ultimo_dia"] == _ayer():
        r["racha"] += 1
    else:
        r["racha"] = 1

    r["ultimo_dia"] = hoy
    r["total_dias"] = r.get("total_dias", 0) + 1
    if r["racha"] > r["max_racha"]:
        r["max_racha"] = r["racha"]

    data[str(uid)] = r
    _guardar_rachas(data)
    return r

def _romper_racha(uid: int) -> int:
    """Resetea la racha de un usuario. Devuelve la racha que tenía."""
    data   = _cargar_rachas()
    r      = _get_racha(data, uid)
    tenia  = r["racha"]
    r["racha"] = 0
    data[str(uid)] = r
    _guardar_rachas(data)
    return tenia

def _emoji_racha(racha: int) -> str:
    if racha >= 30: return "🔱"
    if racha >= 14: return "💎"
    if racha >= 7:  return "🔥"
    if racha >= 3:  return "⚡"
    return "📅"

# ╔═══════════════════════════════════════════════════════════════╗
#   🛠️  HELPERS
# ╚═══════════════════════════════════════════════════════════════╝
def es_superior(m: discord.Member) -> bool:
    return any(r.name in ROLES_SUPERIORES for r in m.roles)

def es_head(m: discord.Member) -> bool:
    return any(r.name == ROL_HEAD for r in m.roles)

def es_staff(m: discord.Member) -> bool:
    return any(r.name in ROLES_STAFF_ALL for r in m.roles)

def _footer(e: discord.Embed, guild: discord.Guild) -> discord.Embed:
    e.set_footer(text=FOOTER, icon_url=guild.icon.url if guild.icon else None)
    return e

def _barras(warns: int, strikes: int):
    bw = "🟡" * warns   + "⬛" * (WARNS_PARA_STRIKE   - warns)
    bs = "🔴" * strikes + "⬛" * (STRIKES_PARA_DEMOTE - strikes)
    return bw, bs

def _now_ts() -> int:
    return int(datetime.datetime.now().timestamp())

def _fecha_str() -> str:
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

async def _log(guild: discord.Guild, embed: discord.Embed, canal_nombre: str = None):
    nombre = canal_nombre or LOGS_CANAL
    canal  = discord.utils.get(guild.text_channels, name=nombre)
    if canal:
        try: await canal.send(embed=embed)
        except discord.Forbidden: pass

async def _get_or_create_cat(guild: discord.Guild, nombre: str):
    cat = discord.utils.get(guild.categories, name=nombre)
    if not cat:
        try:
            cat = await guild.create_category(nombre, overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me:           discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            })
        except discord.Forbidden:
            return None
    return cat

def _owner_from_topic(canal) -> int:
    try:
        if canal.topic and "ownerid:" in canal.topic:
            return int(canal.topic.split("ownerid:")[1].split("|")[0].strip())
    except Exception:
        pass
    return 0

# ╔═══════════════════════════════════════════════════════════════╗
#   📋  SISTEMA DE SANCIONES
# ╚═══════════════════════════════════════════════════════════════╝
async def _registrar_sancion(guild, sancionado, autor, tipo, motivo):
    data        = _cargar_datos()
    sd          = _get_staff_data(data, sancionado.id)
    fecha       = _fecha_str()
    strike_auto = False

    if tipo == "warn":
        sd["warns"].append({"motivo": motivo, "por": autor.id, "fecha": fecha})
        if len(sd["warns"]) >= WARNS_PARA_STRIKE:
            sd["warns"] = []
            sd["strikes"].append({"motivo": "Strike automático — 3 warns acumulados",
                                   "por": bot.user.id, "fecha": fecha})
            strike_auto = True
            tipo = "strike"
    else:
        sd["strikes"].append({"motivo": motivo, "por": autor.id, "fecha": fecha})

    _guardar_datos(data)

    tw, ts = len(sd["warns"]), len(sd["strikes"])
    bw, bs = _barras(tw, ts)
    color  = COLOR_DANGER if tipo == "strike" else COLOR_WARN
    icono  = "💥" if tipo == "strike" else "⚠️"

    e = discord.Embed(color=color, timestamp=datetime.datetime.now())
    e.set_author(name="Sistema de Sanciones  ✦  NightMc Network",
                 icon_url=guild.icon.url if guild.icon else None)
    e.title = f"{icono}  {'Strike' if tipo == 'strike' else 'Warn'} Registrado — NightMc Staff"
    e.set_thumbnail(url=sancionado.display_avatar.url)
    e.description = (
        f"{SEP}\n**👤  Staff:** {sancionado.mention}\n"
        f"**👮  Aplicado por:** {autor.mention}\n"
        f"**📅  Fecha:** <t:{_now_ts()}:F>\n{SEP}"
    )
    e.add_field(name="📋  Motivo", value=f"> {motivo}", inline=False)
    if strike_auto:
        e.add_field(name="🔄  Strike automático",
                    value="> 3 warns acumulados → **+1 Strike**. Warns reseteados.", inline=False)
    e.add_field(name="\u200b", value="\u200b", inline=False)
    e.add_field(name=f"⚠️  Warns `{tw}/{WARNS_PARA_STRIKE}`",    value=bw, inline=True)
    e.add_field(name=f"💥  Strikes `{ts}/{STRIKES_PARA_DEMOTE}`", value=bs, inline=True)
    _footer(e, guild)

    planta = (f"**Staff:** {sancionado.mention}  "
              f"**Motivo:** {motivo}  "
              f"**Sanción:** {'Strike' if tipo == 'strike' else 'Warn'}  "
              f"**Total:** {tw}W · {ts}S  "
              f"**Fecha:** <t:{_now_ts()}:D>")

    canal_s = discord.utils.get(guild.text_channels, name=CANAL_STRIKES)
    if canal_s:
        await canal_s.send(content=planta, embed=e)

    if tw == 2 and tipo != "strike":
        rol_head = discord.utils.get(guild.roles, name=ROL_HEAD)
        av = discord.Embed(color=COLOR_WARN, timestamp=datetime.datetime.now())
        av.title = "⚠️  Aviso — 2 Warns Acumulados"
        av.description = (
            f"{sancionado.mention} acumuló **2 warns**.\n"
            f"> Un warn más = **strike automático**."
        )
        av.set_thumbnail(url=sancionado.display_avatar.url)
        _footer(av, guild)
        if canal_s:
            await canal_s.send(content=rol_head.mention if rol_head else "@Head staff", embed=av)

    if ts >= STRIKES_PARA_DEMOTE:
        rol_head = discord.utils.get(guild.roles, name=ROL_HEAD)
        kick_ok  = False
        try:
            await sancionado.kick(reason=f"3 strikes — {motivo}")
            kick_ok = True
        except Exception:
            pass
        al = discord.Embed(title="🚨  3 STRIKES — DEMOTE REQUERIDO",
                           color=COLOR_DANGER, timestamp=datetime.datetime.now())
        al.description = (
            f"{sancionado.mention} alcanzó **3 strikes**. Demote requerido.\n\n"
            f"{'✅  Expulsado automáticamente.' if kick_ok else '⚠️  No se pudo expulsar. Acción manual requerida.'}"
        )
        al.add_field(name="📋  Último motivo", value=f"```{motivo}```", inline=False)
        _footer(al, guild)
        if canal_s:
            await canal_s.send(
                content=f"{rol_head.mention if rol_head else '@Head staff'} — Revisión requerida.",
                embed=al)

    await _log(guild, e)
    return sd

# ── Autocompletes ──────────────────────────────────────────────────
async def _ac_tipo(interaction, current):
    return [discord.app_commands.Choice(name=t, value=t)
            for t in ["Warn", "Strike"] if current.lower() in t.lower()]

async def _ac_motivo(interaction, current):
    motivos = [
        "Inactividad sin justificar", "Mal comportamiento con usuarios",
        "Abuso de permisos", "Incumplimiento de normas de staff",
        "Filtración de información interna", "Falta de respeto a compañeros",
        "No seguir el protocolo de tickets", "Ausencia en reuniones de staff",
    ]
    return [discord.app_commands.Choice(name=m, value=m)
            for m in motivos if current.lower() in m.lower()][:25]

async def _ac_remover_staff(interaction, current):
    data = _cargar_datos()
    out  = []
    for uid, sd in data.items():
        if not sd.get("warns") and not sd.get("strikes"):
            continue
        m = interaction.guild.get_member(int(uid))
        if m and current.lower() in m.display_name.lower():
            out.append(discord.app_commands.Choice(
                name=f"{m.display_name}  ({len(sd['warns'])}W · {len(sd['strikes'])}S)",
                value=uid))
    return out[:25]

async def _ac_remover_sancion(interaction, current):
    staff_val = next((o["value"] for o in interaction.data.get("options", [])
                      if o["name"] == "staff"), None)
    if not staff_val:
        return [discord.app_commands.Choice(name="Primero selecciona un staff", value="none")]
    sd  = _cargar_datos().get(staff_val, {"warns": [], "strikes": []})
    out = []
    for i, w in enumerate(sd.get("warns", [])):
        lbl = f"⚠️ Warn {i+1} — {w['fecha']} — {w['motivo'][:40]}"
        if current.lower() in lbl.lower():
            out.append(discord.app_commands.Choice(name=lbl[:100], value=f"warn:{i}"))
    for i, s in enumerate(sd.get("strikes", [])):
        lbl = f"💥 Strike {i+1} — {s['fecha']} — {s['motivo'][:40]}"
        if current.lower() in lbl.lower():
            out.append(discord.app_commands.Choice(name=lbl[:100], value=f"strike:{i}"))
    return out[:25] or [discord.app_commands.Choice(name="Sin sanciones", value="none")]

async def _ac_razon_remover(interaction, current):
    razones = [
        "Error al registrar", "Sanción aplicada por error", "Apelación aceptada",
        "Decisión revisada por Head staff", "Sanción duplicada",
        "El miembro ya fue amonestado verbalmente",
    ]
    return [discord.app_commands.Choice(name=r, value=r)
            for r in razones if current.lower() in r.lower()][:25]

# ── Slash commands de sanciones ────────────────────────────────────
@bot.tree.command(name="sancion", description="Registra un Warn o Strike a un miembro del staff")
@discord.app_commands.describe(staff="Staff a sancionar", tipo="Warn o Strike", motivo="Motivo")
@discord.app_commands.autocomplete(tipo=_ac_tipo, motivo=_ac_motivo)
async def sancion_slash(interaction: discord.Interaction,
                        staff: discord.Member, tipo: str, motivo: str):
    if not es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo **High Staff** o superior.", ephemeral=True)
    if staff.bot:
        return await interaction.response.send_message("❌  No puedes sancionar bots.", ephemeral=True)
    if staff.id == interaction.user.id and not es_head(interaction.user):
        return await interaction.response.send_message("❌  No puedes sancionarte a ti mismo.", ephemeral=True)
    tipo_n = tipo.lower()
    if tipo_n not in ("warn", "strike"):
        return await interaction.response.send_message("❌  Tipo inválido. Usa **Warn** o **Strike**.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    sd     = await _registrar_sancion(interaction.guild, staff, interaction.user, tipo_n, motivo)
    bw, bs = _barras(len(sd["warns"]), len(sd["strikes"]))
    await interaction.followup.send(
        f"✅  **{tipo}** registrado para {staff.mention}.\n"
        f"⚠️  Warns: **{len(sd['warns'])}/{WARNS_PARA_STRIKE}** {bw}\n"
        f"💥  Strikes: **{len(sd['strikes'])}/{STRIKES_PARA_DEMOTE}** {bs}", ephemeral=True)

@bot.tree.command(name="historial", description="Muestra el historial de sanciones de un staff")
@discord.app_commands.describe(miembro="Staff a consultar")
async def historial_slash(interaction: discord.Interaction, miembro: discord.Member):
    if not es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo **High Staff** o superior.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    data   = _cargar_datos()
    sd     = _get_staff_data(data, miembro.id)
    tw, ts = len(sd["warns"]), len(sd["strikes"])
    bw, bs = _barras(tw, ts)

    e = discord.Embed(color=COLOR_BLUE, timestamp=datetime.datetime.now())
    e.set_author(name="Sistema de Sanciones  ✦  NightMc Network",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    e.title = f"📋  Historial — {miembro.display_name}"
    e.set_thumbnail(url=miembro.display_avatar.url)
    e.add_field(name=f"⚠️  Warns `{tw}/{WARNS_PARA_STRIKE}`",    value=bw, inline=True)
    e.add_field(name=f"💥  Strikes `{ts}/{STRIKES_PARA_DEMOTE}`", value=bs, inline=True)
    e.add_field(name="\u200b", value="\u200b", inline=False)
    if sd["warns"]:
        e.add_field(name="📄  Warns activos",
                    value="\n".join(f"`{i+1}.` {w['fecha']} — {w['motivo']}"
                                    for i, w in enumerate(sd["warns"])), inline=False)
    if sd["strikes"]:
        e.add_field(name="📄  Strikes activos",
                    value="\n".join(f"`{i+1}.` {s['fecha']} — {s['motivo']}"
                                    for i, s in enumerate(sd["strikes"])), inline=False)
    if not sd["warns"] and not sd["strikes"]:
        e.description = "✅  Sin sanciones registradas."
    _footer(e, interaction.guild)
    await interaction.followup.send(embed=e, ephemeral=True)

@bot.tree.command(name="remover", description="Remueve una sanción específica de un staff")
@discord.app_commands.describe(staff="Staff", sancion="Sanción a remover", razon="Razón")
@discord.app_commands.autocomplete(staff=_ac_remover_staff,
                                    sancion=_ac_remover_sancion,
                                    razon=_ac_razon_remover)
async def remover_slash(interaction: discord.Interaction, staff: str, sancion: str, razon: str):
    if not es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo **High Staff** o superior.", ephemeral=True)
    if sancion == "none":
        return await interaction.response.send_message("❌  Selecciona una sanción válida.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)

    data = _cargar_datos()
    sd   = data.get(staff, {"warns": [], "strikes": []})
    try:
        tipo, idx = sancion.split(":")
        idx = int(idx)
    except Exception:
        return await interaction.followup.send("❌  Sanción inválida.", ephemeral=True)

    lista = sd.get("warns" if tipo == "warn" else "strikes", [])
    if idx < 0 or idx >= len(lista):
        return await interaction.followup.send("❌  Esa sanción ya no existe.", ephemeral=True)

    removida    = lista.pop(idx)
    data[staff] = sd
    _guardar_datos(data)

    miembro  = interaction.guild.get_member(int(staff))
    nombre   = miembro.mention if miembro else f"<@{staff}>"
    tipo_str = "Warn" if tipo == "warn" else "Strike"
    tw, ts   = len(sd["warns"]), len(sd["strikes"])
    bw, bs   = _barras(tw, ts)

    e = discord.Embed(color=COLOR_OK, timestamp=datetime.datetime.now())
    e.set_author(name="Sistema de Sanciones  ✦  NightMc Network",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    e.title = f"🗑️  Sanción Removida — {tipo_str}"
    if miembro: e.set_thumbnail(url=miembro.display_avatar.url)
    e.description = (
        f"{SEP}\n**👤  Staff:** {nombre}\n"
        f"**👮  Removido por:** {interaction.user.mention}\n"
        f"**📅  Fecha:** <t:{_now_ts()}:F>\n{SEP}"
    )
    e.add_field(name=f"{'⚠️' if tipo == 'warn' else '💥'}  Sanción removida",
                value=f"> **{tipo_str}** — {removida.get('motivo', '—')}", inline=False)
    e.add_field(name="📋  Razón", value=f"> {razon}", inline=False)
    e.add_field(name="\u200b", value="\u200b", inline=False)
    e.add_field(name=f"⚠️  Warns `{tw}/{WARNS_PARA_STRIKE}`",    value=bw, inline=True)
    e.add_field(name=f"💥  Strikes `{ts}/{STRIKES_PARA_DEMOTE}`", value=bs, inline=True)
    _footer(e, interaction.guild)

    canal_s = discord.utils.get(interaction.guild.text_channels, name=CANAL_STRIKES)
    if canal_s: await canal_s.send(embed=e)
    await _log(interaction.guild, e)
    await interaction.followup.send(f"✅  {tipo_str} removido correctamente.", ephemeral=True)

# ── Limpiar historial ──────────────────────────────────────────────
class ConfirmarLimpiarView(ui.View):
    def __init__(self, staff: discord.Member, autor: discord.Member):
        super().__init__(timeout=30)
        self.staff = staff
        self.autor = autor

    @ui.button(label="Confirmar", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.autor.id:
            return await interaction.response.send_message("❌  Solo quien ejecutó el comando.", ephemeral=True)
        data = _cargar_datos()
        data[str(self.staff.id)] = {"warns": [], "strikes": []}
        _guardar_datos(data)
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(view=self)
        e = discord.Embed(color=COLOR_OK, timestamp=datetime.datetime.now())
        e.set_author(name="Sistema de Sanciones  ✦  NightMc Network",
                     icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        e.title = "🗑️  Historial Limpiado"
        e.description = (
            f"{SEP}\n**👤  Staff:** {self.staff.mention}\n"
            f"**👮  Limpiado por:** {interaction.user.mention}\n"
            f"**📅  Fecha:** <t:{_now_ts()}:F>\n{SEP}\n"
            f"> ✅  Todos los warns y strikes reseteados a 0."
        )
        _footer(e, interaction.guild)
        canal_s = discord.utils.get(interaction.guild.text_channels, name=CANAL_STRIKES)
        if canal_s: await canal_s.send(embed=e)
        await _log(interaction.guild, e)
        await interaction.followup.send(f"✅  Historial limpiado.", ephemeral=True)

    @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.autor.id:
            return await interaction.response.send_message("❌  Solo quien ejecutó el comando.", ephemeral=True)
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("❌  Cancelado.", ephemeral=True)

@bot.tree.command(name="limpiar_historial", description="Resetea todos los warns y strikes de un staff")
@discord.app_commands.describe(staff="Staff al que limpiar el historial")
async def limpiar_historial_slash(interaction: discord.Interaction, staff: discord.Member):
    if not es_head(interaction.user):
        return await interaction.response.send_message("❌  Solo **Head staff**.", ephemeral=True)
    data   = _cargar_datos()
    sd     = data.get(str(staff.id), {"warns": [], "strikes": []})
    tw, ts = len(sd["warns"]), len(sd["strikes"])
    e = discord.Embed(color=COLOR_WARN)
    e.title = "⚠️  Confirmar limpieza de historial"
    e.description = (
        f"¿Resetear el historial de {staff.mention}?\n\n"
        f"⚠️  Warns: **{tw}**  |  💥  Strikes: **{ts}**\n\n"
        f"*Esta acción no se puede deshacer.*"
    )
    _footer(e, interaction.guild)
    await interaction.response.send_message(
        embed=e, view=ConfirmarLimpiarView(staff, interaction.user), ephemeral=True)

# ╔═══════════════════════════════════════════════════════════════╗
#   🗒️  NOTAS INTERNAS
# ╚═══════════════════════════════════════════════════════════════╝
@bot.tree.command(name="nota", description="Agrega una nota interna sobre un staff (sin sanción)")
@discord.app_commands.describe(staff="Staff", nota="Contenido de la nota")
async def nota_slash(interaction: discord.Interaction, staff: discord.Member, nota: str):
    if not es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo **High Staff** o superior.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    data = _cargar_notas()
    key  = str(staff.id)
    if key not in data: data[key] = []
    data[key].append({"nota": nota, "por": interaction.user.id, "fecha": _fecha_str()})
    _guardar_notas(data)

    e = discord.Embed(color=COLOR_BLUE, timestamp=datetime.datetime.now())
    e.set_author(name="Notas Internas  ✦  NightMc Network",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    e.title = f"📝  Nota Agregada — {staff.display_name}"
    e.set_thumbnail(url=staff.display_avatar.url)
    e.description = (
        f"{SEP}\n**👤  Staff:** {staff.mention}\n"
        f"**✍️  Agregada por:** {interaction.user.mention}\n"
        f"**📅  Fecha:** <t:{_now_ts()}:F>\n{SEP}"
    )
    e.add_field(name=f"📝  Nota #{len(data[key])}", value=f"> {nota}", inline=False)
    e.add_field(name="📊  Total", value=f"`{len(data[key])}`", inline=True)
    _footer(e, interaction.guild)
    await _log(interaction.guild, e)
    await interaction.followup.send(
        f"✅  Nota #{len(data[key])} agregada para {staff.mention}.", ephemeral=True)

@bot.tree.command(name="notas", description="Ver las notas internas de un staff")
@discord.app_commands.describe(staff="Staff a consultar")
async def notas_slash(interaction: discord.Interaction, staff: discord.Member):
    if not es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo **High Staff** o superior.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    notas = _cargar_notas().get(str(staff.id), [])

    e = discord.Embed(color=COLOR_BLUE, timestamp=datetime.datetime.now())
    e.set_author(name="Notas Internas  ✦  NightMc Network",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    e.title = f"📝  Notas — {staff.display_name}"
    e.set_thumbnail(url=staff.display_avatar.url)
    if not notas:
        e.description = "✅  Sin notas registradas."
    else:
        for i, n in enumerate(notas[-10:], 1):
            autor = interaction.guild.get_member(n["por"])
            e.add_field(name=f"📝  Nota #{i}  —  {n['fecha']}",
                        value=f"> {n['nota']}\n> *— {autor.display_name if autor else 'Desconocido'}*",
                        inline=False)
    _footer(e, interaction.guild)
    await interaction.followup.send(embed=e, ephemeral=True)

async def _ac_nota_staff(interaction, current):
    data = _cargar_notas()
    out  = []
    for uid, notas in data.items():
        if not notas: continue
        m = interaction.guild.get_member(int(uid))
        if m and current.lower() in m.display_name.lower():
            out.append(discord.app_commands.Choice(
                name=f"{m.display_name}  ({len(notas)} nota{'s' if len(notas)!=1 else ''})",
                value=uid))
    return out[:25]

async def _ac_nota_num(interaction, current):
    staff_val = next((o["value"] for o in interaction.data.get("options", [])
                      if o["name"] == "staff"), None)
    if not staff_val:
        return [discord.app_commands.Choice(name="Primero selecciona un staff", value="none")]
    notas = _cargar_notas().get(staff_val, [])
    if not notas:
        return [discord.app_commands.Choice(name="Sin notas", value="none")]
    return [discord.app_commands.Choice(
        name=f"Nota #{i+1} — {n['fecha']} — {n['nota'][:40]}", value=str(i))
        for i, n in enumerate(notas) if current.lower() in n["nota"].lower()][:25]

@bot.tree.command(name="retirar_nota", description="Retira una nota interna de un staff")
@discord.app_commands.describe(staff="Staff", nota="Nota a retirar")
@discord.app_commands.autocomplete(staff=_ac_nota_staff, nota=_ac_nota_num)
async def retirar_nota_slash(interaction: discord.Interaction, staff: str, nota: str):
    if not es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo **High Staff** o superior.", ephemeral=True)
    if nota == "none":
        return await interaction.response.send_message("❌  Selecciona una nota válida.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    data  = _cargar_notas()
    notas = data.get(staff, [])
    try:
        idx = int(nota)
    except Exception:
        return await interaction.followup.send("❌  Nota inválida.", ephemeral=True)
    if idx < 0 or idx >= len(notas):
        return await interaction.followup.send("❌  Esa nota ya no existe.", ephemeral=True)
    retirada    = notas.pop(idx)
    data[staff] = notas
    _guardar_notas(data)
    miembro = interaction.guild.get_member(int(staff))
    nombre  = miembro.mention if miembro else f"<@{staff}>"
    await interaction.followup.send(
        f"✅  Nota retirada de {nombre}:\n> *{retirada['nota']}*", ephemeral=True)

# ╔═══════════════════════════════════════════════════════════════╗
#   🔍  STAFF INFO
# ╚═══════════════════════════════════════════════════════════════╝
@bot.tree.command(name="staff_info", description="Muestra toda la información de un staff")
@discord.app_commands.describe(miembro="Staff a consultar")
async def staff_info_slash(interaction: discord.Interaction, miembro: discord.Member):
    if not es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo **High Staff** o superior.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)

    data_s = _cargar_datos()
    data_n = _cargar_notas()
    sd     = _get_staff_data(data_s, miembro.id)
    notas  = data_n.get(str(miembro.id), [])
    tw, ts = len(sd["warns"]), len(sd["strikes"])
    bw, bs = _barras(tw, ts)

    # Racha
    data_r  = _cargar_rachas()
    r_data  = _get_racha(data_r, miembro.id)

    roles_s = [r for r in miembro.roles if r.name in ROLES_STAFF_ALL]
    rango   = roles_s[-1].mention if roles_s else "*Sin rango de staff*"

    e = discord.Embed(color=COLOR_BLUE, timestamp=datetime.datetime.now())
    e.set_author(name="Staff Info  ✦  NightMc Network",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    e.title = f"🔍  {miembro.display_name}"
    e.set_thumbnail(url=miembro.display_avatar.url)
    e.description = (
        f"{SEP}\n**👤  Usuario:** {miembro.mention}\n"
        f"**🏅  Rango:** {rango}\n"
        f"**🆔  ID:** `{miembro.id}`\n"
        f"**📅  En el servidor desde:** <t:{int(miembro.joined_at.timestamp())}:D>\n{SEP}"
    )
    e.add_field(name=f"⚠️  Warns `{tw}/{WARNS_PARA_STRIKE}`",    value=bw, inline=True)
    e.add_field(name=f"💥  Strikes `{ts}/{STRIKES_PARA_DEMOTE}`", value=bs, inline=True)
    e.add_field(name="📝  Notas", value=f"`{len(notas)}`", inline=True)
    e.add_field(
        name=f"{_emoji_racha(r_data['racha'])}  Racha actual",
        value=f"`{r_data['racha']} días`", inline=True)
    e.add_field(name="🏆  Racha máxima", value=f"`{r_data['max_racha']} días`", inline=True)
    if sd["warns"]:
        e.add_field(name="📄  Warns activos",
                    value="\n".join(f"`{i+1}.` {w['fecha']} — {w['motivo']}"
                                    for i, w in enumerate(sd["warns"])), inline=False)
    if sd["strikes"]:
        e.add_field(name="📄  Strikes activos",
                    value="\n".join(f"`{i+1}.` {s['fecha']} — {s['motivo']}"
                                    for i, s in enumerate(sd["strikes"])), inline=False)
    if notas:
        e.add_field(name="📝  Últimas notas",
                    value="\n".join(f"`{i+1}.` {n['fecha']} — {n['nota'][:50]}"
                                    for i, n in enumerate(notas[-5:])), inline=False)
    _footer(e, interaction.guild)
    await interaction.followup.send(embed=e, ephemeral=True)

# ╔═══════════════════════════════════════════════════════════════╗
#   📬  INACTIVIDAD
# ╚═══════════════════════════════════════════════════════════════╝
class InactividadModal(ui.Modal, title="NightMc  ·  Registrar Inactividad"):
    ign    = ui.TextInput(label="IGN (Nick en Minecraft)",
                          placeholder="Tu nick exacto en el servidor")
    inicio = ui.TextInput(label="Empieza",
                          placeholder="Ej: 15 de marzo · Hoy · Esta noche")
    fin    = ui.TextInput(label="Termina",
                          placeholder="Ej: 20 de marzo · En 5 días")
    razon  = ui.TextInput(label="Razón", style=discord.TextStyle.paragraph,
                          placeholder="Motivo de tu inactividad")

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user  = interaction.user
        canal = discord.utils.get(guild.text_channels, name=CANAL_INACTIVIDAD)
        if not canal:
            return await interaction.response.send_message(
                f"❌  No encontré el canal `{CANAL_INACTIVIDAD}`.", ephemeral=True)
        ts = _now_ts()
        e  = discord.Embed(color=COLOR_BLUE, timestamp=datetime.datetime.now())
        e.set_author(name="Registro de Inactividad  ✦  NightMc Network",
                     icon_url=guild.icon.url if guild.icon else None)
        e.title = "📬  Inactividad Registrada"
        e.set_thumbnail(url=user.display_avatar.url)
        e.description = (
            f"{SEP}\n**👤  Staff:** {user.mention}\n"
            f"**🎮  IGN:** `{self.ign.value}`\n"
            f"**📅  Registrado:** <t:{ts}:F>\n{SEP}"
        )
        e.add_field(name="▶️  Empieza", value=f"> {self.inicio.value}", inline=True)
        e.add_field(name="⏹️  Termina", value=f"> {self.fin.value}",   inline=True)
        e.add_field(name="📋  Razón",   value=f"> {self.razon.value}", inline=False)
        _footer(e, guild)
        await canal.send(embed=e)
        await interaction.response.send_message(
            f"✅  Inactividad registrada en {canal.mention}.", ephemeral=True)

@bot.tree.command(name="inactividad", description="Registra tu propia inactividad")
async def inactividad_slash(interaction: discord.Interaction):
    if not es_staff(interaction.user):
        return await interaction.response.send_message(
            "❌  Solo miembros del **Staff** pueden usar este comando.", ephemeral=True)
    await interaction.response.send_modal(InactividadModal())

# ╔═══════════════════════════════════════════════════════════════╗
#   💼  REUNIÓN
# ╚═══════════════════════════════════════════════════════════════╝
@bot.tree.command(name="reunion", description="Publica una convocatoria de reunión al Staff Team")
@discord.app_commands.describe(
    numero="Número de reunión (Ej: 2)",
    fecha="Formato: YYYY-MM-DD HH:MM en hora México UTC-6 (Ej: 2026-03-15 11:30)",
    temas="Temas separados por coma (Ej: Bugs,Tickets,Expansión)",
)
async def reunion_slash(interaction: discord.Interaction, numero: str, fecha: str, temas: str):
    if not es_head(interaction.user):
        return await interaction.response.send_message("❌  Solo **Head staff**.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)

    canal = discord.utils.get(interaction.guild.text_channels, name=CANAL_REUNIONES)
    if not canal:
        return await interaction.followup.send(
            f"❌  No encontré el canal `{CANAL_REUNIONES}`.", ephemeral=True)

    try:
        dt_local = datetime.datetime.strptime(fecha.strip(), "%Y-%m-%d %H:%M")
        dt_utc   = dt_local + datetime.timedelta(hours=6)
        ts_unix  = int(dt_utc.timestamp())
    except ValueError:
        return await interaction.followup.send(
            "❌  Formato incorrecto. Usa: `YYYY-MM-DD HH:MM`\nEjemplo: `2026-03-15 11:30`", ephemeral=True)

    rol_staff  = discord.utils.get(interaction.guild.roles, name=STAFF_TEAM)
    canal_inas = discord.utils.get(interaction.guild.text_channels, name=CANAL_INACTIVIDAD)
    inas_str   = canal_inas.mention if canal_inas else f"`{CANAL_INACTIVIDAD}`"
    temas_str  = "\n".join(f"> ✦  {t.strip()}" for t in temas.split(",") if t.strip())

    e = discord.Embed(color=COLOR_BLUE, timestamp=datetime.datetime.now())
    e.set_author(name="NightMc Network  ✦  Staff Team",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    e.title = f"💼  Reunión #{numero} — NightMC Network"
    e.description = (
        f"Se convoca a todo el {rol_staff.mention if rol_staff else '@Staff team'} "
        f"a la **reunión #{numero}**.\n{SEP}"
    )
    e.add_field(name="📅  Fecha y hora",
                value=f"> 🗓️  <t:{ts_unix}:F>\n> ⏰  <t:{ts_unix}:R>", inline=False)
    e.add_field(name="📋  Temas a tratar", value=temas_str, inline=False)
    e.add_field(name=SEP, value=(
        f"> ⏰  Faltas o retrasos: comunícalos en {inas_str}\n"
        f"> ⚠️  La inasistencia sin justificar puede resultar en sanción.\n"
        f"> 🙌  Gracias a todos — *{interaction.user.display_name}*"
    ), inline=False)
    e.set_image(url=BANNER_STAFF)
    _footer(e, interaction.guild)

    await canal.send(content=rol_staff.mention if rol_staff else "@Staff team", embed=e)
    await interaction.followup.send(f"✅  Reunión #{numero} publicada en {canal.mention}.", ephemeral=True)

# ╔═══════════════════════════════════════════════════════════════╗
#   🔺  STRIKE APPEALS
# ╚═══════════════════════════════════════════════════════════════╝
tickets_abiertos: dict[int, int] = {}

class AppealModal(ui.Modal, title="NightMc  ·  Strike Appeal"):
    ign        = ui.TextInput(label="IGN (Nick en Minecraft)",
                              placeholder="Tu nick exacto en el servidor")
    razon      = ui.TextInput(label="Razón del strike/warn",
                              placeholder="¿Por qué te fue dado?",
                              style=discord.TextStyle.paragraph)
    motivo     = ui.TextInput(label="Motivo para retirarlo",
                              placeholder="¿Por qué debería ser retirado?",
                              style=discord.TextStyle.paragraph)
    pruebas    = ui.TextInput(label="Pruebas (links, capturas, etc.)",
                              placeholder="Links o escribe 'Sin pruebas'",
                              required=False)
    strike_num = ui.TextInput(label="Strike/Warn #",
                              placeholder="Ej: Strike #1, Warn #2")

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user  = interaction.user

        if user.id in tickets_abiertos:
            ch = guild.get_channel(tickets_abiertos[user.id])
            if ch:
                return await interaction.response.send_message(
                    f"❌  Ya tienes un appeal abierto en {ch.mention}.", ephemeral=True)
            del tickets_abiertos[user.id]

        await interaction.response.defer(ephemeral=True)

        rol_head = discord.utils.get(guild.roles, name=ROL_HEAD)
        cat      = await _get_or_create_cat(guild, CAT_APPEAL)
        perms    = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me:           discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            user:               discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        }
        if rol_head:
            perms[rol_head] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            canal = await guild.create_text_channel(
                name=f"appeal-{user.name[:15].lower()}",
                category=cat, overwrites=perms,
                topic=f"appeal | ownerid:{user.id}")
        except discord.Forbidden:
            return await interaction.followup.send("❌  Sin permisos para crear canales.", ephemeral=True)

        tickets_abiertos[user.id] = canal.id

        e = discord.Embed(color=COLOR_STRIKE)
        e.set_author(name="SISTEMA DE APPEALS — NIGHTMC STAFF",
                     icon_url=guild.icon.url if guild.icon else None)
        e.title = "🔺  Strike Appeal — NightMC Network"
        e.description = (
            f"Buenas {user.mention}. Tu apelación será revisada por el **Head staff**.\n"
            f"Sé paciente, el proceso puede tardar varios días.\n{SEP}"
        )
        e.add_field(name="👤  Revisará",            value=f"> {rol_head.mention if rol_head else '@Head staff'}", inline=False)
        e.add_field(name="🎮  IGN",                 value=f"```{self.ign.value}```",        inline=True)
        e.add_field(name="🔢  Strike/Warn #",       value=f"```{self.strike_num.value}```", inline=True)
        e.add_field(name="📋  Razón del strike",    value=f"```{self.razon.value}```",      inline=False)
        e.add_field(name="💬  Motivo de apelación", value=f"```{self.motivo.value}```",     inline=False)
        e.add_field(name="📎  Pruebas",             value=f"```{self.pruebas.value or 'Sin pruebas'}```", inline=False)
        e.add_field(name=SEP, value=(
            "> ⚠️  Las apelaciones falsas serán sancionadas.\n"
            "> ⏳  El Head staff revisará tu caso con atención.\n"
            "> 🙏  Gracias por usar el sistema oficial de NightMC."
        ), inline=False)
        e.set_thumbnail(url=user.display_avatar.url)
        e.set_image(url=BANNER_STAFF)
        _footer(e, guild)

        await canal.send(
            content=f"{user.mention}  {rol_head.mention if rol_head else ''}",
            embed=e, view=AppealControl(owner_id=user.id))

        await interaction.followup.send(f"✅  Appeal abierto en {canal.mention}", ephemeral=True)

        log_e = discord.Embed(title="🔺  Appeal Abierto", color=COLOR_STRIKE,
                              timestamp=datetime.datetime.now())
        log_e.add_field(name="Staff",    value=user.mention,          inline=True)
        log_e.add_field(name="Canal",    value=canal.mention,         inline=True)
        log_e.add_field(name="IGN",      value=self.ign.value,        inline=True)
        log_e.add_field(name="Strike #", value=self.strike_num.value, inline=True)
        log_e.set_thumbnail(url=user.display_avatar.url)
        log_e.set_footer(text=FOOTER)
        await _log(guild, log_e, LOGS_TICKETS)

class AppealControl(ui.View):
    def __init__(self, owner_id: int = 0):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    def _owner(self, canal) -> int:
        return self.owner_id or _owner_from_topic(canal)

    @ui.button(label="Claim", style=discord.ButtonStyle.success,
               emoji="🔑", custom_id="appeal_claim")
    async def claim(self, interaction: discord.Interaction, button: ui.Button):
        if not es_head(interaction.user):
            return await interaction.response.send_message(
                "❌  Solo **Head staff** puede reclamar este appeal.", ephemeral=True)
        button.label    = f"Claimed  ·  {interaction.user.display_name}"
        button.emoji    = None
        button.disabled = True
        await interaction.response.edit_message(view=self)
        e = discord.Embed(color=COLOR_OK)
        e.description = f"🔑  **{interaction.user.mention}** tomó el control de este appeal."
        e.set_footer(text=FOOTER)
        await interaction.channel.send(embed=e)

    @ui.button(label="Cerrar", style=discord.ButtonStyle.danger,
               emoji="🔒", custom_id="appeal_close")
    async def cerrar(self, interaction: discord.Interaction, button: ui.Button):
        if not es_head(interaction.user):
            return await interaction.response.send_message(
                "❌  Solo **Head staff** puede cerrar este appeal.", ephemeral=True)
        owner_id = self._owner(interaction.channel)
        await interaction.response.send_message(
            embed=discord.Embed(color=COLOR_WARN,
                description="⚖️  Antes de cerrar, ¿cuál es el resultado de este appeal?"),
            view=AppealResultView(owner_id=owner_id, cerrado_por=interaction.user),
            ephemeral=True)

class AppealResultView(ui.View):
    def __init__(self, owner_id: int, cerrado_por: discord.Member):
        super().__init__(timeout=60)
        self.owner_id    = owner_id
        self.cerrado_por = cerrado_por

    async def _resolver(self, interaction: discord.Interaction,
                        resultado: str, color: int, emoji: str):
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(view=self)

        canal = interaction.channel
        guild = interaction.guild
        owner = guild.get_member(self.owner_id)

        e = discord.Embed(color=color, timestamp=datetime.datetime.now())
        e.title = f"{emoji}  Appeal {resultado}"
        e.description = (
            f"**Staff:** {owner.mention if owner else f'<@{self.owner_id}>'}\n"
            f"**Resultado:** {resultado}\n"
            f"**Resuelto por:** {self.cerrado_por.mention}\n"
            f"**Fecha:** <t:{_now_ts()}:F>"
        )
        e.set_footer(text=FOOTER)
        await canal.send(embed=e)

        if owner:
            val_embed = discord.Embed(color=COLOR_GOLD, timestamp=datetime.datetime.now())
            val_embed.title = "⭐  ¿Cómo fue tu experiencia?"
            val_embed.description = (
                f"Tu appeal fue marcado como **{resultado}**.\n"
                f"Por favor valora la atención recibida.\n{SEP}\n"
                f"Selecciona una calificación del **1 al 5**:"
            )
            val_embed.set_footer(text=FOOTER)
            await canal.send(
                content=owner.mention,
                embed=val_embed,
                view=ValoracionView(
                    owner_id=self.owner_id,
                    canal=canal,
                    guild=guild,
                    cerrado_por=self.cerrado_por,
                    resultado=resultado))
        else:
            await _cerrar_appeal(canal, guild, self.cerrado_por, self.owner_id, resultado)

    @ui.button(label="Aceptado",    style=discord.ButtonStyle.success,   emoji="✅")
    async def aceptado(self, i, b):    await self._resolver(i, "Aceptado",    COLOR_OK,     "✅")
    @ui.button(label="Rechazado",   style=discord.ButtonStyle.danger,    emoji="❌")
    async def rechazado(self, i, b):   await self._resolver(i, "Rechazado",   COLOR_DANGER, "❌")
    @ui.button(label="Sin resolver", style=discord.ButtonStyle.secondary, emoji="⏸️")
    async def sin_resolver(self, i, b): await self._resolver(i, "Sin resolver", COLOR_BASE,  "⏸️")

class ValoracionView(ui.View):
    def __init__(self, owner_id: int, canal, guild: discord.Guild,
                 cerrado_por: discord.Member, resultado: str):
        super().__init__(timeout=120)
        self.owner_id    = owner_id
        self.canal       = canal
        self.guild       = guild
        self.cerrado_por = cerrado_por
        self.resultado   = resultado

    async def on_timeout(self):
        try:
            await _cerrar_appeal(self.canal, self.guild, self.cerrado_por,
                                 self.owner_id, self.resultado)
        except Exception:
            pass

    async def _dar_estrellas(self, interaction: discord.Interaction, estrellas: int):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "❌  Solo el dueño del ticket puede valorar.", ephemeral=True)
        for item in self.children: item.disabled = True
        await interaction.response.send_modal(
            ValoracionModal(
                estrellas=estrellas,
                owner_id=self.owner_id,
                canal=self.canal,
                guild=self.guild,
                cerrado_por=self.cerrado_por,
                resultado=self.resultado))

    @ui.button(label="⭐",     style=discord.ButtonStyle.secondary, custom_id="val_1")
    async def v1(self, i, b): await self._dar_estrellas(i, 1)
    @ui.button(label="⭐⭐",   style=discord.ButtonStyle.secondary, custom_id="val_2")
    async def v2(self, i, b): await self._dar_estrellas(i, 2)
    @ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary, custom_id="val_3")
    async def v3(self, i, b): await self._dar_estrellas(i, 3)
    @ui.button(label="⭐⭐⭐⭐",  style=discord.ButtonStyle.secondary, custom_id="val_4")
    async def v4(self, i, b): await self._dar_estrellas(i, 4)
    @ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.success,   custom_id="val_5")
    async def v5(self, i, b): await self._dar_estrellas(i, 5)

class ValoracionModal(ui.Modal, title="NightMc  ·  Valoración del Appeal"):
    comentario = ui.TextInput(
        label="Comentario (opcional)",
        placeholder="¿Algo que quieras añadir sobre la atención recibida?",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=300)

    def __init__(self, estrellas, owner_id, canal, guild, cerrado_por, resultado):
        super().__init__()
        self.estrellas   = estrellas
        self.owner_id    = owner_id
        self.canal       = canal
        self.guild       = guild
        self.cerrado_por = cerrado_por
        self.resultado   = resultado

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "✅  ¡Gracias por tu valoración!", ephemeral=True)

        stars_str = "⭐" * self.estrellas + "☆" * (5 - self.estrellas)

        canal_val = discord.utils.get(self.guild.text_channels, name=CANAL_VALORACIONES)
        if canal_val:
            v = discord.Embed(color=COLOR_GOLD, timestamp=datetime.datetime.now())
            v.set_author(name="Valoraciones  ✦  NightMc Network",
                         icon_url=self.guild.icon.url if self.guild.icon else None)
            v.title = "⭐  Nueva Valoración de Appeal"
            v.set_thumbnail(url=interaction.user.display_avatar.url)
            v.description = (
                f"{SEP}\n**👤  Staff:** {interaction.user.mention}\n"
                f"**👮  Atendido por:** {self.cerrado_por.mention}\n"
                f"**⚖️  Resultado:** {self.resultado}\n"
                f"**📅  Fecha:** <t:{_now_ts()}:F>\n{SEP}"
            )
            v.add_field(name="⭐  Calificación",
                        value=f"> {stars_str}  `{self.estrellas}/5`", inline=False)
            if self.comentario.value:
                v.add_field(name="💬  Comentario",
                            value=f"> {self.comentario.value}", inline=False)
            v.set_footer(text=FOOTER)
            await canal_val.send(embed=v)

        await _cerrar_appeal(self.canal, self.guild, self.cerrado_por,
                             self.owner_id, self.resultado)

async def _cerrar_appeal(canal, guild: discord.Guild,
                         cerrado_por: discord.Member, owner_id: int, resultado: str):
    tickets_abiertos.pop(owner_id, None)
    e = discord.Embed(color=COLOR_DANGER)
    e.description = "🔒  Cerrando en **3 segundos**..."
    e.set_footer(text=FOOTER)
    await canal.send(embed=e)

    log_e = discord.Embed(title="🔒  Appeal Cerrado", color=COLOR_DANGER,
                          timestamp=datetime.datetime.now())
    log_e.add_field(name="Canal",       value=canal.name,          inline=True)
    log_e.add_field(name="Resultado",   value=resultado,           inline=True)
    log_e.add_field(name="Cerrado por", value=cerrado_por.mention, inline=True)
    log_e.set_footer(text=FOOTER)
    await _log(guild, log_e, LOGS_TICKETS)
    await _log(guild, log_e)

    await asyncio.sleep(3)
    try: await canal.delete()
    except discord.Forbidden: pass

def _es_appeal(canal) -> bool:
    return bool(canal.topic and "ownerid:" in canal.topic) if canal.topic else False

@bot.tree.command(name="claim", description="Claimea el appeal actual")
async def claim_slash(interaction: discord.Interaction):
    if not _es_appeal(interaction.channel):
        return await interaction.response.send_message(
            "❌  Solo en canales de appeal.", ephemeral=True)
    if not es_head(interaction.user):
        return await interaction.response.send_message(
            "❌  Solo **Head staff**.", ephemeral=True)
    e = discord.Embed(color=COLOR_OK)
    e.description = f"🔑  **{interaction.user.mention}** tomó el control de este appeal."
    e.set_footer(text=FOOTER)
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="close", description="Cierra el appeal actual")
async def close_slash(interaction: discord.Interaction):
    if not _es_appeal(interaction.channel):
        return await interaction.response.send_message(
            "❌  Solo en canales de appeal.", ephemeral=True)
    if not es_head(interaction.user):
        return await interaction.response.send_message(
            "❌  Solo **Head staff**.", ephemeral=True)
    owner_id = _owner_from_topic(interaction.channel)
    await interaction.response.send_message(
        embed=discord.Embed(color=COLOR_WARN,
            description="⚖️  ¿Cuál es el resultado de este appeal?"),
        view=AppealResultView(owner_id=owner_id, cerrado_por=interaction.user),
        ephemeral=True)

@bot.command(name="claim")
async def claim_cmd(ctx):
    try: await ctx.message.delete()
    except: pass
    if not _es_appeal(ctx.channel):
        return await ctx.send("❌  Solo en canales de appeal.")
    if not es_head(ctx.author):
        return await ctx.send("❌  Solo **Head staff**.")
    e = discord.Embed(color=COLOR_OK)
    e.description = f"🔑  **{ctx.author.mention}** tomó el control de este appeal."
    e.set_footer(text=FOOTER)
    await ctx.send(embed=e)

@bot.command(name="close")
async def close_cmd(ctx):
    try: await ctx.message.delete()
    except: pass
    if not _es_appeal(ctx.channel):
        return await ctx.send("❌  Solo en canales de appeal.")
    if not es_head(ctx.author):
        return await ctx.send("❌  Solo **Head staff**.")
    owner_id = _owner_from_topic(ctx.channel)
    await ctx.send(
        embed=discord.Embed(color=COLOR_WARN,
            description="⚖️  ¿Cuál es el resultado de este appeal?"),
        view=AppealResultView(owner_id=owner_id, cerrado_por=ctx.author))

# ╔═══════════════════════════════════════════════════════════════╗
#   🚀  SETUP & SYNC
# ╚═══════════════════════════════════════════════════════════════╝
class AppealLauncher(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Strike Appeal", style=discord.ButtonStyle.danger,
               emoji="🔺", custom_id="appeal_launch")
    async def launch(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AppealModal())

def _setup_embed(guild):
    e = discord.Embed(color=COLOR_STRIKE)
    e.set_author(name="SISTEMA DE APPEALS — NIGHTMC STAFF",
                 icon_url=guild.icon.url if guild.icon else None)
    e.title = "🔺  Strike Appeals — NightMC Network"
    e.description = (
        f"¿Crees que tu sanción fue injusta?\n"
        f"Pulsa el botón para abrir un appeal con el **Head staff**.\n{SEP}"
    )
    e.add_field(name="📋  Necesitarás", value=(
        "> 🎮  Tu IGN en el servidor\n"
        "> 🔢  Número de strike o warn\n"
        "> 📝  Razón por la que fue dado\n"
        "> 💬  Motivo para retirarlo\n"
        "> 📎  Pruebas si las tienes"
    ), inline=False)
    e.add_field(name=SEP, value=(
        "> ⚠️  Los appeals falsos serán sancionados\n"
        "> ⏳  El proceso puede tardar varios días\n"
        "> 🔒  Solo el Head staff puede resolver"
    ), inline=False)
    e.set_image(url=BANNER_STAFF)
    return _footer(e, guild)

@bot.command(name="setup")
async def setup_cmd(ctx):
    if not es_head(ctx.author):
        return await ctx.send("❌  Solo **Head staff**.")
    try: await ctx.message.delete()
    except discord.Forbidden: pass
    await ctx.send(embed=_setup_embed(ctx.guild), view=AppealLauncher())

@bot.command(name="sync")
async def sync_cmd(ctx):
    if not es_head(ctx.author):
        return await ctx.send("❌  Solo **Head staff**.")
    msg = await ctx.send("⏳  Registrando comandos...")
    try:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await msg.edit(content=f"✅  **{len(synced)} comandos** registrados. Haz **Ctrl+R** si no aparecen.")
    except Exception as ex:
        await msg.edit(content=f"❌  Error: {ex}")
    try: await ctx.message.delete()
    except discord.Forbidden: pass

@bot.command(name="clearglobal")
async def clearglobal_cmd(ctx):
    if not es_head(ctx.author):
        return await ctx.send("❌  Solo **Head staff**.")
    msg = await ctx.send("⏳  Limpiando comandos globales...")
    try:
        await bot.http.bulk_upsert_global_commands(bot.application_id, [])
        await msg.edit(content="✅  Comandos globales eliminados. Espera 1-2 minutos y recarga Discord.")
    except Exception as ex:
        await msg.edit(content=f"❌  Error: {ex}")

# ╔═══════════════════════════════════════════════════════════════╗
#   🧪  TESTING
# ╚═══════════════════════════════════════════════════════════════╝
@bot.tree.command(name="test_iniciar_semana", description="[TEST] Marca el inicio de la semana de puntos")
async def test_iniciar_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not es_head(interaction.user):
        return await interaction.followup.send("❌  Solo **Head staff**.", ephemeral=True)
    sotw_data = _cargar_sotw()
    sotw_data["semana_activa"] = True
    _guardar_sotw(sotw_data)
    e = discord.Embed(color=COLOR_OK)
    e.title = "🧪  TEST — Semana Iniciada"
    e.description = (
        "> ✅  Semana marcada como **activa**.\n"
        "> Los puntos de bans empezarán a contarse normalmente.\n"
        "> Usa `/test_cerrar_semana` para simular el cierre."
    )
    e.set_footer(text="[MODO TEST]  " + FOOTER)
    await interaction.followup.send(embed=e, ephemeral=True)

@bot.command(name="test_iniciar_semana")
async def test_iniciar_cmd(ctx):
    if not es_head(ctx.author):
        return await ctx.send("❌  Solo **Head staff**.")
    sotw_data = _cargar_sotw()
    sotw_data["semana_activa"] = True
    _guardar_sotw(sotw_data)
    e = discord.Embed(color=COLOR_OK)
    e.title = "🧪  TEST — Semana Iniciada"
    e.description = (
        "> ✅  Semana marcada como **activa**.\n"
        "> Los puntos de bans empezarán a contarse normalmente.\n"
        "> Usa `st!test_cerrar_semana` para simular el cierre."
    )
    e.set_footer(text="[MODO TEST]  " + FOOTER)
    await ctx.send(embed=e)

@bot.tree.command(name="test_cerrar_semana", description="[TEST] Simula el cierre de semana con los puntos actuales")
async def test_cerrar_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not es_head(interaction.user):
        return await interaction.followup.send("❌  Solo **Head staff**.", ephemeral=True)
    await _reiniciar_semana(interaction.guild, interaction.user, test=True)
    await interaction.followup.send("✅  [TEST] Cierre de semana simulado.", ephemeral=True)

@bot.command(name="test_cerrar_semana")
async def test_cerrar_cmd(ctx):
    if not es_head(ctx.author):
        return await ctx.send("❌  Solo **Head staff**.")
    await _reiniciar_semana(ctx.guild, ctx.author, test=True)
    await ctx.send("✅  [TEST] Cierre de semana simulado.")

# ╔═══════════════════════════════════════════════════════════════╗
#   💬  HELP
# ╚═══════════════════════════════════════════════════════════════╝
def _build_help_embed(member: discord.Member, guild: discord.Guild) -> discord.Embed:
    head  = es_head(member)
    sup   = es_superior(member)
    staff = es_staff(member)

    e = discord.Embed(color=COLOR_BASE, timestamp=datetime.datetime.now())
    e.set_author(name="NightMc Network  ✦  Bot de Staff",
                 icon_url=guild.icon.url if guild.icon else None)
    e.set_thumbnail(url=member.display_avatar.url)

    if head:
        rango_str = "👑  Head Staff"
    elif sup:
        rango_str = "🟠  High Staff"
    elif staff:
        rango_str = "🟢  Staff"
    else:
        rango_str = "⚪  Sin rango de staff"

    e.title = "📋  Comandos disponibles para ti"
    e.description = f"{SEP}\n**Rango detectado:** {rango_str}\n{SEP}"

    if staff or sup or head:
        e.add_field(name="📬  General  🟢", value=(
            "> `/inactividad` — Registrar tu inactividad\n"
            "> `/puntos` · `st!puntos` — Ver tus puntos\n"
            "> `/ps` · `st!ps` — Ranking semanal\n"
            "> `/rachas` · `st!rachas` — Ranking de rachas\n"
            "> `/help` · `st!help` — Este mensaje"
        ), inline=False)

    if sup or head:
        e.add_field(name="⚠️  Sanciones  🟠", value=(
            "> `/sancion @staff <tipo> <motivo>` — Warn o Strike\n"
            "> `/historial @staff` — Ver historial de sanciones\n"
            "> `/remover` — Remover una sanción específica\n"
            "> `/staff_info @staff` — Info completa del staff\n"
            "> ⚙️  3 warns = strike auto · 3 strikes = kick"
        ), inline=False)
        e.add_field(name="📝  Notas  🟡", value=(
            "> `/nota @staff <nota>` — Agregar nota interna\n"
            "> `/notas @staff` — Ver notas\n"
            "> `/retirar_nota` — Eliminar nota"
        ), inline=False)

    if head:
        e.add_field(name="💼  Head Staff  🔴", value=(
            "> `/reunion <numero> <fecha> <temas>` — Convocar reunión\n"
            "> `/limpiar_historial @staff` — Resetear historial completo\n"
            "> `/rp` · `st!rp` — Cerrar semana + anunciar ganadores\n"
            "> `/resetear_puntos @staff` — Resetear puntos de un staff\n"
            "> `/claim` · `st!claim` — Claimear appeal\n"
            "> `/close` · `st!close` — Cerrar appeal\n"
            "> `st!setup` — Panel de appeals\n"
            "> `st!sync` — Sincronizar slash commands\n"
            "> `st!clearglobal` — Limpiar comandos duplicados"
        ), inline=False)
        e.add_field(name="🧪  Testing  🔬", value=(
            "> `/test_iniciar_semana` · `st!test_iniciar_semana`\n"
            "> `/test_cerrar_semana` · `st!test_cerrar_semana`\n"
            "> `/tt @staff` — Enviar DM de inactividad de prueba"
        ), inline=False)

    if not staff and not sup and not head:
        e.description += "\n> ❌  No tienes roles de staff asignados."

    _footer(e, guild)
    return e

@bot.tree.command(name="help", description="Muestra los comandos disponibles según tu rango")
async def help_slash(interaction: discord.Interaction):
    e = _build_help_embed(interaction.user, interaction.guild)
    try:
        await interaction.user.send(embed=e)
        await interaction.response.send_message("📬  Te envié los comandos por DM.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(embed=e, ephemeral=True)

@bot.command(name="help")
async def help_cmd(ctx):
    e = _build_help_embed(ctx.author, ctx.guild)
    try:
        await ctx.author.send(embed=e)
        await ctx.message.add_reaction("📬")
    except discord.Forbidden:
        await ctx.send(embed=e)

# ╔═══════════════════════════════════════════════════════════════╗
#   🚫  SISTEMA DE BANS — VALIDACIÓN + PUNTOS + RACHAS
# ╚═══════════════════════════════════════════════════════════════╝
_CAMPOS = {
    "ign":     re.compile(r"^\s*ign\s*:", re.MULTILINE | re.IGNORECASE),
    "sancion": re.compile(r"^\s*(sanci[oó]n|sancion|ban|punishment|penalty)\s*:", re.MULTILINE | re.IGNORECASE),
    "razon":   re.compile(r"^\s*(raz[oó]n|razon|reason|motivo)\s*:", re.MULTILINE | re.IGNORECASE),
    "pruebas": re.compile(r"^\s*(pruebas?|proof|proofs|evidencia|evidence)\s*:", re.MULTILINE | re.IGNORECASE),
}

_NOMBRES_CAMPOS = {
    "ign":     "IGN",
    "sancion": "Sanción",
    "razon":   "Razón",
    "pruebas": "Pruebas",
}

PLANTILLA_EJEMPLO = (
    "```\n"
    "IGN: NombreDelJugador\n"
    "Sanción: 7 días\n"
    "Razón: Motivo del ban\n"
    "Pruebas: https://link-imagen.com\n"
    "```"
)

def _validar_plantilla(texto: str) -> tuple:
    faltantes = [campo for campo, patron in _CAMPOS.items() if not patron.search(texto)]
    return len(faltantes) == 0, faltantes

_bans_msg_autor: dict[int, int] = {}

def _similaridad(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    if message.channel.name == CANAL_BANS and es_staff(message.author):
        valido, faltantes = _validar_plantilla(message.content)

        if not valido:
            campos_str = ", ".join(_NOMBRES_CAMPOS[c] for c in faltantes)
            try: await message.delete()
            except (discord.Forbidden, discord.NotFound): pass
            try:
                dm = discord.Embed(color=COLOR_DANGER)
                dm.title = "❌  Plantilla incorrecta en bans"
                dm.description = (
                    f"Tu mensaje en **#{CANAL_BANS}** fue eliminado por campos faltantes.\n\n"
                    f"**Faltó:** `{campos_str}`\n\n"
                    f"Usa esta plantilla:\n{PLANTILLA_EJEMPLO}"
                )
                dm.set_footer(text=FOOTER)
                await message.author.send(embed=dm)
            except discord.Forbidden: pass
            await bot.process_commands(message)
            return

        # Anti-duplicados
        canal_id   = message.channel.id
        ahora      = datetime.datetime.now().timestamp()
        limite_12h = ahora - (12 * 3600)

        recientes = _bans_recientes.get(canal_id, [])
        recientes = [(aid, txt, ts) for aid, txt, ts in recientes if ts > limite_12h]

        duplicado = any(_similaridad(message.content, txt) >= 0.80 for _, txt, _ in recientes)

        if duplicado:
            try: await message.delete()
            except (discord.Forbidden, discord.NotFound): pass
            try:
                dm = discord.Embed(color=COLOR_WARN)
                dm.title = "⚠️  Evidencia duplicada"
                dm.description = (
                    f"Tu mensaje en **#{CANAL_BANS}** fue eliminado porque es muy similar\n"
                    f"a una evidencia subida en las últimas **12 horas**.\n\n"
                    f"> No puedes subir la misma sanción dos veces."
                )
                dm.set_footer(text=FOOTER)
                await message.author.send(embed=dm)
            except discord.Forbidden: pass
            await bot.process_commands(message)
            return

        # Válido y no duplicado
        recientes.append((message.author.id, message.content, ahora))
        _bans_recientes[canal_id] = recientes
        _bans_msg_autor[message.id] = message.author.id

        pts = _sumar_punto(message.author.id, 0.1)

        # ── ACTUALIZAR RACHA ─────────────────────────────────────
        racha_data = _actualizar_racha(message.author.id)
        racha_actual = racha_data["racha"]

        try: await message.add_reaction("✅")
        except Exception: pass

        # DM cada 10 evidencias
        if pts["evidencias"] % 10 == 0:
            try:
                dm = discord.Embed(color=COLOR_GOLD)
                dm.title = "🎉  ¡10 evidencias acumuladas!"
                dm.description = (
                    f"¡Llegaste a **{pts['evidencias']} evidencias** esta semana!\n"
                    f"Tienes **{pts['semana']:.1f} puntos** esta semana. ¡Sigue así! 💪"
                )
                dm.set_footer(text=FOOTER)
                await message.author.send(embed=dm)
            except Exception: pass

        # DM por hitos de racha: 3, 7, 14, 30 días
        if racha_actual in (3, 7, 14, 30):
            emoji = _emoji_racha(racha_actual)
            try:
                dm_r = discord.Embed(color=COLOR_PURPLE)
                dm_r.title = f"{emoji}  ¡Hito de racha desbloqueado!"
                dm_r.description = (
                    f"Llevas **{racha_actual} días seguidos** subiendo evidencias.\n"
                    f"¡Sigue así, el equipo lo nota! 🔥"
                )
                dm_r.set_footer(text=FOOTER)
                await message.author.send(embed=dm_r)
            except Exception: pass

        # Publicar en canal rachas si es hito
        if racha_actual in (3, 7, 14, 30):
            canal_r = discord.utils.get(message.guild.text_channels, name=CANAL_RACHAS)
            if canal_r:
                e_r = discord.Embed(color=COLOR_PURPLE, timestamp=datetime.datetime.now())
                e_r.set_author(name="Sistema de Rachas  ✦  NightMc Network",
                               icon_url=message.guild.icon.url if message.guild.icon else None)
                e_r.title = f"{_emoji_racha(racha_actual)}  ¡Hito de racha!"
                e_r.description = (
                    f"{message.author.mention} alcanzó **{racha_actual} días consecutivos** "
                    f"de actividad. ¡Increíble constancia! 🏅"
                )
                e_r.set_thumbnail(url=message.author.display_avatar.url)
                e_r.set_footer(text=FOOTER)
                try: await canal_r.send(embed=e_r)
                except Exception: pass

    await bot.process_commands(message)


@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot: return
    if message.channel.name != CANAL_BANS: return

    autor_id = _bans_msg_autor.pop(message.id, None)
    if autor_id is None: return

    data = _cargar_puntos()
    key  = str(autor_id)
    if key in data:
        data[key]["total"]      = round(max(0.0, data[key]["total"]      - 0.1), 2)
        data[key]["semana"]     = round(max(0.0, data[key]["semana"]     - 0.1), 2)
        data[key]["evidencias"] = max(0, data[key]["evidencias"] - 1)
        _guardar_puntos(data)

    miembro = message.guild.get_member(autor_id) if message.guild else None
    if miembro:
        try:
            dm = discord.Embed(color=COLOR_DANGER)
            dm.title = "🗑️  Evidencia eliminada"
            dm.description = (
                f"Una de tus evidencias en **#{CANAL_BANS}** fue eliminada.\n"
                f"Se te restó **0.1 puntos** de tu cuenta."
            )
            dm.set_footer(text=FOOTER)
            await miembro.send(embed=dm)
        except discord.Forbidden: pass

# ╔═══════════════════════════════════════════════════════════════╗
#   📊  COMANDOS DE PUNTOS
# ╚═══════════════════════════════════════════════════════════════╝
async def _embed_puntos(guild, member):
    data = _cargar_puntos()
    pts  = data.get(str(member.id), {"total": 0.0, "semana": 0.0, "evidencias": 0})
    e = discord.Embed(color=COLOR_GOLD, timestamp=datetime.datetime.now())
    e.set_author(name="Sistema de Puntos  ✦  NightMc Network",
                 icon_url=guild.icon.url if guild.icon else None)
    e.title = f"📊  Puntos — {member.display_name}"
    e.set_thumbnail(url=member.display_avatar.url)
    e.description = SEP
    e.add_field(name="⭐  Esta semana", value=f"`{pts['semana']:.1f} pts`",    inline=True)
    e.add_field(name="🏆  Total",       value=f"`{pts['total']:.1f} pts`",     inline=True)
    e.add_field(name="📋  Evidencias",  value=f"`{pts['evidencias']}`",        inline=True)
    e.add_field(name=SEP, value="> 1 evidencia = **0.1 pts** · 10 evidencias = **1 pt**", inline=False)
    _footer(e, guild)
    return e

@bot.tree.command(name="puntos", description="Ver tus puntos de evidencias")
async def puntos_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not es_staff(interaction.user):
        return await interaction.followup.send("❌  Solo miembros del **Staff**.", ephemeral=True)
    e = await _embed_puntos(interaction.guild, interaction.user)
    await interaction.followup.send(embed=e, ephemeral=True)

@bot.command(name="puntos")
async def puntos_cmd(ctx):
    if not es_staff(ctx.author):
        return await ctx.send("❌  Solo miembros del **Staff**.")
    e = await _embed_puntos(ctx.guild, ctx.author)
    await ctx.send(embed=e)

async def _embed_ranking(guild: discord.Guild) -> discord.Embed:
    data     = _cargar_puntos()
    medallas = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    ranking  = sorted(
        [(uid, v) for uid, v in data.items() if v.get("semana", 0) > 0],
        key=lambda x: x[1]["semana"], reverse=True
    )
    e = discord.Embed(color=COLOR_GOLD, timestamp=datetime.datetime.now())
    e.set_author(name="Sistema de Puntos  ✦  NightMc Network",
                 icon_url=guild.icon.url if guild.icon else None)
    e.title = "🏆  Ranking Semanal de Puntos"
    if not ranking:
        e.description = f"{SEP}\n> Sin puntos registrados esta semana."
    else:
        lineas = []
        for i, (uid, v) in enumerate(ranking[:10]):
            m   = guild.get_member(int(uid))
            nom = m.display_name if m else f"<@{uid}>"
            med = medallas[i] if i < len(medallas) else f"`{i+1}.`"
            lineas.append(f"{med}  **{nom}** — `{v['semana']:.1f} pts` · `{v['evidencias']} evid.`")
        e.description = SEP + "\n" + "\n".join(lineas)
    _footer(e, guild)
    return e

@bot.tree.command(name="ps", description="Ranking de puntos de la semana")
async def ps_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not es_staff(interaction.user):
        return await interaction.followup.send("❌  Solo miembros del **Staff**.", ephemeral=True)
    e = await _embed_ranking(interaction.guild)
    await interaction.followup.send(embed=e, ephemeral=True)

@bot.command(name="ps")
async def ps_cmd(ctx):
    if not es_staff(ctx.author):
        return await ctx.send("❌  Solo miembros del **Staff**.")
    e = await _embed_ranking(ctx.guild)
    await ctx.send(embed=e)

@bot.tree.command(name="rp", description="Reinicia los puntos semanales y anuncia ganadores")
async def rp_slash(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not es_head(interaction.user):
        return await interaction.followup.send("❌  Solo **Head staff**.", ephemeral=True)
    await _reiniciar_semana(interaction.guild, interaction.user)
    await interaction.followup.send("✅  Semana reiniciada y publicada.", ephemeral=True)

@bot.command(name="rp")
async def rp_cmd(ctx):
    if not es_head(ctx.author):
        return await ctx.send("❌  Solo **Head staff**.")
    await _reiniciar_semana(ctx.guild, ctx.author)
    await ctx.send("✅  Semana reiniciada y publicada.")

async def _gestionar_sotw(guild: discord.Guild, top1: discord.Member):
    sotw_data = _cargar_sotw()
    rol_sotw = discord.utils.get(guild.roles, name=ROL_SOTW)
    rol_sotm = discord.utils.get(guild.roles, name=ROL_SOTM)

    if not rol_sotw:
        return

    uid_nuevo   = str(top1.id)
    uid_actual  = sotw_data.get("current_sotw")
    semanas_top = sotw_data.get("semanas", {})

    semanas_top[uid_nuevo] = semanas_top.get(uid_nuevo, 0) + 1

    if uid_actual and uid_actual != uid_nuevo:
        semanas_top[uid_actual] = 0
        anterior = guild.get_member(int(uid_actual))
        if anterior and rol_sotw in anterior.roles:
            try: await anterior.remove_roles(rol_sotw, reason="Nuevo SOTW esta semana")
            except Exception: pass

    if rol_sotw not in top1.roles:
        try: await top1.add_roles(rol_sotw, reason="SOTW de la semana")
        except Exception: pass

    sotw_data["current_sotw"] = uid_nuevo
    sotw_data["semanas"]      = semanas_top

    if semanas_top.get(uid_nuevo, 0) >= 4:
        try: await top1.remove_roles(rol_sotw, reason="Ascendido a SOTM")
        except Exception: pass
        uid_sotm_actual = sotw_data.get("current_sotm")
        if uid_sotm_actual and uid_sotm_actual != uid_nuevo:
            anterior_sotm = guild.get_member(int(uid_sotm_actual))
            if anterior_sotm and rol_sotm and rol_sotm in anterior_sotm.roles:
                try: await anterior_sotm.remove_roles(rol_sotm, reason="Nuevo SOTM")
                except Exception: pass
        if rol_sotm:
            try: await top1.add_roles(rol_sotm, reason="SOTM del mes — 4 semanas como SOTW")
            except Exception: pass
        sotw_data["current_sotm"] = uid_nuevo
        sotw_data["current_sotw"] = None
        semanas_top[uid_nuevo]    = 0
        _guardar_sotw(sotw_data)
        return "sotm"

    _guardar_sotw(sotw_data)
    return "sotw"

async def _reiniciar_semana(guild: discord.Guild, reiniciado_por: discord.Member, test: bool = False):
    data    = _cargar_puntos()
    ranking = sorted(
        [(uid, v) for uid, v in data.items() if v.get("semana", 0) > 0],
        key=lambda x: x[1]["semana"], reverse=True
    )

    canal_pts = discord.utils.get(guild.text_channels, name=CANAL_PUNTOS)
    rol_staff = discord.utils.get(guild.roles, name=STAFF_TEAM)
    medallas  = ["🥇", "🥈", "🥉"]
    top3      = []
    ascendio_sotm = False

    lineas_ranking = []
    if ranking:
        for i, (uid, v) in enumerate(ranking[:10]):
            m   = guild.get_member(int(uid))
            nom = m.display_name if m else f"<@{uid}>"
            med = medallas[i] if i < len(medallas) else f"**{i+1}.**"
            lineas_ranking.append(
                f"{med}  {m.mention if m else nom}  ·  "
                f"`{v['semana']:.1f} pts`  ·  `{v['evidencias']} evid.`"
            )
            if i < 3 and m:
                top3.append(m)

    top1 = top3[0] if top3 else None
    if top1:
        resultado_sotw = await _gestionar_sotw(guild, top1)
        ascendio_sotm  = resultado_sotw == "sotm"

    for uid in data:
        data[uid]["semana"]     = 0.0
        data[uid]["evidencias"] = 0
    _guardar_puntos(data)

    if not canal_pts:
        return

    color = 0xf1c40f if not test else COLOR_BLUE
    e = discord.Embed(color=color, timestamp=datetime.datetime.now())
    e.set_author(
        name="NightMc Network  ✦  Cierre Semanal",
        icon_url=guild.icon.url if guild.icon else None
    )
    e.title = "🧪  [TEST] Cierre de Semana" if test else "🏆  Resultados de la Semana"
    staff_mention = rol_staff.mention if rol_staff else "@Staff team"

    desc = f"{staff_mention}\n{SEP}\n"

    if not top3:
        desc += "Sin actividad esta semana."
    else:
        menciones_str = "  ".join(m.mention for m in top3)
        desc += f"Los staff con más puntos esta semana son: {menciones_str}\n\n"
        if lineas_ranking:
            desc += "\n".join(lineas_ranking) + "\n"
        desc += f"\n{SEP}\n"
        if len(top3) >= 2:
            top2_3_str = " y ".join(m.mention for m in top3[1:])
            desc += f"Quería agradecer a {top2_3_str} por el gran trabajo que han hecho esta semana.\n\n"
        if top1:
            if ascendio_sotm:
                desc += (
                    f"🏅  **Staff of the Month**\n"
                    f"{top1.mention} lleva **4 semanas seguidas** en el top 1. "
                    f"¡Felicidades, has sido ascendido a **SOTM**! 🎉\n"
                )
            else:
                semanas = _cargar_sotw().get("semanas", {}).get(str(top1.id), 1)
                semanas_txt = f" *(Semana {semanas}/4 para SOTM)*" if semanas > 1 else ""
                desc += (
                    f"⭐  **SOTW — Staff of the Week**\n"
                    f"Felicidades {top1.mention}, muchas gracias por esa actividad 💪{semanas_txt}\n"
                )

    desc += f"\n{SEP}\n-# ♻️ Reiniciado por {reiniciado_por.display_name}"
    e.description = desc
    e.set_image(url=BANNER_STAFF)
    _footer(e, guild)

    await canal_pts.send(
        content=rol_staff.mention if rol_staff else "@Staff team",
        embed=e
    )

class ConfirmarResetPuntosView(ui.View):
    def __init__(self, staff: discord.Member, autor: discord.Member):
        super().__init__(timeout=30)
        self.staff = staff
        self.autor = autor

    @ui.button(label="Confirmar", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.autor.id:
            return await interaction.response.send_message(
                "❌  Solo quien ejecutó el comando.", ephemeral=True)
        data = _cargar_puntos()
        key  = str(self.staff.id)
        antes = data.get(key, {"total": 0.0, "semana": 0.0, "evidencias": 0})
        data[key] = {"total": 0.0, "semana": 0.0, "evidencias": 0}
        _guardar_puntos(data)
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(view=self)
        e = discord.Embed(color=COLOR_OK, timestamp=datetime.datetime.now())
        e.title = "🗑️  Puntos Reseteados"
        e.description = (
            f"**👤  Staff:** {self.staff.mention}\n"
            f"**👮  Reseteado por:** {interaction.user.mention}\n"
            f"**📅  Fecha:** <t:{_now_ts()}:F>\n{SEP}\n"
            f"> Semana: `{antes['semana']:.1f} pts` → `0`\n"
            f"> Total: `{antes['total']:.1f} pts` → `0`\n"
            f"> Evidencias: `{antes['evidencias']}` → `0`"
        )
        _footer(e, interaction.guild)
        await interaction.followup.send(embed=e, ephemeral=True)

    @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.autor.id:
            return await interaction.response.send_message(
                "❌  Solo quien ejecutó el comando.", ephemeral=True)
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("❌  Cancelado.", ephemeral=True)

@bot.tree.command(name="resetear_puntos", description="Resetea los puntos de un staff específico")
@discord.app_commands.describe(staff="Staff al que resetear los puntos")
async def resetear_puntos_slash(interaction: discord.Interaction, staff: discord.Member):
    if not es_head(interaction.user):
        return await interaction.response.send_message(
            "❌  Solo **Head staff**.", ephemeral=True)
    data = _cargar_puntos()
    pts  = data.get(str(staff.id), {"total": 0.0, "semana": 0.0, "evidencias": 0})
    e = discord.Embed(color=COLOR_WARN)
    e.title = "⚠️  Confirmar reset de puntos"
    e.description = (
        f"¿Resetear **todos** los puntos de {staff.mention}?\n\n"
        f"⭐  Semana: `{pts['semana']:.1f} pts`\n"
        f"🏆  Total: `{pts['total']:.1f} pts`\n"
        f"📋  Evidencias: `{pts['evidencias']}`\n\n"
        f"*Esta acción no se puede deshacer.*"
    )
    _footer(e, interaction.guild)
    await interaction.response.send_message(
        embed=e, view=ConfirmarResetPuntosView(staff, interaction.user), ephemeral=True)

# ╔═══════════════════════════════════════════════════════════════╗
#   🏅  COMANDOS DE RACHAS                              (NUEVO)
# ╚═══════════════════════════════════════════════════════════════╝
async def _embed_rachas_ranking(guild: discord.Guild) -> discord.Embed:
    data     = _cargar_rachas()
    medallas = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

    ranking = sorted(
        [(uid, v) for uid, v in data.items() if v.get("racha", 0) > 0],
        key=lambda x: x[1]["racha"], reverse=True
    )

    e = discord.Embed(color=COLOR_PURPLE, timestamp=datetime.datetime.now())
    e.set_author(name="Sistema de Rachas  ✦  NightMc Network",
                 icon_url=guild.icon.url if guild.icon else None)
    e.title = "🏅  Ranking de Rachas — Staff Activo"

    if not ranking:
        e.description = f"{SEP}\n> Nadie tiene racha activa actualmente."
    else:
        lineas = []
        for i, (uid, v) in enumerate(ranking[:10]):
            m   = guild.get_member(int(uid))
            if not m: continue
            med = medallas[i] if i < len(medallas) else f"`{i+1}.`"
            emoji = _emoji_racha(v["racha"])
            lineas.append(
                f"{med}  {m.mention}  —  "
                f"{emoji} **{v['racha']} días**  ·  "
                f"máx `{v.get('max_racha', v['racha'])} días`"
            )
        e.description = SEP + "\n" + ("\n".join(lineas) if lineas else "> Sin datos.")

    e.add_field(
        name="ℹ️  Leyenda",
        value=(
            "> 📅 1-2 días  ·  ⚡ 3-6 días  ·  🔥 7-13 días\n"
            "> 💎 14-29 días  ·  🔱 30+ días"
        ),
        inline=False
    )
    _footer(e, guild)
    return e

@bot.tree.command(name="rachas", description="Ver el ranking de rachas de actividad del staff")
async def rachas_slash(interaction: discord.Interaction):
    if not es_staff(interaction.user):
        return await interaction.response.send_message(
            "❌  Solo miembros del **Staff**.", ephemeral=True)
    await interaction.response.defer(ephemeral=False)
    e = await _embed_rachas_ranking(interaction.guild)
    await interaction.followup.send(embed=e)

@bot.command(name="rachas")
async def rachas_cmd(ctx):
    if not es_staff(ctx.author):
        return await ctx.send("❌  Solo miembros del **Staff**.")
    e = await _embed_rachas_ranking(ctx.guild)
    await ctx.send(embed=e)

@bot.tree.command(name="mi_racha", description="Ver tu racha personal de actividad")
async def mi_racha_slash(interaction: discord.Interaction):
    if not es_staff(interaction.user):
        return await interaction.response.send_message(
            "❌  Solo miembros del **Staff**.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    data = _cargar_rachas()
    r    = _get_racha(data, interaction.user.id)
    emoji = _emoji_racha(r["racha"])

    e = discord.Embed(color=COLOR_PURPLE, timestamp=datetime.datetime.now())
    e.set_author(name="Sistema de Rachas  ✦  NightMc Network",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    e.title = f"{emoji}  Mi Racha — {interaction.user.display_name}"
    e.set_thumbnail(url=interaction.user.display_avatar.url)
    e.description = SEP
    e.add_field(name=f"{emoji}  Racha actual",  value=f"**{r['racha']} días**",           inline=True)
    e.add_field(name="🏆  Racha máxima",        value=f"`{r.get('max_racha', 0)} días`",   inline=True)
    e.add_field(name="📅  Total días activo",    value=f"`{r.get('total_dias', 0)} días`",  inline=True)
    e.add_field(name="📋  Último día activo",    value=f"`{r['ultimo_dia'] or 'Nunca'}`",  inline=False)

    # Próximo hito
    hitos = [3, 7, 14, 30]
    prox  = next((h for h in hitos if h > r["racha"]), None)
    if prox:
        falta = prox - r["racha"]
        e.add_field(name="🎯  Próximo hito",
                    value=f"`{prox} días` — faltan **{falta} día{'s' if falta != 1 else ''}**",
                    inline=False)
    _footer(e, interaction.guild)
    await interaction.followup.send(embed=e, ephemeral=True)

@bot.command(name="mi_racha")
async def mi_racha_cmd(ctx):
    if not es_staff(ctx.author):
        return await ctx.send("❌  Solo miembros del **Staff**.")
    data = _cargar_rachas()
    r    = _get_racha(data, ctx.author.id)
    emoji = _emoji_racha(r["racha"])

    e = discord.Embed(color=COLOR_PURPLE, timestamp=datetime.datetime.now())
    e.set_author(name="Sistema de Rachas  ✦  NightMc Network",
                 icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    e.title = f"{emoji}  Mi Racha — {ctx.author.display_name}"
    e.set_thumbnail(url=ctx.author.display_avatar.url)
    e.description = SEP
    e.add_field(name=f"{emoji}  Racha actual",  value=f"**{r['racha']} días**",           inline=True)
    e.add_field(name="🏆  Racha máxima",        value=f"`{r.get('max_racha', 0)} días`",   inline=True)
    e.add_field(name="📅  Total días activo",    value=f"`{r.get('total_dias', 0)} días`",  inline=True)
    hitos = [3, 7, 14, 30]
    prox  = next((h for h in hitos if h > r["racha"]), None)
    if prox:
        falta = prox - r["racha"]
        e.add_field(name="🎯  Próximo hito",
                    value=f"`{prox} días` — faltan **{falta} día{'s' if falta != 1 else ''}**",
                    inline=False)
    _footer(e, ctx.guild)
    await ctx.send(embed=e)

# ╔═══════════════════════════════════════════════════════════════╗
#   ⏰  LOOP DIARIO — REVISAR RACHAS ROTAS               (NUEVO)
# ╚═══════════════════════════════════════════════════════════════╝
@tasks.loop(hours=24)
async def _check_rachas_diario():
    """
    Corre cada 24h. Para cada staff con racha activa, si su último día
    no es hoy ni ayer → racha rota. Notifica en el canal y por DM.
    """
    await bot.wait_until_ready()
    hoy  = _hoy()
    ayer = _ayer()
    data = _cargar_rachas()

    for guild in bot.guilds:
        canal_r   = discord.utils.get(guild.text_channels, name=CANAL_RACHAS)
        rol_staff = discord.utils.get(guild.roles, name=STAFF_TEAM)

        for uid_str, r in list(data.items()):
            racha_actual = r.get("racha", 0)
            ultimo_dia   = r.get("ultimo_dia", "")

            if racha_actual <= 0:
                continue
            if ultimo_dia in (hoy, ayer):
                continue  # Sigue activo

            # Racha rota
            racha_guardada = racha_actual
            r["racha"] = 0
            data[uid_str] = r

            miembro = guild.get_member(int(uid_str))
            if not miembro:
                continue

            # Notificar en canal de rachas
            if canal_r:
                e = discord.Embed(color=COLOR_DANGER, timestamp=datetime.datetime.now())
                e.set_author(name="Sistema de Rachas  ✦  NightMc Network",
                             icon_url=guild.icon.url if guild.icon else None)
                e.title = "💔  Racha rota"
                e.description = (
                    f"{miembro.mention} perdió su racha de **{racha_guardada} días** "
                    f"por no subir evidencias ayer.\n"
                    f"> Su racha vuelve a **0**. ¡A empezar de nuevo! 💪"
                )
                e.set_thumbnail(url=miembro.display_avatar.url)
                e.set_footer(text=FOOTER)
                try: await canal_r.send(embed=e)
                except Exception: pass

            # DM al miembro
            try:
                dm = discord.Embed(color=COLOR_DANGER)
                dm.title = "💔  Perdiste tu racha"
                dm.description = (
                    f"Tu racha de **{racha_guardada} días consecutivos** se rompió "
                    f"porque no subiste ninguna evidencia ayer.\n\n"
                    f"> Vuelve al canal de bans y empieza de nuevo. ¡Tú puedes! 💪"
                )
                dm.set_footer(text=FOOTER)
                await miembro.send(embed=dm)
            except discord.Forbidden:
                pass

    _guardar_rachas(data)

# ╔═══════════════════════════════════════════════════════════════╗
#   🕐  LOOP INACTIVIDAD (del código original)
# ╚═══════════════════════════════════════════════════════════════╝
DIAS_SIN_EVIDENCIA = 4
HORAS_ENTRE_AVISOS = 24
INACTIVIDAD_FILE   = "inactividad_avisos.json"

def _cargar_avisos() -> dict: return _load(INACTIVIDAD_FILE)
def _guardar_avisos(d):       _save(INACTIVIDAD_FILE, d)

async def _aviso_en_inactividad(canal_inac, miembro: discord.Member) -> bool:
    if not canal_inac:
        return False
    limite = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    try:
        async for msg in canal_inac.history(limit=200, after=limite):
            if msg.author.id == miembro.id:
                return True
    except (discord.Forbidden, discord.HTTPException):
        pass
    return False

def _build_dm_inactividad(guild, miembro, horas_sin, canal_inac, test=False):
    dm = discord.Embed(color=0x5865f2, timestamp=datetime.datetime.now())
    dm.set_author(name="NightMc Network  ✦  Staff Team",
                  icon_url=guild.icon.url if guild.icon else None)
    dm.set_thumbnail(url=miembro.display_avatar.url)
    dm.title = "👋  Un recordatorio del Staff Team"
    horas_int = int(horas_sin)
    if horas_int >= 24:
        tiempo_str = f"**{horas_int // 24} día{'s' if horas_int // 24 != 1 else ''}**"
    else:
        tiempo_str = f"**{horas_int} hora{'s' if horas_int != 1 else ''}**"
    inac_ref = canal_inac.mention if canal_inac else f"#{CANAL_INACTIVIDAD}"
    dm.description = (
        f"{miembro.mention}, notamos que llevas {tiempo_str} "
        f"sin subir evidencias al canal de bans.\n{SEP}"
    )
    dm.add_field(name="📋  ¿Qué hacer?", value=(
        f"> Si estás **inactivo o ausente**, avísalo en {inac_ref}.\n"
        f"> Si sigues activo, **sube evidencias** para no ser sancionado. 💪"
    ), inline=False)
    dm.add_field(name="💡  Recuerda", value=(
        "> La actividad es clave para mantener el servidor en orden.\n"
        "> Si ya avisaste tu inactividad, ignora este mensaje. 😊"
    ), inline=False)
    footer_txt = ("[MODO TEST]  ✦  " if test else "Mensaje automático  ✦  ") + FOOTER
    dm.set_footer(text=footer_txt)
    return dm

@tasks.loop(hours=24)
async def _recordatorio_inactividad():
    await bot.wait_until_ready()
    ahora  = datetime.datetime.now().timestamp()
    puntos = _cargar_puntos()
    avisos = _cargar_avisos()

    for guild in bot.guilds:
        rol_staff_team = discord.utils.get(guild.roles, name=STAFF_TEAM)
        if not rol_staff_team:
            continue
        canal_inac = discord.utils.get(guild.text_channels, name=CANAL_INACTIVIDAD)

        for miembro in rol_staff_team.members:
            if miembro.bot: continue
            key = str(miembro.id)
            if key not in puntos:
                puntos[key] = {"total": 0.0, "semana": 0.0, "evidencias": 0, "ultima_evidencia": ahora}
                continue
            ultima    = puntos[key].get("ultima_evidencia", ahora)
            horas_sin = (ahora - ultima) / 3600
            if horas_sin < (DIAS_SIN_EVIDENCIA * 24): continue
            ultimo_aviso = avisos.get(key, 0)
            if (ahora - ultimo_aviso) < (HORAS_ENTRE_AVISOS * 3600): continue
            ya_aviso = await _aviso_en_inactividad(canal_inac, miembro)
            if ya_aviso: continue
            try:
                dm = _build_dm_inactividad(guild, miembro, horas_sin, canal_inac)
                await miembro.send(embed=dm)
                avisos[key] = ahora
            except discord.Forbidden: pass

    _guardar_puntos(puntos)
    _guardar_avisos(avisos)

# ╔═══════════════════════════════════════════════════════════════╗
#   🧪  /tt — TEST DM inactividad
# ╚═══════════════════════════════════════════════════════════════╝
@bot.tree.command(name="tt", description="[TEST] Envía el DM de inactividad a un staff para probarlo")
@discord.app_commands.describe(staff="Staff al que enviar el DM de prueba")
async def tt_slash(interaction: discord.Interaction, staff: discord.Member):
    await interaction.response.defer(ephemeral=True)
    if not es_head(interaction.user):
        return await interaction.followup.send("❌  Solo **Head staff**.", ephemeral=True)
    guild      = interaction.guild
    canal_inac = discord.utils.get(guild.text_channels, name=CANAL_INACTIVIDAD)
    ya_aviso   = await _aviso_en_inactividad(canal_inac, staff)
    dm = _build_dm_inactividad(guild, staff, 24, canal_inac, test=True)
    if ya_aviso:
        dm.add_field(name="ℹ️  Info TEST",
                     value="> Este usuario **ya avisó** su inactividad. En modo normal **no** recibiría este DM.",
                     inline=False)
    try:
        await staff.send(embed=dm)
        aviso_txt = "  ⚠️  (Ya había avisado inactividad)" if ya_aviso else ""
        await interaction.followup.send(
            f"✅  DM de prueba enviado a {staff.mention}.{aviso_txt}", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send(
            f"❌  No se pudo enviar DM a {staff.mention} — tiene los DMs cerrados.", ephemeral=True)

# ╔═══════════════════════════════════════════════════════════════╗
#   🚀  EVENTOS DE ARRANQUE
# ╚═══════════════════════════════════════════════════════════════╝
@bot.event
async def on_ready():
    bot.add_view(AppealLauncher())
    bot.add_view(AppealControl())
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name="Staff NightMc ⚖️"))
    print(f"✦  Staff Bot v3.1 listo: {bot.user}")
    print(f"   Prefijo: st!  |  Usa st!sync para registrar slash commands")
    if not _recordatorio_inactividad.is_running():
        _recordatorio_inactividad.start()
    if not _check_rachas_diario.is_running():      # ← NUEVO
        _check_rachas_diario.start()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("❌  Sin permisos.")
    if isinstance(error, commands.CommandInvokeError):
        if isinstance(error.original, (discord.NotFound, discord.Forbidden)):
            return
    raise error

# ╔═══════════════════════════════════════════════════════════════╗
#   🚀  ARRANQUE SEGURO
# ╚═══════════════════════════════════════════════════════════════╝
def inicializar_archivos():
    """Asegura que los archivos necesarios existan para evitar errores."""
    for archivo in [SANCIONES_FILE, PUNTOS_FILE, REUNIONES_FILE]:
        if not os.path.exists(archivo):
            with open(archivo, "w", encoding='utf-8') as f:
                json.dump({}, f)
            print(f"📦 Archivo creado: {archivo}")

if __name__ == "__main__":
    inicializar_archivos()
    
    # Cargamos el token desde Railway o .env
    load_dotenv()
    token_final = os.getenv("DISCORD_TOKEN")

    if token_final:
        print("✅ Conectando con NightMC Network...")
        try:
            bot.run(token_final)
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
    else:
        print("❌ ERROR: No se encontró la variable DISCORD_TOKEN en Railway.")
        print("   → En local: crea un archivo .env con STAFF_TOKEN=tu_token")
