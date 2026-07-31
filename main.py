import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import os
from datetime import datetime, timezone, timedelta, time
import random
import google_sheet
import csv
import json
from classes import User
from pathlib import Path
from colorama import Fore, Style, init
import pdf

init(autoreset=True)

load_dotenv()
token = os.getenv("DISCORD_TOKEN")

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

medium_perm = "Heidrun's Bekanta"
high_perm = "Heidrun's Vän"

channel_ids = {}
user_ids = {}       # guild_id: {username: id}
reminders = {}
weekly_reminders = {}
missions = {}       # guild_id: {public: private}

# LOGIC
def get_type(description):
    event_type = ""
    reminder = 0
    is_type = False
    for c in description.lower():
        if c == "[":
            is_type = True
            continue
        if c == "]":
            is_type = False
            break
        if is_type:
            event_type += c
    contents = event_type.split(",")
    if len(contents) == 1:
        reminder = 60
        event_manager = ""
    elif len(contents) == 2:
        _contents = [None, None, None]
        for i, part in enumerate(contents):
            try:
                _part = int(part)
                _contents[1] = _part
            except ValueFAILURE:
                _contents[i] = part
        event_type, reminder, event_manager = _contents
    else:
        event_type, reminder, event_manager = contents
    return event_type, reminder, event_manager

def save_creds():
    with open("guild_credentials.json", "w", encoding="utf-8") as f:
        json.dump(google_auth, f, indent=4)

def save_registry():
    with open("registrations.json", "w", encoding="utf-8") as f:
        json.dump(announcement_channels, f, indent=4)

def save_users():
    with open("user_info.json", "w", encoding="utf-8") as f:
        json.dump(user_info, f, indent=4, ensure_ascii=False)

def log(category: str, msg: str) -> None:
    category = category.upper()
    if category == "WARNING":
        fore = Fore.RED
    elif category == "FAILURE":
        fore = Fore.RED
    elif category == "NOTICE":
        fore = Fore.BLUE
    elif category == "SUCCESS":
        fore = Fore.GREEN
    else:
        fore = Fore.WHITE
    print(f"Heidrun || {fore}{category.upper()}{Style.RESET_ALL} || {msg}")

def get_channel(guild, name):
    channels = channel_ids.get(guild)
    if channels is None:
        return None
    partial_matches = []
    for channel, _id in channels.items():
        channel_name = channel
        if channel_name == name.lower():
            return _id       # Return if direct match
        for part in channel_name.split("-"):
            if part in name.lower():
                partial_matches.append(channel)

    log("NOTICE", f"Matcher funna för kanalsökning '{name}': {partial_matches}")

    if len(partial_matches) == 0:
        return None     # If absolut 0 matches

    if len(partial_matches) == 1:
        return channels[partial_matches[0]]
    else:
        return None     # If more than one match is found

async def collect_info(user):
    log("NOTICE", "Bekräftat. Påbörjar insamlning av data från användare.")
    questions = {
        "name": "För och efternamn *(Sven Svensson)*:",
        "number": "Telefonnummer *(076 xxx xx xx)*:",
        "mail": "Mailaddress *(sven@gmail.com)*:",
        "bank": "Bank *(SEB)*:",
        "cnumber": "Clearing Nummer *(5432)*:",
        "anumber": "Kontonummer *(01 234 56)*:"
    }

    answers = {
        "name": "",
        "number": "",
        "mail": "",
        "bank": "",
        "cnumber": "",
        "anumber": ""
    }

    await user.send("Jag kommer nu fråga dig lite frågor, jag kräver att du svarar genom att bara skriva i chatten.\nOm du vill avbryta vid något tillfälle svara med **AVBRYT**, eller vänta 5min.")
    def check(message):
        return (message.author == user and isinstance(message.channel, discord.DMChannel))
    for tag, question in questions.items():
        await user.send(question)
        try:
            response = await bot.wait_for("message", timeout=300, check=check)
            if response.content.lower() == "avbryt":
                await user.send("Jag har inte all tid i världen... Skriv igen senare om du fortfarande är intereserad, sluta slösa min tid.")
                return
            answers[tag] = response.content
        except TimeoutError:
            await user.send("Jag har inte all tid i världen... Skriv igen senare om du fortfarande är intereserad, sluta slösa min tid.")
            return

    await user.send(f"## Kontrollera gärna att dessa uppgifter stämmer: \n**Namn:** {answers['name']}\n**Telefonnummer:** {answers['number']}\n**Mail:** {answers['mail']}\n**Bank:** {answers['bank']}\n**Clearing Nummer:** {answers['cnumber']}\n**Kontonummer:** {answers['anumber']}\n\n**Stämmer dessa? (Y/N):**")
    try:
        response = await bot.wait_for("message", timeout=300, check=check)
        if response.content.lower() not in ["j", "y", "ja", "yes"]:
            await user.send("Jaha, då får du gärna kika över din information och sluta slösa min tid. Är du så urusel att du inte kan din egna information? Du får skriva *!register info* igen om du vill testa en gång till.")
            return
    except TimeoutError:
        await user.send("Jag har inte all tid i världen... Skriv igen senare om du fortfarande är intereserad, sluta slösa min tid.")
        return
    user_info[user.id] = answers
    await user.send("Dåså, då har jag registrerat dig. Du kan nu använda *!reimbursement* för att automatiskt fylla i ersättningsblanketter. Om du någonsin vill ta bort din information så kan du skriva *!unregister info*")
    save_users()

