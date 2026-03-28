import discord
from discord.ext import commands
import datetime
import json
import os
import re
import pytz
from dotenv import load_dotenv

# ╔═══════════════════════════════════════════════════════════════╗
#   ⚙️  CONFIGURACIÓN
# ╚═══════════════════════════════════════════════════════════════╝
STAFF_TEAM        = "Staff team"
TODOS_ROLES_STAFF = ["Low staff", "Medium Staff", "Hight staff", "Head staff", "Staff team"]
ROLES_SUPERIORES  = ["Hight staff", "Head staff"]

SANCIONES_FILE      = "sanciones_data.json"
PUNTOS_FILE         = "puntos_data.json"
REUNIONES_FILE      = "reuniones_data.json"
SEMANA_ACTIVA_FILE  = "semana_activa.json"
SANCIONES_CANAL     = "sanciones"
CANAL_STRIKES       = "strikes"
CANAL_REUNIONES     = "💼│reuniones"
WARNS_PARA_STRIKE   = 3
STRIKES_PARA_DEMOTE = 3

# Zona horaria España
HORARIO_ESPAÑA = pytz.timezone("Europe/Madrid")

# Canales de puntos y sus valores
CANALES_PUNTOS = {
    "bans":      {"emoji": "🚫", "puntos": 3, "descripcion": "Ban aplicado"},
    "mutes-warns": {"emoji": "🔇", "puntos": 1, "descripcion": "Mute/Warn aplicado"},
    "tickets-dc": {"emoji": "🔗", "puntos": 2, "descripcion": "Ticket cerrado"},
    "revives":   {"emoji": "💀", "puntos": 4, "descripcion": "Revive realizado"},
    "trades":    {"emoji": "🤝", "puntos": 2, "descripcion": "Trade completado"},
    "helpops":   {"emoji": "⭐", "puntos": 1, "descripcion": "HelpOp atendido"},
}

# ╔═══════════════════════════════════════════════════════════════╗
#   🎨  ESTÉTICA
# ╚═══════════════════════════════════════════════════════════════╝
BANNER_URL   = "https://i.imgur.com/uhYEbZj.png"
COLOR_OK     = 0x57f287
COLOR_DANGER = 0xed4245
COLOR_WARN   = 0xfee75c
COLOR_BLUE   = 0x5865f2
COLOR_PURPLE = 0x9b59b6
COLOR_GOLD   = 0xf1c40f
FOOTER       = "NightMc.me"

# ╔═══════════════════════════════════════════════════════════════╗
#   🤖  BOT
# ╚═══════════════════════════════════════════════════════════════╝
class SancionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix="st!", intents=intents, help_command=None)

    async def setup_hook(self):
        print("✦  Bot de Staff listo. Usa st!sync para registrar los comandos slash.")

    async def on_ready(self):
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching, name="Staff NightMc ⚖️"))
        print(f"✦  Online  ·  {self.user}  ·  {self.user.id}")

bot = SancionBot()

# ╔═══════════════════════════════════════════════════════════════╗
#   🔧  UTILIDADES — GENERALES
# ╚═══════════════════════════════════════════════════════════════╝
def _es_superior(m: discord.Member) -> bool:
    return any(r.name in ROLES_SUPERIORES for r in m.roles)

def _es_head(m: discord.Member) -> bool:
    return any(r.name == "Head staff" for r in m.roles)

def _es_staff(m: discord.Member) -> bool:
    return any(r.name in TODOS_ROLES_STAFF for r in m.roles)

def es_domingo_espana() -> bool:
    ahora = datetime.datetime.now(HORARIO_ESPAÑA)
    return ahora.weekday() == 6

async def _resolver_miembro(ctx_or_guild, raw: str) -> discord.Member:
    guild = ctx_or_guild if isinstance(ctx_or_guild, discord.Guild) else ctx_or_guild.guild
    raw = raw.strip().strip("<@!>").strip("<@>")
    try:
        uid = int(raw)
        m = guild.get_member(uid)
        if m: return m
        m = await guild.fetch_member(uid)
        if m: return m
    except (ValueError, discord.NotFound):
        pass
    raw_lower = raw.lower()
    for m in guild.members:
        if m.name.lower() == raw_lower or m.display_name.lower() == raw_lower:
            return m
    return None

