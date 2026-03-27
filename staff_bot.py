import discord
from discord.ext import commands
import datetime
import json
import os
import re

# ╔═══════════════════════════════════════════════════════════════╗
#   ⚙️  CONFIGURACIÓN
# ╚═══════════════════════════════════════════════════════════════╝
STAFF_TEAM        = "Staff team"
TODOS_ROLES_STAFF = ["Low staff", "Medium Staff", "Hight staff", "Head staff", "Staff team"]
ROLES_SUPERIORES  = ["Hight staff", "Head staff"]

SANCIONES_FILE      = "sanciones_data.json"
PUNTOS_FILE         = "puntos_data.json"
REUNIONES_FILE      = "reuniones_data.json"
SANCIONES_CANAL     = "sanciones"
CANAL_STRIKES       = "strikes"
CANAL_REUNIONES     = "💼│reuniones"
WARNS_PARA_STRIKE   = 3
STRIKES_PARA_DEMOTE = 3

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
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        print("✦  Bot de Staff listo. Usa !sync para registrar los comandos slash.")

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

def _es_staff(m: discord.Member) -> bool:
    return any(r.name in TODOS_ROLES_STAFF for r in m.roles)

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
            "historial": [],
            "por_canal": {c: 0 for c in CANALES_PUNTOS}
        }
    # Asegura que existan todos los canales
    for c in CANALES_PUNTOS:
        data[key]["por_canal"].setdefault(c, 0)
    return data[key]

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
    """Cuando el bot (u otro superior) pone ✅ en un canal de puntos, suma puntos al autor."""
    # Solo reacciones de bots o superiores cuentan
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    reactor = guild.get_member(payload.user_id)
    if not reactor:
        return

    # Solo el bot o superiores pueden validar
    if not (reactor.bot or _es_superior(reactor)):
        return

    # Solo ✅
    if str(payload.emoji) != "✅":
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel:
        return

    # ¿Es un canal de puntos? Buscar por nombre parcial
    canal_key = None
    for key in CANALES_PUNTOS:
        if key in channel.name:
            canal_key = key
            break
    if not canal_key:
        return

    # Obtener el mensaje
    try:
        message = await channel.fetch_message(payload.message_id)
    except Exception:
        return

    # No contar si el autor es un bot
    if message.author.bot:
        return

    # Solo contar si es staff
    autor = guild.get_member(message.author.id)
    if not autor or not _es_staff(autor):
        return

    # Sumar puntos
    puntos_a_dar = CANALES_PUNTOS[canal_key]["puntos"]
    data = _cargar_puntos()
    pd   = _get_puntos_data(data, autor.id)
    pd["total"] += puntos_a_dar
    pd["por_canal"][canal_key] = pd["por_canal"].get(canal_key, 0) + puntos_a_dar
    pd["historial"].append({
        "canal":  canal_key,
        "puntos": puntos_a_dar,
        "fecha":  datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "msg_id": str(payload.message_id)
    })
    _guardar_puntos(data)
    print(f"[puntos] +{puntos_a_dar} a {autor} en #{canal_key} (total: {pd['total']})")