# SAVEFILES
if os.path.exists("guild_credentials.json"):
    log("NOTICE", "Läser in Google Service Account Credentials för registrerade guilder...")
    with open("guild_credentials.json", "r", encoding="utf-8") as f:
        google_auth = {int(k): v for k, v in json.load(f).items()}
    log("SUCCESS", "Bekräftat. Inläsning av Google Service Accounts lyckad.")
else:
    google_auth = {}

if os.path.exists("registrations.json"):
    log("NOTICE", "Läser in registrerade notiskanaler för guilder...")
    with open("registrations.json", "r", encoding="utf-8") as s:
        announcement_channels = {int(guild_id): data for guild_id, data in json.load(s).items()}
    log("SUCCESS", "Bekräftat. Inläsning av notiskanaler lyckad.")
else:
    announcement_channels = {}      # guild.id: {type: {tag: channel_id}}

if os.path.exists("user_info.json"):
    log("NOTICE", "Läser in registrerade användare...")
    with open("user_info.json", "r", encoding="utf-8") as s:
        user_info = {int(user_id): data for user_id, data in json.load(s).items()}
    log("SUCCESS", "Bekräftat. Inläsning av användare lyckad.")
else:
    user_info = {}      # user_id: User

# INTENTS
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guild_scheduled_events = True

bot = commands.Bot(command_prefix="!", intents=intents)

# AUTO
@bot.event
async def on_ready():
    log("NOTICE", "Registrerar kanaler och användare...")
    for guild in bot.guilds:
        channel_ids[guild.id] = {}
        user_ids[guild.id] = {}
        missions[guild.id] = {}
        if guild.id not in announcement_channels:
            announcement_channels[guild.id] = {"announcement": {}}
        for channel in guild.channels:
            channel_ids[guild.id][channel.name] = channel.id
        for member in guild.members:
            user_ids[guild.id][member.name] = member.id
        
    if not remind_event.is_running():
        remind_event.start()
    if not check_forms.is_running():
        check_forms.start()
    log("SUCCESS", "Redo att fördela bäsk <3")

@bot.event
async def on_member_join(member):
    await member.send(f"Salvete, {member.name}. Benedicat te hircus sanctus. Se till att du läser reglerna får våran kära server. Glöm inte att byta ditt discord namn på servern till ditt riktiga namn, och gör gärna onboardingen så att du får lite roller.")

# COMMANDS
@bot.command()
async def dd1310(ctx):
    role = discord.utils.get(ctx.guild.roles, name="Daniel's Lärjung")
    if role:
        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            await ctx.send(f"{ctx.author.mention}, jag skannade din Canvas, och det ser fortfarande ut som att du är kursregistrerad. Vill du verkligen kasta bort potentiell kunskap genom att ta bort rollen? Uruselt... Nåväl, till din önskan.")
        else:
            await ctx.author.add_roles(role)
            await ctx.send(f"{ctx.author.mention} vad roligt att du söker högre kunskap! Jag har nu gett dig rollen {role}. Du kan hitta den dedikerade Asse kanalen längre ner.")
    else:
        await ctx.send("Jag kunde tyvärr inte hitta den rollen...")

@bot.command()
async def notis(ctx):
    role = discord.utils.get(ctx.guild.roles, name="Heidrun's Följare")
    if not role:
        await ctx.send("Jag kunde tyvärr inte hitta den rollen...")
        return

    if role not in ctx.author.roles:
        await ctx.author.add_roles(role)
        await ctx.send(f"Mindre uruselt {ctx.author.mention}. Nu kommer du få notis när jag skickar ut påminnelser sen.")
        log("NOTICE", f"Individ {ctx.author.id} i guild {ctx.guild.id} har fått rollen {role.id}")
    else:
        await ctx.author.remove_roles(role)
        await ctx.send(f"Nu kommer du inte få några notiser, det vet du va {ctx.author.mention}? Äntligen någon som har koll i kalendern iallafall...")
        log("NOTICE", f"Individ {ctx.author.id} i guild {ctx.guild.id} har förlorat rollen {role.id}")