# ╔═══════════════════════════════════════════════════════════════╗
#   💾  SANCIONES — DATA
# ╚═══════════════════════════════════════════════════════════════╝
def _cargar_datos() -> dict:
    if os.path.exists(SANCIONES_FILE):
        try:
            with open(SANCIONES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _guardar_datos(data: dict):
    with open(SANCIONES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _get_staff_data(data: dict, uid: int) -> dict:
    key = str(uid)
    if key not in data:
        data[key] = {"warns": [], "strikes": []}
    return data[key]

# ╔═══════════════════════════════════════════════════════════════╗
#   💾  PUNTOS — DATA
# ╚═══════════════════════════════════════════════════════════════╝
def _cargar_puntos() -> dict:
    if os.path.exists(PUNTOS_FILE):
        try:
            with open(PUNTOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _guardar_puntos(data: dict):
    with open(PUNTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _get_puntos_data(data: dict, uid: int) -> dict:
    key = str(uid)
    if key not in data:
        data[key] = {
            "total": 0,
            "weekly": 0,
            "historial": [],
            "por_canal": {c: 0 for c in CANALES_PUNTOS}
        }
    for c in CANALES_PUNTOS:
        data[key]["por_canal"].setdefault(c, 0)
    data[key].setdefault("weekly", 0)
    return data[key]

# ╔═══════════════════════════════════════════════════════════════╗
#   💾  SEMANA ACTIVA — DATA
# ╚═══════════════════════════════════════════════════════════════╝
def _cargar_semana_activa() -> dict:
    if os.path.exists(SEMANA_ACTIVA_FILE):
        try:
            with open(SEMANA_ACTIVA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"activa": False, "inicio": None, "id_semana": 0}

def _guardar_semana_activa(data: dict):
    with open(SEMANA_ACTIVA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ╔═══════════════════════════════════════════════════════════════╗
#   💾  REUNIONES — DATA
# ╚═══════════════════════════════════════════════════════════════╝
def _cargar_reuniones() -> dict:
    if os.path.exists(REUNIONES_FILE):
        try:
            with open(REUNIONES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"contador": 0, "reuniones": []}

def _guardar_reuniones(data: dict):
    with open(REUNIONES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ╔═══════════════════════════════════════════════════════════════╗
#   📺  CANALES — HELPERS
# ╚═══════════════════════════════════════════════════════════════╝
async def _get_o_crear_canal(guild: discord.Guild, nombre: str, categoria_nombre: str = "📋 LOGS"):
    c = discord.utils.get(guild.text_channels, name=nombre)
    if c:
        return c
    try:
        cat = discord.utils.get(guild.categories, name=categoria_nombre)
        if not cat:
            cat = await guild.create_category(categoria_nombre)
        rol_st = discord.utils.get(guild.roles, name=STAFF_TEAM)
        perms = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me:           discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if rol_st:
            perms[rol_st] = discord.PermissionOverwrite(read_messages=True, send_messages=False)
        return await guild.create_text_channel(nombre, category=cat, overwrites=perms)
    except Exception:
        return None

async def _get_sanciones_canal(guild):
    return await _get_o_crear_canal(guild, SANCIONES_CANAL)

async def _get_canal_strikes(guild):
    return await _get_o_crear_canal(guild, CANAL_STRIKES)

# ╔═══════════════════════════════════════════════════════════════╗
#   📊  EMBED — HISTORIAL SANCIONES
# ╚═══════════════════════════════════════════════════════════════╝
def _build_historial_embed(miembro, sd, guild):
    e = discord.Embed(title="📋  Historial — " + miembro.display_name,
                      color=COLOR_BLUE, timestamp=datetime.datetime.now())
    e.set_author(name="Sistema de Sanciones — NightMc Network",
                 icon_url=guild.icon.url if guild.icon else None)
    e.set_thumbnail(url=miembro.display_avatar.url)
    e.add_field(name="⚠️  Warns",   value="`" + str(len(sd["warns"])) + "/3`",   inline=True)
    e.add_field(name="💥  Strikes", value="`" + str(len(sd["strikes"])) + "/3`", inline=True)
    e.add_field(name="\u200b", value="\u200b", inline=False)
    if sd["warns"]:
        t = ""
        for i, w in enumerate(sd["warns"][-5:], 1):
            t += "`" + str(i) + ".` " + w["fecha"] + " — " + w["motivo"] + "\n"
        e.add_field(name="📄  Últimos warns", value=t, inline=False)
    if sd["strikes"]:
        t = ""
        for i, s in enumerate(sd["strikes"][-5:], 1):
            t += "`" + str(i) + ".` " + s["fecha"] + " — " + s["motivo"] + "\n"
        e.add_field(name="📄  Últimos strikes", value=t, inline=False)
    if not sd["warns"] and not sd["strikes"]:
        e.description = "✅  Sin sanciones registradas."
    e.set_footer(text=FOOTER)
    return e

# ╔═══════════════════════════════════════════════════════════════╗
#   🚨  NOTIFICACIÓN STRIKE / DEMOTE
# ╚═══════════════════════════════════════════════════════════════╝
async def _notificar_strike(guild, miembro, sd, canal_s, motivo, demote=False):
    total_strikes = len(sd["strikes"])
    rol_head = discord.utils.get(guild.roles, name="Head staff")

    if demote:
        kick_ok = False
        try:
            await miembro.kick(reason=f"3 strikes acumulados — {motivo}")
            kick_ok = True
        except Exception:
            pass

        kick_txt = ("✅  El miembro fue **expulsado del servidor** automáticamente."
                    if kick_ok else
                    "⚠️  No se pudo expulsar (sube el rol del bot). Acción manual requerida.")

        e = discord.Embed(
            title="🚨  ALERTA — 3 STRIKES ACUMULADOS",
            description=(
                miembro.mention + " ha acumulado **" + str(total_strikes) + " strike(s)**.\n\n"
                "⚠️  Según las normas del staff, corresponde evaluar un **demote**.\n"
                "Un miembro de **Head staff** debe revisar este caso.\n\n" + kick_txt
            ),
            color=COLOR_DANGER, timestamp=datetime.datetime.now()
        )
        e.set_thumbnail(url=miembro.display_avatar.url)
        e.add_field(name="📋  Último motivo", value=f"```{motivo}```", inline=False)
        e.set_footer(text=FOOTER)
        mention = rol_head.mention if rol_head else "@Head staff"
        if canal_s:
            await canal_s.send(content=f"{mention} — Revisión requerida.", embed=e)
    else:
        e = discord.Embed(
            title="💥  Strike automático por warns",
            description=(
                miembro.mention + " acumuló **3 warns** → **+1 Strike automático**.\n"
                "Strikes totales: **" + str(len(sd["strikes"])) + "**"
            ),
            color=COLOR_DANGER, timestamp=datetime.datetime.now()
        )
        e.set_footer(text=FOOTER)
        if canal_s:
            await canal_s.send(embed=e)

# ╔═══════════════════════════════════════════════════════════════╗
#   🏆  SISTEMA DE PUNTOS — DETECCIÓN AUTOMÁTICA
# ╚═══════════════════════════════════════════════════════════════╝
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    reactor = guild.get_member(payload.user_id)
    if not reactor:
        return

    if not (reactor.bot or _es_superior(reactor)):
        return

    if str(payload.emoji) != "✅":
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel:
        return

    canal_key = None
    for key in CANALES_PUNTOS:
        if key in channel.name:
            canal_key = key
            break
    if not canal_key:
        return

    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception:
        return

    if message.author.bot:
        return

    autor = guild.get_member(message.author.id)
    if not autor or not _es_staff(autor):
        return

    # Verificar si la semana está activa
    data_semana = _cargar_semana_activa()
    if not data_semana["activa"]:
        return

    puntos_base = CANALES_PUNTOS[canal_key]["puntos"]
    multiplicador = 2 if es_domingo_espana() else 1
    puntos_a_dar = puntos_base * multiplicador

    data = _cargar_puntos()
    pd = _get_puntos_data(data, autor.id)
    pd["total"] += puntos_a_dar
    pd["weekly"] += puntos_a_dar
    pd["por_canal"][canal_key] = pd["por_canal"].get(canal_key, 0) + puntos_a_dar
    pd["historial"].append({
        "canal":  canal_key,
        "puntos": puntos_a_dar,
        "fecha":  datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "msg_id": str(payload.message_id)
    })
    _guardar_puntos(data)
    print(f"[puntos] +{puntos_a_dar} a {autor} en #{canal_key} (semanal: {pd['weekly']})")

# ╔═══════════════════════════════════════════════════════════════╗
#   📊  COMANDOS DE PUNTOS
# ╚═══════════════════════════════════════════════════════════════╝
@bot.tree.command(name="puntos", description="Muestra los puntos de un staff")
@discord.app_commands.describe(miembro="Staff a consultar (opcional)")
async def puntos_slash(interaction: discord.Interaction, miembro: discord.Member = None):
    if not _es_staff(interaction.user):
        return await interaction.response.send_message("❌  Solo staff puede usar este comando.", ephemeral=True)

    await interaction.response.defer()
    data = _cargar_puntos()

    if miembro:
        if not _es_staff(miembro):
            return await interaction.followup.send("❌  Ese usuario no es staff.", ephemeral=True)
        pd = _get_puntos_data(data, miembro.id)
        e = discord.Embed(title="🏆  Puntos — " + miembro.display_name, color=COLOR_GOLD)
        e.set_thumbnail(url=miembro.display_avatar.url)
        e.add_field(name="⭐  Total", value=f"**{pd['total']} pts**", inline=True)
        e.add_field(name="📅  Semanal", value=f"**{pd['weekly']} pts**", inline=True)
        e.add_field(name="\u200b", value="\u200b", inline=False)
        
        desglose = ""
        for canal_key, info in CANALES_PUNTOS.items():
            pts = pd["por_canal"].get(canal_key, 0)
            desglose += f"{info['emoji']}  **#{canal_key}** → `{pts} pts`\n"
        e.add_field(name="📊  Desglose por canal", value=desglose, inline=False)
        
        if pd["historial"]:
            ult = pd["historial"][-5:][::-1]
            txt = ""
            for h in ult:
                txt += f"`{h['fecha']}` · #{h['canal']} · **+{h['puntos']}**\n"
            e.add_field(name="🕒  Últimas actividades", value=txt, inline=False)
        e.set_footer(text=FOOTER)
        return await interaction.followup.send(embed=e)

    # Si no hay miembro, mostrar los propios puntos
    pd = _get_puntos_data(data, interaction.user.id)
    e = discord.Embed(title="🏆  Tus Puntos", color=COLOR_GOLD)
    e.add_field(name="⭐  Total", value=f"**{pd['total']} pts**", inline=True)
    e.add_field(name="📅  Semanal", value=f"**{pd['weekly']} pts**", inline=True)
    e.set_footer(text=FOOTER)
    await interaction.followup.send(embed=e)

@bot.tree.command(name="ps", description="Muestra el ranking semanal de puntos")
async def ranking_semanal_slash(interaction: discord.Interaction):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)

    data_semana = _cargar_semana_activa()
    if not data_semana["activa"]:
        return await interaction.response.send_message("⚠️  No hay semana activa.", ephemeral=True)

    puntos_data = _cargar_puntos()
    ranking = []
    for uid_str, pd in puntos_data.items():
        if pd["weekly"] > 0:
            miembro = interaction.guild.get_member(int(uid_str))
            if miembro and _es_staff(miembro):
                ranking.append((miembro, pd["weekly"]))

    ranking.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title=f"📊  Ranking semanal #{data_semana['id_semana']}",
        color=COLOR_GOLD
    )
    if not ranking:
        embed.description = "Aún no hay puntos esta semana."
    else:
        txt = ""
        medallas = ["🥇", "🥈", "🥉"]
        for i, (m, pts) in enumerate(ranking[:10]):
            med = medallas[i] if i < 3 else f"`{i+1}.`"
            txt += f"{med}  {m.mention}  —  **{pts} pts**\n"
        embed.description = txt
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="iniciar_semana", description="Inicia una nueva semana de puntos")
async def iniciar_semana_slash(interaction: discord.Interaction):
    if not _es_head(interaction.user):
        return await interaction.response.send_message("❌  Solo Head staff puede iniciar la semana.", ephemeral=True)

    data_semana = _cargar_semana_activa()
    if data_semana["activa"]:
        return await interaction.response.send_message("⚠️  Ya hay una semana activa. Ciérrala primero con `/cerrar_semana`.", ephemeral=True)

    puntos_data = _cargar_puntos()
    for uid_str, pd in puntos_data.items():
        pd["weekly"] = 0
    _guardar_puntos(puntos_data)

    data_semana["activa"] = True
    data_semana["inicio"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_semana["id_semana"] = data_semana.get("id_semana", 0) + 1
    _guardar_semana_activa(data_semana)

    embed = discord.Embed(
        title="📅  Semana de puntos iniciada",
        description=f"La semana **#{data_semana['id_semana']}** ha comenzado.\nSe empezarán a contar los puntos de los staff.",
        color=COLOR_OK
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cerrar_semana", description="Cierra la semana actual y anuncia el ganador")
async def cerrar_semana_slash(interaction: discord.Interaction):
    if not _es_head(interaction.user):
        return await interaction.response.send_message("❌  Solo Head staff puede cerrar la semana.", ephemeral=True)

    data_semana = _cargar_semana_activa()
    if not data_semana["activa"]:
        return await interaction.response.send_message("⚠️  No hay una semana activa.", ephemeral=True)

    puntos_data = _cargar_puntos()
    ranking = []
    for uid_str, pd in puntos_data.items():
        if pd["weekly"] > 0:
            miembro = interaction.guild.get_member(int(uid_str))
            if miembro and _es_staff(miembro):
                ranking.append((miembro, pd["weekly"]))

    ranking.sort(key=lambda x: x[1], reverse=True)

    if ranking:
        ganador, puntos = ranking[0]
        embed = discord.Embed(
            title="🏆  Semana cerrada",
            description=f"La semana **#{data_semana['id_semana']}** ha finalizado.\n\n🥇 **Ganador:** {ganador.mention} con **{puntos} puntos**.",
            color=COLOR_GOLD
        )
    else:
        embed = discord.Embed(
            title="🏆  Semana cerrada",
            description="No hubo puntos acumulados esta semana.",
            color=COLOR_WARN
        )

    for pd in puntos_data.values():
        pd["weekly"] = 0
    _guardar_puntos(puntos_data)

    data_semana["activa"] = False
    _guardar_semana_activa(data_semana)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="puntos-reset", description="Resetea los puntos de un miembro del staff")
@discord.app_commands.describe(miembro="Miembro a resetear")
async def puntos_reset_slash(interaction: discord.Interaction, miembro: discord.Member):
    if not _es_head(interaction.user):
        return await interaction.response.send_message("❌  Solo Head staff puede resetear puntos.", ephemeral=True)
    
    data = _cargar_puntos()
    key = str(miembro.id)
    if key in data:
        data[key] = {"total": 0, "weekly": 0, "historial": [], "por_canal": {c: 0 for c in CANALES_PUNTOS}}
        _guardar_puntos(data)
        await interaction.response.send_message(f"✅  Puntos de {miembro.mention} reseteados.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌  {miembro.mention} no tiene puntos registrados.", ephemeral=True)

# ╔═══════════════════════════════════════════════════════════════╗
#   ⏱️  SISTEMA DE INACTIVIDAD
# ╚═══════════════════════════════════════════════════════════════╝
@bot.tree.command(name="inactividad", description="Consulta el tiempo sin mensajes de un staff")
@discord.app_commands.describe(
    opcion="1: global | 2: por canal/categoría | 3: top inactivos",
    miembro="Miembro a consultar (opcional, solo para opciones 1 y 2)",
    canal="Canal o categoría (para opción 2)",
)
async def inactividad_slash(
    interaction: discord.Interaction,
    opcion: int,
    miembro: discord.Member = None,
    canal: str = None
):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)

    await interaction.response.defer()

    if opcion == 1:
        if not miembro:
            return await interaction.followup.send("❌  Debes especificar un miembro para la opción 1.")
        
        if not _es_staff(miembro):
            return await interaction.followup.send("❌  Ese usuario no es staff.")
        
        ultimo_msg = None
        for channel in interaction.guild.text_channels:
            try:
                async for msg in channel.history(limit=1):
                    if msg.author == miembro:
                        if ultimo_msg is None or msg.created_at > ultimo_msg:
                            ultimo_msg = msg.created_at
                        break
            except:
                continue
        
        if ultimo_msg is None:
            desc = f"{miembro.mention} no ha enviado ningún mensaje reciente."
        else:
            delta = datetime.datetime.now() - ultimo_msg
            dias = delta.days
            horas = delta.seconds // 3600
            minutos = (delta.seconds % 3600) // 60
            desc = f"{miembro.mention} ha estado inactivo por **{dias} días, {horas} horas, {minutos} minutos**."
        
        embed = discord.Embed(title="⏱️  Inactividad global", description=desc, color=COLOR_WARN)
        await interaction.followup.send(embed=embed)

    elif opcion == 2:
        if not miembro or not canal:
            return await interaction.followup.send("❌  Para opción 2 necesitas miembro y canal/categoría.")
        
        if not _es_staff(miembro):
            return await interaction.followup.send("❌  Ese usuario no es staff.")
        
        target = discord.utils.get(interaction.guild.text_channels, name=canal)
        if not target:
            target = discord.utils.get(interaction.guild.categories, name=canal)
            if not target:
                return await interaction.followup.send(f"❌  No encontré el canal/categoría `{canal}`.")
        
        ultimo_msg = None
        if isinstance(target, discord.CategoryChannel):
            for ch in target.text_channels:
                try:
                    async for msg in ch.history(limit=1):
                        if msg.author == miembro:
                            if ultimo_msg is None or msg.created_at > ultimo_msg:
                                ultimo_msg = msg.created_at
                            break
                except:
                    continue
        else:
            try:
                async for msg in target.history(limit=1):
                    if msg.author == miembro:
                        ultimo_msg = msg.created_at
                        break
            except:
                pass
        
        if ultimo_msg is None:
            desc = f"{miembro.mention} no ha escrito en `{canal}` recientemente."
        else:
            delta = datetime.datetime.now() - ultimo_msg
            dias = delta.days
            horas = delta.seconds // 3600
            minutos = (delta.seconds % 3600) // 60
            desc = f"{miembro.mention} ha estado inactivo en `{canal}` por **{dias} días, {horas} horas, {minutos} minutos**."
        
        embed = discord.Embed(title="⏱️  Inactividad por canal", description=desc, color=COLOR_WARN)
        await interaction.followup.send(embed=embed)

    elif opcion == 3:
        staffs = [m for m in interaction.guild.members if _es_staff(m) and not m.bot]
        inactividad = []
        
        for s in staffs:
            ultimo_msg = None
            for channel in interaction.guild.text_channels:
                try:
                    async for msg in channel.history(limit=1):
                        if msg.author == s:
                            if ultimo_msg is None or msg.created_at > ultimo_msg:
                                ultimo_msg = msg.created_at
                            break
                except:
                    continue
            
            if ultimo_msg:
                delta = datetime.datetime.now() - ultimo_msg
                inactividad.append((s, delta))
            else:
                inactividad.append((s, datetime.timedelta(days=9999)))
        
        inactividad.sort(key=lambda x: x[1], reverse=True)
        top = inactividad[:5]
        
        desc = ""
        for i, (m, delta) in enumerate(top, 1):
            if delta.days == 9999:
                desc += f"**{i}.** {m.mention} → **Sin mensajes registrados**\n"
            else:
                dias = delta.days
                horas = delta.seconds // 3600
                minutos = (delta.seconds % 3600) // 60
                desc += f"**{i}.** {m.mention} → **{dias}d {horas}h {minutos}m**\n"
        
        embed = discord.Embed(title="⏱️  Top 5 staff más inactivos", description=desc, color=COLOR_WARN)
        await interaction.followup.send(embed=embed)

# ╔═══════════════════════════════════════════════════════════════╗
#   📅  SISTEMA DE REUNIONES
# ╚═══════════════════════════════════════════════════════════════╝
class AsistenciaView(discord.ui.View):
    def __init__(self, reunion_id: int):
        super().__init__(timeout=None)
        self.reunion_id = reunion_id

    @discord.ui.button(label="Asistiré puntualmente", emoji="✅",
                       style=discord.ButtonStyle.success, custom_id="asistir_puntual")
    async def asistir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._registrar_respuesta(interaction, "puntual", "✅  Confirmado — Asistirás puntualmente.")

    @discord.ui.button(label="Llegaré con retraso", emoji="⏰",
                       style=discord.ButtonStyle.secondary, custom_id="asistir_tarde")
    async def tarde(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._registrar_respuesta(interaction, "tarde", "⏰  Confirmado — Llegarás con retraso.")

    @discord.ui.button(label="No puedo asistir", emoji="❌",
                       style=discord.ButtonStyle.danger, custom_id="no_asistir")
    async def no_asistir(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._registrar_respuesta(interaction, "ausente", "❌  Registrado — No podrás asistir.")

    async def _registrar_respuesta(self, interaction: discord.Interaction, estado: str, msg: str):
        data = _cargar_reuniones()
        for r in data.get("reuniones", []):
            if r["id"] == self.reunion_id:
                uid = str(interaction.user.id)
                r.setdefault("asistencia", {})
                r["asistencia"][uid] = {
                    "estado": estado,
                    "nombre": interaction.user.display_name,
                    "fecha":  datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                }
                _guardar_reuniones(data)
                break
        await interaction.response.send_message(msg, ephemeral=True)

async def _ac_temas(interaction: discord.Interaction, current: str):
    temas = [
        "Infraestructura & Feedback",
        "Soporte & Discord",
        "Expansión & Roadmap",
        "Panel Abierto",
        "Normas internas del staff",
        "Revisión de sanciones",
        "Nuevas modalidades del server",
        "Rendimiento del equipo",
        "Anuncios importantes",
        "Revisión de tickets",
    ]
    return [discord.app_commands.Choice(name=t, value=t)
            for t in temas if current.lower() in t.lower()][:25]

@bot.tree.command(name="reunion", description="Convoca una reunión oficial del staff")
@discord.app_commands.describe(
    titulo="Título de la reunión",
    fecha="Fecha de la reunión",
    hora="Hora de la reunión en UTC",
    canal_voz="Canal de voz donde se hará la reunión",
    temas="Temas separados por |",
    descripcion="Descripción opcional",
    mencionar="Rol a mencionar (opcional)",
)
async def reunion_slash(
    interaction: discord.Interaction,
    titulo: str,
    fecha: str,
    hora: str,
    canal_voz: str,
    temas: str,
    descripcion: str = None,
    mencionar: str = None,
):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    timestamp_str = ""
    try:
        hm = hora.strip().split(":")
        h, m = int(hm[0]), int(hm[1])
        meses = {
            "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
            "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12
        }
        fecha_lower = fecha.lower()
        mes_num = 1
        dia_num = 1
        anio_num = datetime.datetime.now().year
        for mes_str, mes_n in meses.items():
            if mes_str in fecha_lower:
                mes_num = mes_n
                break
        nums = re.findall(r'\d+', fecha)
        if len(nums) >= 1:
            dia_num = int(nums[0])
        if len(nums) >= 2:
            anio_num = int(nums[-1]) if int(nums[-1]) > 100 else anio_num

        dt_utc = datetime.datetime(anio_num, mes_num, dia_num, h, m, 0,
                                   tzinfo=datetime.timezone.utc)
        unix = int(dt_utc.timestamp())
        timestamp_str = f"<t:{unix}:F>"
        timestamp_rel = f"<t:{unix}:R>"
    except Exception:
        timestamp_str = f"**{fecha}** a las **{hora} UTC**"
        timestamp_rel = ""

    lista_temas = [t.strip() for t in temas.split("|") if t.strip()]

    data_r = _cargar_reuniones()
    data_r["contador"] = data_r.get("contador", 0) + 1
    num = data_r["contador"]

    def _numero_ordinal(n: int) -> str:
        nombres = ["Primera","Segunda","Tercera","Cuarta","Quinta",
                   "Sexta","Séptima","Octava","Novena","Décima"]
        if 1 <= n <= 10:
            return nombres[n - 1]
        return f"{n}ª"

    num_texto = _numero_ordinal(num)

    canal_destino = None
    for ch in interaction.guild.text_channels:
        if "reuniones" in ch.name.lower():
            canal_destino = ch
            break
    if not canal_destino:
        canal_destino = interaction.channel

    rol_mencion = mencionar or STAFF_TEAM
    rol_obj = discord.utils.get(interaction.guild.roles, name=rol_mencion)
    mention_txt = rol_obj.mention if rol_obj else f"@{rol_mencion}"

    desc_base = descripcion or "Este encuentro es clave para alinear nuestros objetivos y compartir los avances de la network."

    temas_txt = ""
    emojis_temas = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, tema in enumerate(lista_temas):
        emoji = emojis_temas[i] if i < len(emojis_temas) else "▫️"
        temas_txt += f"{emoji}  **{tema}**\n"

    sep = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    e = discord.Embed(
        title=f"📋  NIGHTMC NETWORK — {titulo.upper()}",
        color=COLOR_PURPLE,
        timestamp=datetime.datetime.now()
    )
    e.set_author(
        name="NightMc Network — Convocatoria Oficial",
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None
    )

    e.description = (
        f"{mention_txt}\n\n"
        f"**{rol_mencion}**, se les convoca oficialmente a nuestra **{num_texto} Reunión** — *{titulo}*.\n"
        f"{desc_base}\n"
        f"¡Su participación es lo que hace grande a **NightMC**!\n\n"
        f"{sep}"
    )

    if temas_txt:
        e.add_field(name="📌  LO QUE VEREMOS ESE DÍA", value=temas_txt, inline=False)
        e.add_field(name="\u200b", value=sep, inline=False)

    datos_reunion = f"📅  **FECHA Y HORA:** {timestamp_str}\n"
    if timestamp_rel:
        datos_reunion += f"⏱️  **TIEMPO RESTANTE:** {timestamp_rel}\n"
    datos_reunion += f"🎙️  **CANAL:** {canal_voz}\n"
    e.add_field(name="🗓️  DATOS DE LA REUNIÓN", value=datos_reunion, inline=False)

    e.add_field(
        name="⚠️  AVISO IMPORTANTE",
        value="> Si por motivos de fuerza mayor no puedes asistir o llegarás tarde,\n> es **obligatorio** avisarlo en: 📬│inactividad",
        inline=False
    )
    e.add_field(name="\u200b", value=sep, inline=False)
    e.add_field(
        name="✅  ¿CONFIRMAS TU ASISTENCIA?",
        value="Usa los botones de abajo para confirmar.",
        inline=False
    )
    e.set_footer(text=f"Reunión #{num}  ✦  {FOOTER}  ✦  Convocada por {interaction.user.display_name}")

    reunion_obj = {
        "id":        num,
        "titulo":    titulo,
        "fecha":     fecha,
        "hora":      hora,
        "canal_voz": canal_voz,
        "temas":     lista_temas,
        "convocada_por": interaction.user.id,
        "convocada_en":  datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "asistencia": {}
    }
    data_r.setdefault("reuniones", []).append(reunion_obj)
    _guardar_reuniones(data_r)

    view = AsistenciaView(num)
    msg = await canal_destino.send(embed=e, view=view)

    await interaction.followup.send(
        f"✅  Reunión **#{num}** convocada en {canal_destino.mention}.", ephemeral=True)

@bot.tree.command(name="reunion-asistencia", description="Ver resumen de asistencia de una reunión")
@discord.app_commands.describe(numero="Número de la reunión")
async def reunion_asistencia_slash(interaction: discord.Interaction, numero: int):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)

    data_r = _cargar_reuniones()
    reunion = next((r for r in data_r.get("reuniones", []) if r["id"] == numero), None)
    if not reunion:
        return await interaction.response.send_message(f"❌  No encontré la reunión #{numero}.", ephemeral=True)

    asistencia = reunion.get("asistencia", {})
    puntuales = [v["nombre"] for v in asistencia.values() if v["estado"] == "puntual"]
    tarde = [v["nombre"] for v in asistencia.values() if v["estado"] == "tarde"]
    ausentes = [v["nombre"] for v in asistencia.values() if v["estado"] == "ausente"]

    e = discord.Embed(
        title=f"📋  Asistencia — Reunión #{numero}: {reunion['titulo']}",
        color=COLOR_PURPLE
    )
    e.add_field(name=f"✅  Puntuales ({len(puntuales)})",
                value="\n".join(puntuales) or "Ninguno", inline=False)
    e.add_field(name=f"⏰  Con retraso ({len(tarde)})",
                value="\n".join(tarde) or "Ninguno", inline=False)
    e.add_field(name=f"❌  Ausentes ({len(ausentes)})",
                value="\n".join(ausentes) or "Ninguno", inline=False)
    e.set_footer(text=FOOTER)
    await interaction.response.send_message(embed=e, ephemeral=True)

# ╔═══════════════════════════════════════════════════════════════╗
#   ⚡  SLASH — SANCIONES
# ╚═══════════════════════════════════════════════════════════════╝
async def _sancion_tipo_ac(interaction, current):
    ops = ["Warn", "Warn x2", "Warn 3 (Strike automático)", "Strike", "Strike x2", "Strike 3 (Demote)"]
    return [discord.app_commands.Choice(name=o, value=o)
            for o in ops if current.lower() in o.lower()]

async def _sancion_motivo_ac(interaction, current):
    motivos = [
        "Inactividad sin justificar",
        "Mal comportamiento con usuarios",
        "Abuso de permisos",
        "Incumplimiento de normas de staff",
        "Filtración de información interna",
        "Falta de respeto a compañeros",
        "No seguir el protocolo de tickets",
        "Ausencia en reuniones de staff",
        "Uso incorrecto de comandos",
        "No reportar bugs o errores encontrados",
    ]
    return [discord.app_commands.Choice(name=m, value=m)
            for m in motivos if current.lower() in m.lower()][:25]

async def _remover_staff_ac(interaction: discord.Interaction, current: str):
    data = _cargar_datos()
    opciones = []
    for uid_str, sd in data.items():
        if not sd.get("warns") and not sd.get("strikes"):
            continue
        try:
            m = interaction.guild.get_member(int(uid_str))
            if not m:
                continue
            nombre = m.display_name
            if current.lower() in nombre.lower():
                opciones.append(discord.app_commands.Choice(
                    name=nombre + "  (" + str(len(sd["warns"])) + "W · " + str(len(sd["strikes"])) + "S)",
                    value=uid_str
                ))
        except Exception:
            continue
    return opciones[:25]

async def _remover_sancion_ac(interaction: discord.Interaction, current: str):
    staff_val = None
    try:
        for opt in interaction.data.get("options", []):
            if opt["name"] == "staff":
                staff_val = opt["value"]
                break
    except Exception:
        pass
    if not staff_val:
        return [discord.app_commands.Choice(name="Primero selecciona un staff", value="none")]
    data = _cargar_datos()
    sd = data.get(staff_val, {"warns": [], "strikes": []})
    opciones = []
    for i, w in enumerate(sd.get("warns", [])):
        label = "⚠️ Warn " + str(i+1) + " — " + w["fecha"] + " — " + w["motivo"][:40]
        val = "warn:" + str(i)
        if current.lower() in label.lower():
            opciones.append(discord.app_commands.Choice(name=label[:100], value=val))
    for i, s in enumerate(sd.get("strikes", [])):
        label = "💥 Strike " + str(i+1) + " — " + s["fecha"] + " — " + s["motivo"][:40]
        val = "strike:" + str(i)
        if current.lower() in label.lower():
            opciones.append(discord.app_commands.Choice(name=label[:100], value=val))
    if not opciones:
        return [discord.app_commands.Choice(name="Sin sanciones registradas", value="none")]
    return opciones[:25]

async def _remover_razon_ac(interaction: discord.Interaction, current: str):
    razones = [
        "Error al registrar",
        "Sanción aplicada por error",
        "Apelación aceptada",
        "Decisión revisada por Head staff",
        "Acuerdo interno del staff",
        "Sanción duplicada",
        "El miembro ya fue amonestado verbalmente",
    ]
    return [discord.app_commands.Choice(name=r, value=r)
            for r in razones if current.lower() in r.lower()][:25]

@bot.tree.command(name="sancion", description="Registra una sanción a un miembro del staff")
@discord.app_commands.describe(
    staff="Miembro del staff a sancionar",
    motivo="Motivo de la sanción",
    sancion="Tipo de sanción: Warn o Strike",
)
@discord.app_commands.autocomplete(motivo=_sancion_motivo_ac, sancion=_sancion_tipo_ac)
async def sancion_slash(interaction: discord.Interaction,
                        staff: discord.Member,
                        motivo: str,
                        sancion: str):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)
    if staff.bot:
        return await interaction.response.send_message("❌  No puedes sancionar a un bot.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    data = _cargar_datos()
    sd = _get_staff_data(data, staff.id)
    fecha_ahora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    sancion_lower = sancion.lower()
    es_strike = sancion_lower.startswith("strike")

    if "x2" in sancion_lower:
        cantidad = 2
    elif sancion_lower.startswith("warn 3") or sancion_lower.startswith("strike 3"):
        cantidad = 3
    else:
        cantidad = 1

    strike_auto = False

    if not es_strike:
        for _ in range(cantidad):
            if len(sd["warns"]) < 3:
                sd["warns"].append({"motivo": motivo, "por": interaction.user.id, "fecha": fecha_ahora})
        if len(sd["warns"]) >= 3:
            sd["warns"] = []
            sd["strikes"].append({"motivo": "Strike automático por 3 warns",
                                   "por": bot.user.id, "fecha": fecha_ahora})
            strike_auto = True
    else:
        for _ in range(cantidad):
            if len(sd["strikes"]) < 3:
                sd["strikes"].append({"motivo": motivo, "por": interaction.user.id, "fecha": fecha_ahora})

    _guardar_datos(data)

    total_warns = len(sd["warns"])
    total_strikes = len(sd["strikes"])

    if es_strike or strike_auto:
        color = COLOR_DANGER
        icono = "💥"
    else:
        color = COLOR_WARN
        icono = "⚠️"

    barra_warns = ("🟡" * total_warns) + ("⬛" * (3 - total_warns))
    barra_strikes = ("🔴" * total_strikes) + ("⬛" * (3 - total_strikes))

    nota = ""
    if strike_auto:
        nota = "\n> 🔄  *3 warns → 1 strike automático. Warns reseteados a 0.*"

    e = discord.Embed(
        title=icono + "  Sanción Registrada — NightMc Staff",
        color=color, timestamp=datetime.datetime.now()
    )
    e.set_author(name="Sistema de Sanciones  ✦  NightMc Network",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    e.set_thumbnail(url=staff.display_avatar.url)
    e.description = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**👤  Staff:** " + staff.mention + "\n"
        "**👮  Aplicado por:** " + interaction.user.mention + "\n"
        "**📅  Fecha:** " + fecha_ahora + "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    e.add_field(name="📋  Motivo", value="> " + motivo, inline=False)
    e.add_field(name="⚖️  Sanción", value="> **" + sancion + "**" + nota, inline=False)
    e.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)
    e.add_field(name="⚠️  Warns  `" + str(total_warns) + "/3`", value=barra_warns, inline=True)
    e.add_field(name="💥  Strikes  `" + str(total_strikes) + "/3`", value=barra_strikes, inline=True)
    e.set_footer(text="Aplicado por " + interaction.user.display_name + "  ✦  " + FOOTER)

    canal = await _get_canal_strikes(interaction.guild)
    if canal:
        await canal.send(embed=e)
        await interaction.followup.send("✅  Sanción registrada.", ephemeral=True)
    else:
        await interaction.followup.send("❌  No se encontró el canal #strikes.", ephemeral=True)

    if total_strikes >= 3 and es_strike:
        await _notificar_strike(interaction.guild, staff, sd, canal, motivo, demote=True)

@bot.tree.command(name="historial", description="Muestra el historial de warns/strikes de un staff")
@discord.app_commands.describe(miembro="Staff a consultar")
async def historial_slash(interaction: discord.Interaction, miembro: discord.Member):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)
    
    data = _cargar_datos()
    sd = _get_staff_data(data, miembro.id)
    await interaction.response.send_message(embed=_build_historial_embed(miembro, sd, interaction.guild), ephemeral=True)

async def _ejecutar_remover(interaction, staff_uid: str, sancion_val: str, razon: str):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    if sancion_val == "none":
        return await interaction.followup.send("❌  Selecciona una sanción válida.", ephemeral=True)

    data = _cargar_datos()
    try:
        uid = int(staff_uid)
    except ValueError:
        return await interaction.followup.send("❌  Staff inválido.", ephemeral=True)

    sd = data.get(staff_uid, {"warns": [], "strikes": []})

    try:
        tipo, idx_str = sancion_val.split(":")
        idx = int(idx_str)
    except Exception:
        return await interaction.followup.send("❌  Sanción inválida.", ephemeral=True)

    lista = sd.get("warns" if tipo == "warn" else "strikes", [])
    if idx < 0 or idx >= len(lista):
        return await interaction.followup.send("❌  Esa sanción ya no existe.", ephemeral=True)

    sancion_removida = lista.pop(idx)
    data[staff_uid] = sd
    _guardar_datos(data)

    miembro = interaction.guild.get_member(uid)
    nombre_display = miembro.mention if miembro else f"<@{uid}>"
    icono = "⚠️" if tipo == "warn" else "💥"
    tipo_nombre = "Warn" if tipo == "warn" else "Strike"
    total_warns = len(sd.get("warns", []))
    total_strikes = len(sd.get("strikes", []))
    barra_warns = ("🟡" * total_warns) + ("⬛" * (3 - total_warns))
    barra_strikes = ("🔴" * total_strikes) + ("⬛" * (3 - total_strikes))

    sep = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    e = discord.Embed(
        title="🗑️  Sanción Removida — NightMc Staff",
        color=COLOR_OK, timestamp=datetime.datetime.now()
    )
    e.set_author(name="Sistema de Sanciones  ✦  NightMc Network",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    if miembro:
        e.set_thumbnail(url=miembro.display_avatar.url)
    e.description = (
        sep + "\n"
        "**👤  Staff:** " + nombre_display + "\n"
        "**👮  Removido por:** " + interaction.user.mention + "\n"
        "**📅  Fecha:** " + datetime.datetime.now().strftime("%d/%m/%Y  %H:%M") + "\n" + sep
    )
    e.add_field(name=icono + "  Sanción removida",
                value="> **" + tipo_nombre + "** — " + sancion_removida.get("motivo", "—"), inline=False)
    e.add_field(name="📋  Razón de remoción", value="> " + razon, inline=False)
    e.add_field(name="\u200b", value=sep, inline=False)
    e.add_field(name="⚠️  Warns  `" + str(total_warns) + "/3`", value=barra_warns, inline=True)
    e.add_field(name="💥  Strikes  `" + str(total_strikes) + "/3`", value=barra_strikes, inline=True)
    e.set_footer(text="Removido por " + interaction.user.display_name + "  ✦  " + FOOTER)

    for canal in [await _get_canal_strikes(interaction.guild),
                  await _get_sanciones_canal(interaction.guild)]:
        if canal:
            try:
                await canal.send(embed=e)
            except Exception:
                pass

    await interaction.followup.send("✅  " + tipo_nombre + " removido correctamente.", ephemeral=True)

@bot.tree.command(name="remover", description="Remueve una sanción específica de un miembro del staff")
@discord.app_commands.describe(
    staff="Staff del que remover la sanción",
    sancion="Sanción a remover",
    razon="Razón por la que se remueve",
)
@discord.app_commands.autocomplete(staff=_remover_staff_ac, sancion=_remover_sancion_ac, razon=_remover_razon_ac)
async def remover_slash(interaction: discord.Interaction, staff: str, sancion: str, razon: str):
    await _ejecutar_remover(interaction, staff, sancion, razon)

@bot.tree.command(name="rs", description="[Alias] Remueve una sanción específica")
@discord.app_commands.describe(
    staff="Staff del que remover la sanción",
    sancion="Sanción a remover",
    razon="Razón por la que se remueve",
)
@discord.app_commands.autocomplete(staff=_remover_staff_ac, sancion=_remover_sancion_ac, razon=_remover_razon_ac)
async def rs_slash(interaction: discord.Interaction, staff: str, sancion: str, razon: str):
    await _ejecutar_remover(interaction, staff, sancion, razon)

# ╔═══════════════════════════════════════════════════════════════╗
#   🆘  COMANDOS DE AYUDA DINÁMICA
# ╚═══════════════════════════════════════════════════════════════╝
def _get_comandos_por_rol(member: discord.Member):
    roles_miembro = [r.name for r in member.roles]
    
    comandos = [
        ("⚖️ Sanciones", "/sancion", "Registrar sanción (warn/strike)", ["Hight staff", "Head staff"]),
        ("⚖️ Sanciones", "/historial", "Ver historial de sanciones", ["Hight staff", "Head staff"]),
        ("⚖️ Sanciones", "/remover", "Remover una sanción", ["Hight staff", "Head staff"]),
        ("⚖️ Sanciones", "/rs", "Alias de /remover", ["Hight staff", "Head staff"]),
        ("⚖️ Sanciones", "st!warn", "Warn por prefijo", ["Hight staff", "Head staff"]),
        ("⚖️ Sanciones", "st!strike", "Strike por prefijo", ["Hight staff", "Head staff"]),
        ("⚖️ Sanciones", "st!historial", "Historial por prefijo", ["Hight staff", "Head staff"]),
        ("🏆 Puntos", "/puntos", "Ver puntos (totales y semanales)", ["Staff team"]),
        ("🏆 Puntos", "/ps", "Ranking semanal", ["Hight staff", "Head staff"]),
        ("🏆 Puntos", "/iniciar_semana", "Iniciar semana de puntos", ["Head staff"]),
        ("🏆 Puntos", "/cerrar_semana", "Cerrar semana y anunciar ganador", ["Head staff"]),
        ("🏆 Puntos", "/puntos-reset", "Resetear puntos de un staff", ["Head staff"]),
        ("⏱️ Inactividad", "/inactividad", "Consultar inactividad (global/por canal/top)", ["Hight staff", "Head staff"]),
        ("📅 Reuniones", "/reunion", "Convocar reunión", ["Hight staff", "Head staff"]),
        ("📅 Reuniones", "/reunion-asistencia", "Ver asistencia a reunión", ["Hight staff", "Head staff"]),
        ("🔧 Administración", "st!sync", "Sincronizar comandos slash", ["Head staff"]),
    ]
    
    comandos_usuario = []
    for cat, nombre, desc, roles in comandos:
        if any(r in roles for r in roles_miembro):
            comandos_usuario.append((cat, nombre, desc))
    
    return comandos_usuario

@bot.tree.command(name="help", description="Muestra la ayuda según tu rango")
async def help_slash(interaction: discord.Interaction):
    await _enviar_help(interaction, interaction.user)

@bot.command(name="help")
async def help_prefix(ctx):
    await _enviar_help(ctx, ctx.author)

async def _enviar_help(ctx_or_interaction, usuario):
    comandos = _get_comandos_por_rol(usuario)
    if not comandos:
        msg = "No tienes acceso a ningún comando."
        if hasattr(ctx_or_interaction, 'response'):
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return
    
    embed = discord.Embed(title="📖  Ayuda de NightMC Staff", color=COLOR_BLUE)
    categorias = {}
    for cat, nombre, desc in comandos:
        categorias.setdefault(cat, []).append(f"`{nombre}` – {desc}")
    
    for cat, lista in categorias.items():
        embed.add_field(name=cat, value="\n".join(lista), inline=False)
    
    roles_usuario = [r.name for r in usuario.roles if r.name in TODOS_ROLES_STAFF]
    embed.set_footer(text=f"Tu rango: {', '.join(roles_usuario) if roles_usuario else 'Sin rol staff'}")
    
    if hasattr(ctx_or_interaction, 'response'):
        await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed)

# ╔═══════════════════════════════════════════════════════════════╗
#   💬  COMANDOS DE PREFIJO (LEGACY)
# ╚═══════════════════════════════════════════════════════════════╝
@bot.command(name="warn")
async def warn_cmd(ctx, raw_miembro: str = None, *, motivo: str = None):
    if not _es_superior(ctx.author):
        return await ctx.send("❌  Solo **Hight staff** o superior puede usar este comando.")
    if not raw_miembro:
        return await ctx.send("❌  Uso: `st!warn @staff motivo`")
    if not motivo:
        return await ctx.send("❌  Debes especificar un motivo.")
    
    miembro = await _resolver_miembro(ctx, raw_miembro)
    if not miembro:
        return await ctx.send("❌  No encontré ese usuario. Usa @mención o el ID.")
    if miembro.bot:
        return await ctx.send("❌  No puedes sancionar a un bot.")

    data = _cargar_datos()
    sd = _get_staff_data(data, miembro.id)
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    if len(sd["warns"]) < 3:
        sd["warns"].append({"motivo": motivo, "por": ctx.author.id, "fecha": fecha})

    nuevo_strike = False
    if len(sd["warns"]) >= 3:
        sd["warns"] = []
        sd["strikes"].append({"motivo": "Strike automático por 3 warns",
                               "por": bot.user.id, "fecha": fecha})
        nuevo_strike = True

    _guardar_datos(data)
    total_warns = len(sd["warns"])
    total_strikes = len(sd["strikes"])

    canal_s = await _get_sanciones_canal(ctx.guild)
    e = discord.Embed(title="⚠️  Warn Registrado — Staff NightMc", color=COLOR_WARN,
                      timestamp=datetime.datetime.now())
    e.set_thumbnail(url=miembro.display_avatar.url)
    e.add_field(name="👤  Staff", value=miembro.mention, inline=True)
    e.add_field(name="👮  Aplicado por", value=ctx.author.mention, inline=True)
    e.add_field(name="📋  Motivo", value="```" + motivo + "```", inline=False)
    barra_w = ("🟡" * total_warns) + ("⬛" * (3 - total_warns))
    barra_s = ("🔴" * total_strikes) + ("⬛" * (3 - total_strikes))
    e.add_field(name="⚠️  Warns `" + str(total_warns) + "/3`", value=barra_w, inline=True)
    e.add_field(name="💥  Strikes `" + str(total_strikes) + "/3`", value=barra_s, inline=True)
    if nuevo_strike:
        e.add_field(name="🔄  Strike automático", value="> 3 warns → +1 strike. Warns reseteados.", inline=False)
    e.set_footer(text=FOOTER)
    
    if canal_s:
        await canal_s.send(embed=e)
    try:
        await ctx.message.delete()
    except:
        pass
    await ctx.send(f"✅  Warn registrado para {miembro.mention}. "
                   f"Warns: **{total_warns}/3** | Strikes: **{total_strikes}/3**", delete_after=8)
    if nuevo_strike:
        await _notificar_strike(ctx.guild, miembro, sd, canal_s, motivo)

@bot.command(name="strike")
async def strike_cmd(ctx, raw_miembro: str = None, *, motivo: str = None):
    if not _es_superior(ctx.author):
        return await ctx.send("❌  Solo **Hight staff** o superior puede usar este comando.")
    if not raw_miembro:
        return await ctx.send("❌  Uso: `st!strike @staff motivo`")
    if not motivo:
        return await ctx.send("❌  Debes especificar un motivo.")
    
    miembro = await _resolver_miembro(ctx, raw_miembro)
    if not miembro:
        return await ctx.send("❌  No encontré ese usuario. Usa @mención o el ID.")
    if miembro.bot:
        return await ctx.send("❌  No puedes sancionar a un bot.")

    data = _cargar_datos()
    sd = _get_staff_data(data, miembro.id)
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    if len(sd["strikes"]) < 3:
        sd["strikes"].append({"motivo": motivo, "por": ctx.author.id, "fecha": fecha})
    _guardar_datos(data)

    total_warns = len(sd["warns"])
    total_strikes = len(sd["strikes"])

    canal_s = await _get_sanciones_canal(ctx.guild)
    e = discord.Embed(title="💥  Strike Registrado — Staff NightMc", color=COLOR_DANGER,
                      timestamp=datetime.datetime.now())
    e.set_thumbnail(url=miembro.display_avatar.url)
    e.add_field(name="👤  Staff", value=miembro.mention, inline=True)
    e.add_field(name="👮  Aplicado por", value=ctx.author.mention, inline=True)
    e.add_field(name="📋  Motivo", value="```" + motivo + "```", inline=False)
    barra_w = ("🟡" * total_warns) + ("⬛" * (3 - total_warns))
    barra_s = ("🔴" * total_strikes) + ("⬛" * (3 - total_strikes))
    e.add_field(name="⚠️  Warns `" + str(total_warns) + "/3`", value=barra_w, inline=True)
    e.add_field(name="💥  Strikes `" + str(total_strikes) + "/3`", value=barra_s, inline=True)
    e.set_footer(text=FOOTER)
    
    if canal_s:
        await canal_s.send(embed=e)
    try:
        await ctx.message.delete()
    except:
        pass
    await ctx.send(f"✅  Strike registrado para {miembro.mention}. "
                   f"Warns: **{total_warns}/3** | Strikes: **{total_strikes}/3**", delete_after=8)
    if total_strikes >= 3:
        await _notificar_strike(ctx.guild, miembro, sd, canal_s, motivo, demote=True)

@bot.command(name="historial")
async def historial_cmd(ctx, raw_miembro: str = None):
    if not _es_superior(ctx.author):
        return await ctx.send("❌  Solo **Hight staff** o superior puede usar este comando.")
    if not raw_miembro:
        return await ctx.send("❌  Uso: `st!historial @staff`")
    
    miembro = await _resolver_miembro(ctx, raw_miembro)
    if not miembro:
        return await ctx.send("❌  No encontré ese usuario. Usa @mención o el ID.")
    
    data = _cargar_datos()
    sd = _get_staff_data(data, miembro.id)
    await ctx.send(embed=_build_historial_embed(miembro, sd, ctx.guild))

# ╔═══════════════════════════════════════════════════════════════╗
#   🛠️  ADMIN
# ╚═══════════════════════════════════════════════════════════════╝
@bot.command()
@commands.has_permissions(administrator=True)
async def sync(ctx):
    msg = await ctx.send("⏳  Registrando comandos...")
    try:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await msg.edit(content=f"✅  **{len(synced)} comandos** registrados en **{ctx.guild.name}**.\n💡  Si no aparecen haz **Ctrl+R**.")
        for cmd in synced:
            print(f"  · /{cmd.name}")
    except Exception as e:
        await msg.edit(content=f"❌  Error: {e}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("❌  Sin permisos.")
    if isinstance(error, commands.MemberNotFound):
        return await ctx.send("❌  No encontré ese usuario. Usa @mención o el ID.")
    raise error

# ╔═══════════════════════════════════════════════════════════════╗
#   🚀  TOKEN Y EJECUCIÓN
# ╚═══════════════════════════════════════════════════════════════╝
load_dotenv()
token = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if token:
        print("✅ Iniciando el bot de NightMC...")
        bot.run(token)
    else:
        print("❌ ERROR: No se encontró la variable DISCORD_TOKEN.")