# ── /puntos ────────────────────────────────────────────────────────
@bot.tree.command(name="puntos", description="Muestra el ranking de puntos del staff")
@discord.app_commands.describe(miembro="Ver puntos de un miembro específico (opcional)")
async def puntos_slash(interaction: discord.Interaction, miembro: discord.Member = None):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)

    await interaction.response.defer(ephemeral=False)
    data = _cargar_puntos()

    if miembro:
        # Vista individual
        pd = _get_puntos_data(data, miembro.id)
        e = discord.Embed(
            title="🏆  Puntos — " + miembro.display_name,
            color=COLOR_GOLD, timestamp=datetime.datetime.now()
        )
        e.set_thumbnail(url=miembro.display_avatar.url)
        e.set_author(name="Sistema de Puntos — NightMc Network",
                     icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        e.add_field(name="⭐  Total", value=f"**{pd['total']} pts**", inline=False)
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
        else:
            e.add_field(name="🕒  Actividad", value="Sin actividad registrada.", inline=False)
        e.set_footer(text=FOOTER)
        return await interaction.followup.send(embed=e)

    # Ranking global
    ranking = []
    for uid_str, pd in data.items():
        total = pd.get("total", 0)
        if total == 0:
            continue
        m = interaction.guild.get_member(int(uid_str))
        if not m:
            continue
        ranking.append((m, total))

    ranking.sort(key=lambda x: x[1], reverse=True)

    e = discord.Embed(
        title="🏆  Ranking de Puntos — Staff NightMc",
        color=COLOR_GOLD, timestamp=datetime.datetime.now()
    )
    e.set_author(name="Sistema de Puntos — NightMc Network",
                 icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

    if not ranking:
        e.description = "Aún no hay puntos registrados."
    else:
        medallas = ["🥇", "🥈", "🥉"]
        txt = ""
        for i, (m, pts) in enumerate(ranking[:10]):
            med = medallas[i] if i < 3 else f"`{i+1}.`"
            txt += f"{med}  {m.mention}  —  **{pts} pts**\n"
        e.description = txt

    e.set_footer(text=FOOTER)
    await interaction.followup.send(embed=e)

# ── /puntos-reset ──────────────────────────────────────────────────
@bot.tree.command(name="puntos-reset", description="Resetea los puntos de un miembro del staff")
@discord.app_commands.describe(miembro="Miembro a resetear")
async def puntos_reset_slash(interaction: discord.Interaction, miembro: discord.Member):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    data = _cargar_puntos()
    key  = str(miembro.id)
    if key in data:
        data[key] = {"total": 0, "historial": [], "por_canal": {c: 0 for c in CANALES_PUNTOS}}
        _guardar_puntos(data)
    await interaction.followup.send(f"✅  Puntos de {miembro.mention} reseteados.", ephemeral=True)

# ╔═══════════════════════════════════════════════════════════════╗
#   📅  SISTEMA DE REUNIONES
# ╚═══════════════════════════════════════════════════════════════╝

# ── Views de Asistencia ────────────────────────────────────────────
class AsistenciaView(discord.ui.View):
    def __init__(self, reunion_id: int):
        super().__init__(timeout=None)
        self.reunion_id = reunion_id
        self.custom_id_prefix = f"reunion_{reunion_id}"

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

# ── Autocomplete reuniones ──────────────────────────────────────────
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

# ── /reunion ────────────────────────────────────────────────────────
@bot.tree.command(name="reunion", description="Convoca una reunión oficial del staff")
@discord.app_commands.describe(
    titulo="Título de la reunión (ej: Primera Reunión Estratégica)",
    fecha="Fecha de la reunión (ej: sábado, 28 de marzo de 2026)",
    hora="Hora de la reunión en UTC (ej: 17:30)",
    canal_voz="Canal de voz donde se hará la reunión",
    temas="Temas separados por | (ej: Infraestructura|Soporte|Roadmap)",
    descripcion="Descripción o subtítulo de la reunión (opcional)",
    mencionar="Rol a mencionar (opcional, por defecto @Staff team)",
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
        return await interaction.response.send_message(
            "❌  Solo Hight staff o superior puede convocar reuniones.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    # Parsear hora UTC a timestamp de Discord
    timestamp_str = ""
    try:
        # Intentar parsear la hora — formato HH:MM
        hm = hora.strip().split(":")
        h, m = int(hm[0]), int(hm[1])
        # Intentar parsear la fecha (buscar día y mes)
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

    # Parsear temas
    lista_temas = [t.strip() for t in temas.split("|") if t.strip()]

    # Número de reunión
    data_r = _cargar_reuniones()
    data_r["contador"] = data_r.get("contador", 0) + 1
    num = data_r["contador"]
    num_texto = _numero_ordinal(num)

    # Encontrar canal de reuniones
    canal_destino = None
    for ch in interaction.guild.text_channels:
        if "reuniones" in ch.name.lower():
            canal_destino = ch
            break
    if not canal_destino:
        canal_destino = interaction.channel

    # Rol a mencionar
    rol_mencion = mencionar or STAFF_TEAM
    rol_obj = discord.utils.get(interaction.guild.roles, name=rol_mencion)
    mention_txt = rol_obj.mention if rol_obj else f"@{rol_mencion}"

    # Descripción del embed
    desc_base = descripcion or "Este encuentro es clave para alinear nuestros objetivos y compartir los avances de la network."

    # Temas formateados
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
    if interaction.guild.banner:
        e.set_image(url=interaction.guild.banner.url)

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

    # Datos de la reunión
    datos_reunion = f"📅  **FECHA Y HORA:** {timestamp_str}\n"
    if timestamp_rel:
        datos_reunion += f"⏱️  **TIEMPO RESTANTE:** {timestamp_rel}\n"
    datos_reunion += f"🎙️  **CANAL:** {canal_voz}\n"
    e.add_field(name="🗓️  DATOS DE LA REUNIÓN", value=datos_reunion, inline=False)

    e.add_field(
        name="⚠️  AVISO IMPORTANTE",
        value=(
            "> Si por motivos de fuerza mayor no puedes asistir o llegarás tarde,\n"
            "> es **obligatorio** avisarlo en: 📬│inactividad"
        ),
        inline=False
    )
    e.add_field(name="\u200b", value=sep, inline=False)
    e.add_field(
        name="✅  ¿CONFIRMAS TU ASISTENCIA?",
        value="Usa los botones de abajo para confirmar.",
        inline=False
    )
    e.set_footer(text=f"Reunión #{num}  ✦  {FOOTER}  ✦  Convocada por {interaction.user.display_name}")

    # Guardar reunión
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

def _numero_ordinal(n: int) -> str:
    nombres = ["Primera","Segunda","Tercera","Cuarta","Quinta",
               "Sexta","Séptima","Octava","Novena","Décima"]
    if 1 <= n <= 10:
        return nombres[n - 1]
    return f"{n}ª"

# ── /reunion-asistencia ────────────────────────────────────────────
@bot.tree.command(name="reunion-asistencia", description="Ver resumen de asistencia de una reunión")
@discord.app_commands.describe(numero="Número de la reunión (ej: 1)")
async def reunion_asistencia_slash(interaction: discord.Interaction, numero: int):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)

    data_r = _cargar_reuniones()
    reunion = next((r for r in data_r.get("reuniones", []) if r["id"] == numero), None)
    if not reunion:
        return await interaction.followup.send(f"❌  No encontré la reunión #{numero}.", ephemeral=True)

    asistencia = reunion.get("asistencia", {})
    puntuales = [v["nombre"] for v in asistencia.values() if v["estado"] == "puntual"]
    tarde      = [v["nombre"] for v in asistencia.values() if v["estado"] == "tarde"]
    ausentes   = [v["nombre"] for v in asistencia.values() if v["estado"] == "ausente"]

    e = discord.Embed(
        title=f"📋  Asistencia — Reunión #{numero}: {reunion['titulo']}",
        color=COLOR_PURPLE, timestamp=datetime.datetime.now()
    )
    e.add_field(name=f"✅  Puntuales ({len(puntuales)})",
                value="\n".join(puntuales) or "Ninguno", inline=False)
    e.add_field(name=f"⏰  Con retraso ({len(tarde)})",
                value="\n".join(tarde) or "Ninguno", inline=False)
    e.add_field(name=f"❌  Ausentes ({len(ausentes)})",
                value="\n".join(ausentes) or "Ninguno", inline=False)
    e.set_footer(text=FOOTER)
    await interaction.followup.send(embed=e, ephemeral=True)

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
    sd   = data.get(staff_val, {"warns": [], "strikes": []})
    opciones = []
    for i, w in enumerate(sd.get("warns", [])):
        label = "⚠️ Warn " + str(i+1) + " — " + w["fecha"] + " — " + w["motivo"][:40]
        val   = "warn:" + str(i)
        if current.lower() in label.lower():
            opciones.append(discord.app_commands.Choice(name=label[:100], value=val))
    for i, s in enumerate(sd.get("strikes", [])):
        label = "💥 Strike " + str(i+1) + " — " + s["fecha"] + " — " + s["motivo"][:40]
        val   = "strike:" + str(i)
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

# ── /sancion ──────────────────────────────────────────────────────
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
        return await interaction.response.send_message(
            "❌  Solo Hight staff o superior puede usar este comando.", ephemeral=True)
    if staff.bot:
        return await interaction.response.send_message("❌  No puedes sancionar a un bot.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)

    data = _cargar_datos()
    sd   = _get_staff_data(data, staff.id)
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

    total_warns   = len(sd["warns"])
    total_strikes = len(sd["strikes"])

    if es_strike or strike_auto:
        color = COLOR_DANGER
        icono = "💥"
    else:
        color = COLOR_WARN
        icono = "⚠️"

    barra_warns   = ("🟡" * total_warns)   + ("⬛" * (3 - total_warns))
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
    e.add_field(name="📋  Motivo",  value="> " + motivo, inline=False)
    e.add_field(name="⚖️  Sanción", value="> **" + sancion + "**" + nota, inline=False)
    e.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)
    e.add_field(name="⚠️  Warns  `" + str(total_warns) + "/3`",    value=barra_warns,   inline=True)
    e.add_field(name="💥  Strikes  `" + str(total_strikes) + "/3`", value=barra_strikes, inline=True)
    e.set_footer(text="Aplicado por " + interaction.user.display_name + "  ✦  " + FOOTER)

    canal = await _get_canal_strikes(interaction.guild)
    if canal:
        await canal.send(embed=e)
        await interaction.followup.send("✅  Sanción registrada en " + canal.mention, ephemeral=True)
    else:
        await interaction.followup.send("❌  No se encontró el canal #strikes.", ephemeral=True)

    if total_strikes >= 3 and es_strike:
        await _notificar_strike(interaction.guild, staff, sd, canal, motivo, demote=True)

# ── /historial ────────────────────────────────────────────────────
@bot.tree.command(name="historial", description="Muestra el historial de warns/strikes de un staff")
@discord.app_commands.describe(miembro="Staff a consultar")
async def historial_slash(interaction: discord.Interaction, miembro: discord.Member):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message("❌  Solo Hight staff o superior.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    data = _cargar_datos()
    sd   = _get_staff_data(data, miembro.id)
    await interaction.followup.send(embed=_build_historial_embed(miembro, sd, interaction.guild), ephemeral=True)

# ── /remover y /rs ────────────────────────────────────────────────
async def _ejecutar_remover(interaction, staff_uid: str, sancion_val: str, razon: str):
    if not _es_superior(interaction.user):
        return await interaction.response.send_message(
            "❌  Solo Hight staff o superior puede usar este comando.", ephemeral=True)

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
        return await interaction.followup.send(
            "❌  Esa sanción ya no existe.", ephemeral=True)

    sancion_removida = lista.pop(idx)
    data[staff_uid] = sd
    _guardar_datos(data)

    miembro        = interaction.guild.get_member(uid)
    nombre_display = miembro.mention if miembro else f"<@{uid}>"
    icono          = "⚠️" if tipo == "warn" else "💥"
    tipo_nombre    = "Warn" if tipo == "warn" else "Strike"
    total_warns    = len(sd.get("warns", []))
    total_strikes  = len(sd.get("strikes", []))
    barra_warns    = ("🟡" * total_warns)   + ("⬛" * (3 - total_warns))
    barra_strikes  = ("🔴" * total_strikes) + ("⬛" * (3 - total_strikes))

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
    e.add_field(name="⚠️  Warns  `" + str(total_warns) + "/3`",    value=barra_warns,   inline=True)
    e.add_field(name="💥  Strikes  `" + str(total_strikes) + "/3`", value=barra_strikes, inline=True)
    e.set_footer(text="Removido por " + interaction.user.display_name + "  ✦  " + FOOTER)

    for canal in [await _get_canal_strikes(interaction.guild),
                  await _get_sanciones_canal(interaction.guild)]:
        if canal:
            try: await canal.send(embed=e)
            except Exception: pass

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

@bot.tree.command(name="rs", description="[Alias] Remueve una sanción específica de un miembro del staff")
@discord.app_commands.describe(
    staff="Staff del que remover la sanción",
    sancion="Sanción a remover",
    razon="Razón por la que se remueve",
)
@discord.app_commands.autocomplete(staff=_remover_staff_ac, sancion=_remover_sancion_ac, razon=_remover_razon_ac)
async def rs_slash(interaction: discord.Interaction, staff: str, sancion: str, razon: str):
    await _ejecutar_remover(interaction, staff, sancion, razon)

# ╔═══════════════════════════════════════════════════════════════╗
#   💬  COMANDOS DE PREFIJO
# ╚═══════════════════════════════════════════════════════════════╝
@bot.command(name="warn")
async def warn_cmd(ctx, raw_miembro: str = None, *, motivo: str = None):
    if not _es_superior(ctx.author):
        return await ctx.send("❌  Solo **Hight staff** o superior puede usar este comando.")
    if not raw_miembro:
        return await ctx.send("❌  Uso: `!warn @staff motivo`")
    if not motivo:
        return await ctx.send("❌  Debes especificar un motivo.")
    miembro = await _resolver_miembro(ctx, raw_miembro)
    if not miembro:
        return await ctx.send("❌  No encontré ese usuario. Usa @mención o el ID.")
    if miembro.bot:
        return await ctx.send("❌  No puedes sancionar a un bot.")

    data = _cargar_datos()
    sd   = _get_staff_data(data, miembro.id)
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
    total_warns   = len(sd["warns"])
    total_strikes = len(sd["strikes"])

    canal_s = await _get_sanciones_canal(ctx.guild)
    e = discord.Embed(title="⚠️  Warn Registrado — Staff NightMc", color=COLOR_WARN,
                      timestamp=datetime.datetime.now())
    e.set_thumbnail(url=miembro.display_avatar.url)
    e.add_field(name="👤  Staff",        value=miembro.mention,   inline=True)
    e.add_field(name="👮  Aplicado por", value=ctx.author.mention, inline=True)
    e.add_field(name="📋  Motivo", value="```" + motivo + "```", inline=False)
    barra_w = ("🟡" * total_warns) + ("⬛" * (3 - total_warns))
    barra_s = ("🔴" * total_strikes) + ("⬛" * (3 - total_strikes))
    e.add_field(name="⚠️  Warns `" + str(total_warns) + "/3`",    value=barra_w, inline=True)
    e.add_field(name="💥  Strikes `" + str(total_strikes) + "/3`", value=barra_s, inline=True)
    if nuevo_strike:
        e.add_field(name="🔄  Strike automático", value="> 3 warns → +1 strike. Warns reseteados.", inline=False)
    e.set_footer(text=FOOTER)
    if canal_s:
        await canal_s.send(embed=e)
    try: await ctx.message.delete()
    except: pass
    await ctx.send(f"✅  Warn registrado para {miembro.mention}. "
                   f"Warns: **{total_warns}/3** | Strikes: **{total_strikes}/3**", delete_after=8)
    if nuevo_strike:
        await _notificar_strike(ctx.guild, miembro, sd, canal_s, motivo)

@bot.command(name="strike")
async def strike_cmd(ctx, raw_miembro: str = None, *, motivo: str = None):
    if not _es_superior(ctx.author):
        return await ctx.send("❌  Solo **Hight staff** o superior puede usar este comando.")
    if not raw_miembro:
        return await ctx.send("❌  Uso: `!strike @staff motivo`")
    if not motivo:
        return await ctx.send("❌  Debes especificar un motivo.")
    miembro = await _resolver_miembro(ctx, raw_miembro)
    if not miembro:
        return await ctx.send("❌  No encontré ese usuario. Usa @mención o el ID.")
    if miembro.bot:
        return await ctx.send("❌  No puedes sancionar a un bot.")

    data = _cargar_datos()
    sd   = _get_staff_data(data, miembro.id)
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    if len(sd["strikes"]) < 3:
        sd["strikes"].append({"motivo": motivo, "por": ctx.author.id, "fecha": fecha})
    _guardar_datos(data)

    total_warns   = len(sd["warns"])
    total_strikes = len(sd["strikes"])

    canal_s = await _get_sanciones_canal(ctx.guild)
    e = discord.Embed(title="💥  Strike Registrado — Staff NightMc", color=COLOR_DANGER,
                      timestamp=datetime.datetime.now())
    e.set_thumbnail(url=miembro.display_avatar.url)
    e.add_field(name="👤  Staff",        value=miembro.mention,   inline=True)
    e.add_field(name="👮  Aplicado por", value=ctx.author.mention, inline=True)
    e.add_field(name="📋  Motivo", value="```" + motivo + "```", inline=False)
    barra_w = ("🟡" * total_warns) + ("⬛" * (3 - total_warns))
    barra_s = ("🔴" * total_strikes) + ("⬛" * (3 - total_strikes))
    e.add_field(name="⚠️  Warns `" + str(total_warns) + "/3`",    value=barra_w, inline=True)
    e.add_field(name="💥  Strikes `" + str(total_strikes) + "/3`", value=barra_s, inline=True)
    e.set_footer(text=FOOTER)
    if canal_s:
        await canal_s.send(embed=e)
    try: await ctx.message.delete()
    except: pass
    await ctx.send(f"✅  Strike registrado para {miembro.mention}. "
                   f"Warns: **{total_warns}/3** | Strikes: **{total_strikes}/3**", delete_after=8)
    if total_strikes >= 3:
        await _notificar_strike(ctx.guild, miembro, sd, canal_s, motivo, demote=True)

@bot.command(name="historial")
async def historial_cmd(ctx, raw_miembro: str = None):
    if not _es_superior(ctx.author):
        return await ctx.send("❌  Solo **Hight staff** o superior puede usar este comando.")
    if not raw_miembro:
        return await ctx.send("❌  Uso: `!historial @staff`")
    miembro = await _resolver_miembro(ctx, raw_miembro)
    if not miembro:
        return await ctx.send("❌  No encontré ese usuario. Usa @mención o el ID.")
    data = _cargar_datos()
    sd   = _get_staff_data(data, miembro.id)
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

# --- AL FINAL DE TU ARCHIVO staff_bot.py ---
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

if __name__ == "__main__":
    if token:
        print("✅ Iniciando el bot de NightMC...")
        bot.run(token)
    else:
        print("❌ ERROR: No se encontró la variable DISCORD_TOKEN.")

# ╔═══════════════════════════════════════════════════════════════╗
#   🚀  TOKEN
# ╚═══════════════════════════════════════════════════════════════╝
TOKEN = os.environ.get("DISCORD_TOKEN", "TU_TOKEN_AQUI")
bot.run(TOKEN)