@bot.command()
async def thread(ctx, _channel, mission, *, _args):
    log("NOTICE", f"Trådskapelseförfrågan antagen: {_channel}, {mission}, {_args}")
    description = ""
    try:
        args = [s.strip() for s in _args.split(",")]
        if not args:
            await ctx.send("Du kan inte använda komman i din beskrivning eller namn, det vet ju vem som helst!")
            return
        if len(args) == 1:
            name = args[0]
        elif len(args) == 2:
            name, description = args
        elif len(args) > 2:
            name = args[0]
            description = ", ".join(args[1:])
        else:
            await ctx.send("Du kan inte använda komman i din beskrivning eller namn, det vet ju vem som helst!")
            return
        log("SUCCESS", f"Tråd skapad i {_channel} i guild {ctx.guild.name}")
    except ValueError:
        await ctx.send("Kika syntaxen igen, något gick snett.")
        log("FAILURE", "ValueFAILURE inträffade vid trådskapelse.")
        return

    channel_id = get_channel(ctx.guild.id, _channel)
    if not channel_id:
        await ctx.send(f"Jag kunde tyvärr inte hitta någon kanal som heter '{_channel}'.")
        return
    channel = bot.get_channel(channel_id)
    if not channel or not name or not mission:
        await ctx.send("Det verkar som att du inte gav rätt syntax där. Är du läskunnig? Isåfall borde du läsa dokumentationen igen. Jag kräver kanal, namn, om det är ett uppdrag, och om du vill en beskrivning.")
        return
    if not isinstance(channel, discord.ForumChannel):
        await ctx.send(f"Håll i hatten pojk, alla vet ju att {channel.name} inte är ett Forum... Testa en annan kanal innan jag blir galen av din idiokrati, det är smittsamt du vet.")
        return

    if mission.lower() == "y":
        name = f"Uppdrag - {name}"

    if description:
        await channel.create_thread(
            name=name,
            content=description
        )
    else:
        await channel.create_thread(
            name=name,
            content=f"Här är din nya tråd {ctx.author.mention}. Glöm inte att lägga till lämplig TAG med hjälp av !tag. Skicka en bild och använda !thumbnail för att sätta en cover bild."
        )

@bot.command()
async def thumbnail(ctx):
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("Vem tror du att du är? Det är ju självfallet att man måste använda detta kommando i en forum tråd!")
        return

    if not ctx.message.reference:
        await ctx.send("Du måste givetvis svara en bild för att använda kommandot, har du inte läst dokumentationen?")
        return

    message = await ctx.channel.fetch_message(
        ctx.message.reference.message_id
    )

    if not message.attachments:
        await ctx.send("Men du, det där är ju ingen bild... Om du ska fortsätta så här kommer jag ")
        return

    image = await message.attachments[0].to_file()

    # Get first message in thread
    messages = [
        message async for message in ctx.channel.history(
            limit=1,
            oldest_first=True
        )
    ]

    if not messages:
        await ctx.send("Jag kunde tyävrr inte hitta första meddelandet, synen blir sämre när man blir äldre du vet.")
        return

    first_message = messages[0]

    # Edit first message
    await first_message.edit(
        attachments=[image]
    )

@bot.command()
async def status(ctx, *, status):
    STATUS_TAGS = {
        "klar": "KLAR",
        "påbörjad": "PÅBÖRJAD",
        "ej påbörjad": "EJ PÅBÖRJAD"
    }

    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("Vem tror du att du är? Det är ju självfallet att man måste använda detta kommando i en forumtråd!")
        return

    status = status.lower()

    if not status:
        await ctx.send("Du måste ju givetvis också säga vilket status du vill sätta. Tror du att jag kan läsa dina tankar eller?")
        return

    if status not in STATUS_TAGS:
        await ctx.send("Sådant status har vi inte min pojk. Använd: klar, påbörjad, ej påbörjad")
        return

    thread = ctx.channel
    forum = thread.parent

    # Find the status tag objects
    status_tags = {
        tag.name.lower(): tag
        for tag in forum.available_tags
        if tag.name.lower() in [x.lower() for x in STATUS_TAGS.values()]
    }

    new_status_tag = status_tags[STATUS_TAGS[status].lower()]

    # Keep all non-status tags
    new_tags = [
        tag for tag in thread.applied_tags
        if tag.name.lower() not in [x.lower() for x in STATUS_TAGS.values()]
    ]

    # Add new status tag
    new_tags.append(new_status_tag)

    # Apply tags
    await thread.edit(applied_tags=new_tags)

    await ctx.send(f"Status ändrad till {new_status_tag.name}.")

@bot.command()
async def tag(ctx, *, tag):
    if not isinstance(ctx.channel, discord.Thread):
        await ctx.send("Vem tror du att du är? Det är ju självfallet att man måste använda detta kommando i en forumtråd!")
        return

    thread = ctx.channel
    forum = thread.parent
    tags = forum.available_tags
    if tag not in [tag.name.lower() for tag in tags]:
        await ctx.send("Sådant tag har vi inte min pojk. Kika igen vilka som finns, jag orkar inte skapa några nya.")
        return
    new_tags = [_tag for _tag in thread.applied_tags]
    for _tag in tags:
        if _tag.name.lower() == tag:
            new_tag = _tag
            break
    else:
        await ctx.send("Sådant tag har vi inte min pojk. Kika igen vilka som finns, jag orkar inte skapa några nya.")
        return

    for i, _tag in enumerate(new_tags):
        if _tag.name.lower() == tag:
            new_tags.pop(i)
            break
    else:
        new_tags.append(new_tag)

    await thread.edit(applied_tags=new_tags)

@bot.command()
@commands.has_role(high_perm)
async def reggoogle(ctx):
    log("NOTICE", f"Länkar Google Service Account till guild {ctx.guild.id}")
    if not ctx.message.attachments:
        await ctx.send("Hur tänker du att jag ska registrera ditt konto om du inte ens skickar JSON filen för ditt service konto?")
        log("WARNING", "Kunde inte länka Google Service Account pågrund av bristande crediter.")
        return

    attachment = ctx.message.attachments[0]

    try:
        data = json.loads(await attachment.read())
    except json.JSONDecodeFAILURE:
        await ctx.send("Men det var som sjutton... Du är teknolog men kan inte formatera en JSON fil korrekt...")
        log("FAILURE", "Kunde inte läsa in JSON fil för google registrering.")
        return

    path = Path("auths")
    path.mkdir(exist_ok=True)

    filename = path / f"{ctx.guild.id}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    google_auth[ctx.guild.id] = str(filename)

    with open("guild_credentials.json", "w", encoding="utf-8") as file:
        json.dump(google_auth, file, indent=4)

    await ctx.send(f"Bekräftat. Jaha, då har jag nu länkat service kontot {ctx.author.mention}. Nu kan ni använda funktionerna som länkandet till google forms och kalender.")
    log("SUCCESS", f"Google registrering länkad för guild {ctx.guild.id}")

    await ctx.message.delete()

@bot.command()
@commands.has_role(high_perm)
async def unreggoogle(ctx):
    log("NOTICE", f"Raderar google länk för guild {ctx.guild.id}")
    guild_id = ctx.guild.id
    if guild_id not in google_auth:
        await ctx.send("Men hallå, har du en skruv lös i skallen? Ni har ju inte länkat något konto. Använd !reggoogle först för att registrera en länk.")
        log("WARNING", f"Ingen google länk är registrerad för guild {ctx.guild.id}. Avbryter radering.")
        return

    filepath = google_auth[guild_id]
    if os.path.exists(filepath):
        os.remove(filepath)

    del google_auth[guild_id]
    log("SUCCESS", f"Google länk för guild {ctx.guild.id} raderat.")

    save_creds()

    await ctx.send("Nu kan du känna dig säker, jag har raderat all information gällande erat service konto.")

@bot.command()
async def register(ctx, r_type: str, tag: str = None, value: discord.TextChannel = None):
    r_type = r_type.lower()
    log("NOTICE", f"Påbörjar registrering av {r_type}")
    if tag is not None:
        tag = tag.lower()
        channels = announcement_channels[ctx.guild.id]
        if channels.get(r_type) is None:
            announcement_channels[ctx.guild.id][r_type] = {}
    if r_type == "announcement" and tag is not None and value is not None:
        channels = announcement_channels[ctx.guild.id]
        if channels[r_type].get(tag) is None:
            announcement_channels[ctx.guild.id][r_type][tag] = value.id
        else:
            log("NOTICE", f"Överskrider registrering av notiskanal {tag}.")
            announcement_channels[ctx.guild.id][r_type][tag] = value.id
        log("SUCCESS", f"Registrering av notiskanal {tag} till {value.name} lyckad.")
        await ctx.send(f"Bekräftat. Notiskanal {tag} registrerad till kanal {value.id}.")
    elif r_type == "info":
        if ctx.guild is not None:
            await ctx.author.send("Du tänker inte skicka dina privata uppgifter till allmänheten va?\nSkriv istället *!register info* här så håller vi det mellan oss två.")
            return
        await collect_info(ctx.author)
    else:
        log("FAILURE", f"Typ {r_type} finns inte i systemet.")
    save_registry()

@bot.command()
async def registration(ctx, tag):
    if tag == "server":
        linked = True if google_auth.get(ctx.guild.id) is not None else False
        info_qp = f"<#{announcement_channels[ctx.guild.id]["announcement"].get("info-qp")}>" if announcement_channels[ctx.guild.id]["announcement"].get("info-qp") is not None else None
        info_qp_intern = f"<#{announcement_channels[ctx.guild.id]["announcement"].get("info-qp-intern")}>" if announcement_channels[ctx.guild.id]["announcement"].get("info-qp-intern") is not None else None
        info_styret = f"<#{announcement_channels[ctx.guild.id]["announcement"].get("info-styret")}>" if announcement_channels[ctx.guild.id]["announcement"].get("info-styret") is not None else None
        info_sektionen = f"<#{announcement_channels[ctx.guild.id]["announcement"].get("info-sektionen")}>" if announcement_channels[ctx.guild.id]["announcement"].get("info-sektionen") is not None else None
        await ctx.send(f"# Registration {ctx.guild.name}\n## General Info\nMembers: {ctx.guild.member_count} / {ctx.guild.max_members}\nBitrate Limit: {ctx.guild.bitrate_limit}\nFilesize Limit: {ctx.guild.filesize_limit} bytes ({round(ctx.guild.filesize_limit / 1000000)} MB)\nGoogle Link: {linked}\n## Announcement Channels\nInfo-Sektionen: {info_sektionen}\nInfo-QP: {info_qp}\nInfo-QP-Intern: {info_qp_intern}\nInfo-Styret: {info_styret}")
    elif tag == "info":
        user = user_info.get(ctx.author.id)
        if user is None:
            await ctx.send(f"Du har ännu inte registrerat dig. Använd *!register info* för att registrera dig.")
        else:
            await ctx.send(f"# Registration {ctx.author.name}\n**Name:** {user["name"]}\n**Telefonnummer:** {user["number"]}\n**Mail:** {user["mail"]}\n**Bank:** {user["bank"]}\n**Clearing Nummer:** {user["cnumber"]}\n**Kontonummer:** {user["anumber"]}")

@bot.command()
async def reimbursement(ctx, place, recipient, total, *, description):
    log("NOTICE", f"Förbereder ersättningsblankett för {ctx.author.id}")
    def check(message):
        return (message.author == ctx.author)
    try:
        await ctx.send("Har du fått godkänt från ditt kostnadsställe för detta köp? (Y/N): ")
        response = await bot.wait_for("message", timeout=300, check=check)
        if response.content.lower() not in ["y", "j", "ja", "yes"]:
            await ctx.send("Men vad i... Om det inte är godkänt kan jag inte skapa en ersättningsblankett åt dig.")
            return
    except TimeoutError:
        await ctx.send(f"{ctx.author.mention} Jag har inte all tid i världen... Skriv igen senare om du fortfarande är intereserad, sluta slösa min tid.")
        return
    
    try:
        await ctx.send("Jag kommer skicka ersättningsblanketten till denna kanal, vilket betyder att viss del av din privata information kommer delas, är du okej med det? (Y/N): ")
        response = await bot.wait_for("message", timeout=300, check=check)
        if response.content.lower() not in ["y", "j", "ja", "yes"]:
            await ctx.send("Jag förstår, du kan skriva detta kommando igen privat till mig så skickar jag det där.")
            return
        data = user_info.get(ctx.author.id)
        if data is None:
            await ctx.send("Du har inte registrerat din information. Kalla inte på mig igen förens du gjort det... *!register info*.")
        pdf.create_reimbursement(ctx.author, True, place, data["name"], data["number"], data["mail"], data["bank"], data["cnumber"], data["anumber"], recipient, total, description)
        filepath = Path(f"reimbursement-{ctx.author.id}.pdf")
        log("SUCCESS", f"Ersättningsblankett skapad för individ {ctx.author.id}.")
    except TimeoutError:
            await ctx.send(f"{ctx.author.mention} Jag har inte all tid i världen... Skriv igen senare om du fortfarande är intereserad, sluta slösa min tid.")
            return

    try:
        await ctx.send("Okej, jag har nu skapat en ersättningsblankett åt dig. Kom ihåg att du måste ge den till rätt attestant:", file=discord.File(f"reimbursement-{ctx.author.id}.pdf"))
    finally:
        log("NOTICE", f"Raderar Erästtningsblankett för användare {ctx.author.id}.")
        if os.path.exists(filepath):
            os.remove(filepath)
            log("SUCCESS", "Lyckad, fil har raderats.")
        else:
            log("FAILURE", f"Kunde inte hitta fil {filepath}")
        
# ERRORS
        
# REMINDERS
@tasks.loop(minutes=1)
async def remind_event():
    now = datetime.now(timezone.utc)
    await remind_calender()
    log("NOTICE", "Läser events...")
    for guild in bot.guilds:
        for event in guild.scheduled_events:
            log("NOTICE", f"Checkar event {event.name}")
            if not reminders.get(event.id):
                reminders[event.id] = False
            if not reminders[event.id]:
                log("NOTICE", f"Förbereder påminnelse för {event.name}")
                description = event.description.lower()
                event_type, reminder, event_manager = get_type(description)
                if event.start_time - timedelta(minutes=int(reminder)) >= now or not event_type:
                    log("WARNING", f"Event {event.name} är inte aktuellt, skippar...")
                    continue
                time_left = event.start_time - datetime.now(timezone.utc)
                minutes = int(time_left.total_seconds() // 60)
                version_first = random.randint(1, 5)
                version_second = random.randint(1, 5)
                role = discord.utils.get(guild.roles, name="Heidrun's Följare")
                if not role:
                    log("WARNING", "Ingen notisroll finns för Heidrun's Följare, skippar...")
                    continue
                if minutes < 0:
                    log("WARNING", f"Event {event.name} har redan börjat eller varit, skippar...")
                    continue
                if event_type == "pub":
                    workers = description.split("[arbetare]:")[1].strip()
                    log("NOTICE", f"{workers} registrerade för event {event.id}")
                    worker_notis = []
                    for worker in workers.split(","):
                        user = bot.get_user(user_ids[guild.id][worker])
                        if user:
                            worker_notis.append(user)

                    channel = announcement_channels[guild.id]["announcement"].get("info-qp")
                    if channel is None:
                        log("FAILURE", f"Kunde inte hitta notiskanal för 'qlubbmästeriet utlysande' i guild {guild.id}")
                        continue
                    channel = bot.get_channel(announcement_channels[guild.id]["announcement"]["info-qp"])
                    messages_first = {
                        1: f"# ---=PUB=---\n{role.mention} Har du sätt? Det är ju för sjutton **{event.name}** idag! Baren slår upp dörrarna om ynka **{minutes} minuter**, och här sitter ni som om ni hade all tid i världen... Dagens generation...\nVisste ni förresten att vi faktiskt har både kall öl och riktig bäsk? Jo minsann, sådant som folk förr i tiden kunde uppskatta, innan alla började springa omkring med sina märkliga drycker och trodde de var något.",
                        2: f"# ---=PUB=---\n{role.mention} Har ni hört det här? Det är ju **{event.name}** idag! Och som vanligt verkar folk behöva bli påminda om sådant som faktiskt står i kalendern. Baren öppnar om **{minutes} minuter**, så det vore väl inte för mycket begärt att ni kunde masa er i tid för en gångs skull.\nVo har både kall öl och bäsk, minsann. Riktiga drycker, sådana som folk uppskattade innan allting skulle vara så märkvärdigt och modernt.",
                        3: f"# ---=PUB=---\n{role.mention} Men snälla nån... har ni helt missat att det är **{event.name}** idag? Det är ju nästan imponerande hur dåligt folk kan hålla reda på enkla saker. Baren öppnar om **{minutes} minuter**, och jag antar att några av er fortfarande sitter hemma och funderar på vad ni ska göra ikväll. Jag kan tala om vad ni ska göra: ni ska komma till puben.\nDär finns både kall öl och bäsk, om någon fortfarande vet vad en riktig dryck är.",
                        4: f"# ---=PUB=---\n{role.mention} Jag antar att jag får vara den som påminner er igen... Det är nämligen **{event.name}** idag. Ja, faktiskt. Baren öppnar om **{minutes} minuter**, så om ni tänkte komma får ni väl börja röra på er nu istället för att sitta där och fundera.\nOch ja, vi har både kall öl och bäsk. Jag vet, helt otroligt att någon fortfarande anstänger sig och ordnar trevliga saker.",
                        5: f"# ---=PUB=---\n{role.mention} Kära nån, på min tid i Sn@quan behövde man minsann inte påminna folk om att det var **{event.name}**. Då visste man när det var dags att dyka och umgås som vanligt folk. Men tiderna förändras väl, antar jag. Därför kommer här en påminnelse: **DET ÄR PUB IDAG.**. Baren öppnar om **{minutes} minuter**. Det är inte direkt gott om tid, så ni får väl slita er från era soffor och annat trams. Vi serverar kall öl och bäsk, precis som sig bör."
                    }
                    messages_second = {
                        1: f"Ni får väl masa er dit en stund åtminstone. Det skadar ingen att visa sig bland folk ibland, vet ni. Ni kan till och med hälsa på de stackars tappra själar som står och sliter bakom baren ikväll: {" ".join(user.mention for user in worker_notis)}.",
                        2: f"Kom nu förbi en liten stund åtminstonde. Det är faktiskt trevligt att se era ansikten ibland, även om vissa av er verkar göra allt för att undvika folk. Bakom baren står kvällens tappra arbetare, som offrar sin dyrbara tid för att hålla ordning på eländet: {" ".join(user.mention for user in worker_notis)}.",
                        3: f"Ni behöver inte stanna hela kvällen, men nog borde ni kunna visa lite livstecken och hälsa på de stackare som står bakom baren. Följande tappra själar har tagit på sig ansvaret denna gång: {" ".join(user.mention for user in worker_notis)}.",
                        4: f"Ta nu och kom förbi en sväng. Ni kanske till och med råkar ha trevligt, även om det verkar vara en överraskning för vissa. I baren finner ni dessa tappra individer, som valt att spendera sin kväll med att servera en: {" ".join(user.mention for user in worker_notis)}.",
                        5: f"Så kom förbi en stund. Hälsa på folk, drick något gott och visa att ni fortfarande vet hur man beter sig socialt. Bakom baren hittar ni dessa tappra knegare: {" ".join(user.mention for user in worker_notis)}."
                    }
                    if channel:
                        await channel.send(messages_first[version_first])
                        if worker_notis:
                            await channel.send(messages_second[version_second])
                    else:
                        log("FAILURE", f"Kunde inte hitta notiskanal för 'qlubbmästeriet utlysande' i guild {guild.id}")
                        continue
                elif event_type == "sm":
                    channel = announcement_channels[guild.id]["announcement"].get("info-sektionen")
                    if channel is None:
                        log("FAILURE", f"Kunde inte hitta notiskanal för 'utlysande' i guild {guild.id}")
                        continue
                    channel = bot.get_channel(announcement_channels[guild.id]["announcement"].get("info-sektion"))
                    if channel:
                        await channel.send(f"# ---=SM=---\n{role.mention} Har du nu lyckats glömma bort att det är möte idag också? Jösses, man får tydligen hålla reda på allting själv nuförtiden. Mötet börjar om ynka {minutes} minuter, så det vore väl på tiden att du pallrar dig dit och gör din röst hörd.\nVem vet, kanske finns det till och med lite käk att få om du behagar dyka upp. Sådant händer minsann inte varje dag, men ibland försöker folk faktiskt göra något trevligt för en gångs skull.")
                        await channel.send(f"Mötet håller hus i {event.location}, ifall du skulle ha glömt det också. Och om du inte dyker upp... ja, då får jag väl anteckna att du för all framtid är bannlyst från att kalla dig min vän.")
                    else:
                        log("FAILURE", f"Kunde inte hitta notiskanal för 'utlysande' i guild {guild.id}")
                        continue
                elif event_type == "qmöte":
                    channel = announcement_channels[guild.id]["announcement"].get("info-qp-intern")
                    if channel is None:
                        log("FAILURE", f"Kunde inte hitta notiskanal för 'qlubbmästeriet intern' i guild {guild.id}")
                        continue
                    channel = bot.get_channel(announcement_channels[guild.id]["announcement"].get("info-qp-intern"))
                    if channel:
                        await channel.send(f"{role.mention} Glöm inte att det är {event.name}, ses om {minutes} minuter <3.")
                    else:
                        log("FAILURE", f"Kunde inte hitta notiskanal för 'qlubbmästeriet intern' i guild {guild.id}")
                elif event_type == "smöte":
                    channel = announcement_channels[guild.id]["announcement"].get("info-styret")
                    if channel is None:
                        log("FAILURE", f"Kunde inte hitta notiskanal för 'styret' i guild {guild.id}")
                        continue
                    channel = bot.get_channel(announcement_channels[guild.id]["announcement"].get("info-styret"))
                    if channel:
                        await channel.send(f"{role.mention} Glöm inte att det är {event.name}, ses om {minutes} minuter <3.")
                    else:
                        log("FAILURE", f"Kunde inte hitta notiskanal för 'styret' i guild {guild.id}")
                reminders[event.id] = True
                log("SUCCESS", f"Skickade påminnelse för {event.name}")

@tasks.loop(minutes=1)
async def check_forms():
    for guild in bot.guilds:
        log("NOTICE", f"Checkar google sheet for guild {guild.id}")
        auth = google_auth.get(guild.id)
        if auth is None:
            log("WARNING", f"Ingen google länk för guild {guild.id}, skippar...")
            continue
        old_answers = google_sheet.old_read()
        answers = google_sheet.google_read(auth)
        for answer in answers:
            skip = False
            for old_answer in old_answers:
                if answer == old_answer:
                    log("WARNING", "Forum redan registrerad, skippar...")
                    skip = True
                    break
            if skip:
                continue

            log("NOTICE", f"Nytt Black Märquet uppdrag hittat för guild {guild.id}")

            channels = {
                "Märke / Patch": "💡idéer-märquen",
                "Dokument / Document": "💡idéer-dokument",
                "PR": "💡idéer-pr",
                "Annat / Other": "💡idéer-dokument"
            }

            channel = channels.get(answer.mission)
            if not channel:
                continue

            channel = bot.get_channel(channel_ids[guild.id][channel])
            priv_channel = channel_ids[guild.id].get("bm-uppdrag")
            if priv_channel is None:
                continue
            priv_channel = bot.get_channel(priv_channel)

            tags = channel.available_tags
            applied_tags = []
            for tag in tags:
                if tag.name == "Uppdrag" or tag.name == "EJ PÅBÖRJAD":
                    applied_tags.append(tag)

            if not answer.discord:
                content = f"{answer.name} från {answer.represent} skickade precis in en förfrågan! De frågar att vi designar {answer.mission} åt dem. Så här skrev de: '*{answer.description}*', verkar ju lite knasigt men vad vet jag."
                priv_thread = None
            else:
                user = user_ids[guild.id].get(answer.username.lower())
                role = discord.utils.get(guild.roles, name="Black Märquet")
                if role is None:
                    continue
                priv_thread = await priv_channel.create_thread(
                    name=f"Uppdrag - {answer.mission} ({answer.represent})",
                    type=discord.ChannelType.private_thread
                )
                await priv_thread.send(f"Hej <@{user}>. Tack för din förfråga till {role.mention}. I denna kanal kommer all kommunikation ske. Black Märquet arbetar i en annan kanal, men kommer skicka uppdateringar kring ditt ärende här. Om du vill lägga till en till person till tråden kan du göra så genom att enkelt @'a dem här.")
                content = f"{answer.name} från {answer.represent} skickade precis in en förfrågan! De frågar att vi designar {answer.mission} åt dem. Så här skrev de: '*{answer.description}*', verkar ju lite knasigt men vad vet jag. Jag har skapat en separat kommunikationstråd med kunden: {priv_thread.mention}."
            pub_thread = await channel.create_thread(
                name=f"Uppdrag - {answer.mission} ({answer.represent})",
                content=content,
                applied_tags=applied_tags
            )

            log("SUCCESS", f"Ny tråd skapad för Black Märquet Uppdrag i guild {guild.id}")

            fields=["Name", "Represent", "Mission", "Description", "Discord", "Username", "Private", "Public"]
            with open("previous_projects.csv", "a", encoding="utf-8") as save:
                writer = csv.DictWriter(save, fieldnames=fields)
                if priv_thread is None:
                    writer.writerow({"Name": answer.name, "Represent": answer.represent, "Mission": answer.mission, "Description": answer.description, "Discord": answer.discord, "Username": answer.username, "Private": priv_thread, "Public": pub_thread.thread.id})
                    missions[guild.id][pub_thread.thread.id] = priv_thread
                else:
                    missions[guild.id][pub_thread.thread.id] = priv_thread.id
                    writer.writerow({"Name": answer.name, "Represent": answer.represent, "Mission": answer.mission, "Description": answer.description, "Discord": answer.discord, "Username": answer.username, "Private": priv_thread.id, "Public": pub_thread.thread.id})
                    await priv_thread.send(f"**Not för Black Märquet** || Arbetstråd: {pub_thread.thread.mention}")

async def remind_calender():
    now = datetime.now(timezone.utc)
    today = datetime.today().weekday()
    log("NOTICE", "Läser kalendrar...")
    if today != 0 or not time(7, 0) <= now.time() <= time(7, 2):
        return      # Skip if it's not monday or time is not around 7
    for guild in bot.guilds:
        events = []
        channel = bot.get_channel(channel_ids[guild.id][INFO])
        if channel is None:
            continue

        for event in guild.scheduled_events:
            log("NOTICE", f"Checkar event {event.name} för guild {guild.id}")
            if not weekly_reminders.get(event.id):
                weekly_reminders[event.id] = False

            if weekly_reminders[event.id]:
                continue        # Reminder already sent

            description = event.description.lower()
            event_type, foo, event_manager = get_type(description)
            if event.start_time <= now or not event_type:
                continue        # Skip if event has happened or not a valid event

            if event.start_time < now + timedelta(weeks=1):
                events.append((event, event_type, event_manager))

        message = "## Dag | Event | Tid | Plats | Arrangör\n"
        for event, event_type, event_manager in sorted(events, key=lambda x: x[0].start_time):
            message += f"{event.start_time.strftime("%A")} | {event.name} | {event.start_time.strftime("%H:%M")} | {event.location} | {event_manager.upper()}\n"
        if events:
            await channel.send("# Händelser denna vecka\n God morgon alla. Solen är uppe, så det är dags att palla sig till skolan. Jag vet att ni alla är rätt så urusla att kika i kalendern, så jag har sumerat upp händelserna för denna vecka.\n@everyone")
            await channel.send(message)
        else:
            await channel.send("# Händelser denna vecka\n God morgon alla. Sektionen är något urusla och har inte planerat något för veckan, så ni får ruttna hemma tills något mindre uruselt händer. @everyone")


bot.run(token, log_handler=handler, log_level=logging.DEBUG)