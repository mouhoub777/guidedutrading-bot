import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, MessageReactionHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler, ChatMemberHandler
import asyncio
from dotenv import load_dotenv
from collections import defaultdict, deque
import time

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://guidedutrading-bot.onrender.com")
PORT = int(os.getenv("PORT", 8443))

# ADMINS - Exemptés de modération
ADMINS = [4943731, 7580303994]

user_warnings = defaultdict(int)
user_messages = defaultdict(lambda: deque(maxlen=10))
user_data = defaultdict(dict)
user_last_message_time = defaultdict(float)

BANNED_WORDS = [
    'connard', 'salope', 'pute', 'merde', 'putain', 'con', 'connasse',
    'batard', 'enculé', 'fdp', 'ntm', 'fils de pute', 'ta gueule',
    'ferme ta gueule', 'va te faire', 'nique', 'pd', 'tapette',
    'enfoiré', 'casse toi', 'va chier', 'débile', 'crétin', 'idiot',
    'salaud', 'pourriture', 'ordure', 'connerie', 'merdique'
]

# ====================== SYSTÈME DE BIENVENUE ======================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start avec gestion du paramètre welcome"""
    user = update.effective_user
    
    if context.args and context.args[0] == 'welcome':
        print(f"🆕 NOUVEAU via lien : {user.first_name} (@{user.username})")
        
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🆕 <b>Nouveau visiteur !</b>\n👤 {user.first_name}\n🆔 {user.id}\n📝 @{user.username or 'N/A'}\n\n🔗 Via lien d'invitation",
            parse_mode='HTML'
        )
        
        await send_welcome_message(update, context, user)

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user):
    """Envoie UNIQUEMENT le message de bienvenue avec question source"""
    keyboard = [
        [InlineKeyboardButton("📺 YouTube", callback_data="source_youtube")],
        [InlineKeyboardButton("📸 Instagram", callback_data="source_instagram")],
        [InlineKeyboardButton("🐦 Twitter/X", callback_data="source_twitter")],
        [InlineKeyboardButton("📱 Telegram", callback_data="source_telegram")],
        [InlineKeyboardButton("🌐 Site Web", callback_data="source_siteweb")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"👋 <b>Bienvenue {user.first_name} !</b>\n\n"
        f"Merci de t'intéresser à Guide Du Trading 🚀\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"Pour mieux te connaître :\n\n"
        f"📍 <b>Comment as-tu découvert Guide Du Trading ?</b>"
    )
    
    await update.message.reply_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def detect_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Détecte les nouveaux membres du GROUPE"""
    try:
        result = update.chat_member
        
        if result.chat.id != GROUP_ID:
            return
        
        was_member = result.old_chat_member.status in ["member", "administrator", "creator"]
        is_member = result.new_chat_member.status in ["member", "administrator", "creator"]
        
        if not was_member and is_member:
            user = result.new_chat_member.user
            
            if user.is_bot:
                return
            
            print(f"✅ NOUVEAU MEMBRE DANS LE GROUPE: {user.first_name} (@{user.username})")
            
            if user.id in user_data:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"✅ <b>A rejoint le groupe !</b>\n👤 {user.first_name}\n🆔 {user.id}\n📝 @{user.username or 'N/A'}\n\n📊 Source: {user_data[user.id].get('source', 'inconnue').upper()}",
                    parse_mode='HTML'
                )
            else:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=f"⚠️ <b>A rejoint SANS passer par le bot !</b>\n👤 {user.first_name}\n🆔 {user.id}\n📝 @{user.username or 'N/A'}",
                    parse_mode='HTML'
                )
            
    except Exception as e:
        print(f"❌ Erreur détection: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la réponse"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    data = query.data
    
    if data.startswith("source_"):
        source = data.replace("source_", "")
        user_data[user_id]['source'] = source
        
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"📊 <b>Source trackée!</b>\n👤 {query.from_user.first_name}\n🆔 {user_id}\n📍 {source.upper()}",
            parse_mode='HTML'
        )
        
        GROUP_INVITE_LINK = "https://t.me/+sEW_LL0F4LQyZmY0"
        keyboard_groupe = [[InlineKeyboardButton("👥 REJOINDRE LE GROUPE 🔥", url=GROUP_INVITE_LINK)]]
        await query.edit_message_text(
            text="✅ <b>Merci d'avoir répondu !</b>\n\nVoici le lien du groupe 👇",
            reply_markup=InlineKeyboardMarkup(keyboard_groupe),
            parse_mode='HTML'
        )
        
        await send_tmgm_comparison(query, context, user_id)

async def send_tmgm_comparison(query, context, user_id):
    """Envoie le comparatif complet TMGM"""
    
    keyboard = [
        [InlineKeyboardButton("🎁 Ouvrir compte TMGM", url="https://affiliate.tmgm.com/visit/?bta=35488&brand=tmgm")],
        [InlineKeyboardButton("🎯 Tester en DÉMO", url="https://affiliate.tmgm.com/visit/?bta=35488&brand=tmgm")],
        [InlineKeyboardButton("💬 Me contacter", url="https://t.me/Guidedutrading")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"<b>Si tu veux trader avec un courtier fiable et économiser des centaines d'euros par mois, je te recommande TMGM 🏆</b>\n\n"
        f"Voici pourquoi 👇\n\n"
        f"📊 <b>COMPARATIF SPREADS - GOLD (XAUUSD)</b>\n\n"
        f"<i>Profil : 5 trades/jour (1 lot/jour total)</i>\n\n"
        f"<code>Courtier        | Coût/Mois\n"
        f"Vantage         |   $360  ❌\n"
        f"VT Markets      |   $320  ❌\n"
        f"RaiseFX         |   $460  ❌\n"
        f"Fxcess          |   $400  ❌\n"
        f"IronFX          |   $480  ❌\n"
        f"✅ TMGM         |   $160  ✅</code>\n\n"
        f"💰 <b>ÉCONOMIES ANNUELLES :</b>\n"
        f"• vs Vantage : <b>$2,400/an</b>\n"
        f"• vs VT Markets : <b>$1,920/an</b>\n"
        f"• vs RaiseFX : <b>$3,600/an</b>\n"
        f"• vs Fxcess : <b>$2,880/an</b>\n"
        f"• vs IronFX : <b>$3,840/an</b>\n\n"
        f"🏆 <b>POURQUOI TMGM ?</b>\n"
        f"✅ Spreads 50% plus bas\n"
        f"✅ Régulation TIER 1 (ASIC + FCA)\n"
        f"✅ Exécution ultra-rapide\n"
        f"✅ Support 24/7 FR\n\n"
        f"📌 <b>QUEL COMPTE TMGM CHOISIR ?</b>\n\n"
        f"🔥 <b>COMPTE EDGE</b> (Recommandé pour traders actifs)\n"
        f"• Spread Or : 0.94 pip\n"
        f"• Commission : $7 par lot\n\n"
        f"💎 <b>COMPTE CLASSIC</b> (Pour traders occasionnels 1 à 3 trades/semaine)\n"
        f"• Spread Or : ~8 pips\n"
        f"• Commission : $0\n\n"
        f"🛡️ <b>RÉGULATIONS :</b>\n"
        f"✅ TMGM : ASIC + FCA (Tier 1)\n"
        f"🟡 Vantage : ASIC + VFSC\n"
        f"🟡 VT Markets : FSCA + FSC\n"
        f"🟡 Fxcess : CySEC\n"
        f"🟡 IronFX : CySEC + FCA\n"
        f"⚠️ RaiseFX : Offshore\n\n"
        f"💡 <b>Économise jusqu'à $320/mois avec TMGM !</b>"
    )
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"📊 <b>✅ COMPARATIF ENVOYÉ</b>\n\n"
            f"👤 {query.from_user.first_name}\n"
            f"🆔 {user_id}\n"
            f"📝 @{query.from_user.username or 'N/A'}\n"
            f"📍 Source: {user_data[user_id]['source']}\n\n"
            f"🎯 Potentiel converti TMGM"
        ),
        parse_mode='HTML'
    )

# ====================== MODÉRATION ======================

async def add_warning(context, chat_id, user_id, username, reason):
    user_warnings[user_id] += 1
    count = user_warnings[user_id]
    
    if count >= 3:
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 @{username} banni (3 warnings) !"
            )
        except Exception as e:
            print(f"Erreur: {e}")
    else:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Warning {count}/3 pour @{username}\nRaison: {reason}"
        )
    
    await asyncio.sleep(5)
    await msg.delete()

async def check_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if user_id in ADMINS:
        return
    
    try:
        await message.delete()
        await add_warning(context, message.chat_id, user_id,
                        message.from_user.username or message.from_user.first_name,
                        "Lien détecté")
    except Exception as e:
        print(f"Erreur: {e}")

async def check_text_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if user_id in ADMINS:
        return
    
    text = message.text.lower()
    link_patterns = ['http://', 'https://', 'www.', '.com', '.fr', '.net', 't.me/']
    
    if any(pattern in text for pattern in link_patterns):
        try:
            await message.delete()
            await add_warning(context, message.chat_id, user_id,
                            message.from_user.username or message.from_user.first_name,
                            "Lien interdit")
        except Exception as e:
            print(f"Erreur: {e}")

async def check_insults(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if user_id in ADMINS:
        return
    
    text = message.text.lower()
    
    if any(word in text for word in BANNED_WORDS):
        try:
            await message.delete()
            await add_warning(context, message.chat_id, user_id,
                            message.from_user.username or message.from_user.first_name,
                            "Langage inapproprié")
        except Exception as e:
            print(f"Erreur: {e}")

async def check_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if user_id in ADMINS:
        return
    
    current_time = time.time()
    user_messages[user_id].append(current_time)
    
    if len(user_messages[user_id]) >= 5:
        time_diff = current_time - user_messages[user_id][0]
        if time_diff < 10:
            try:
                await message.delete()
                await add_warning(context, message.chat_id, user_id,
                                message.from_user.username or message.from_user.first_name,
                                "Spam détecté")
            except Exception as e:
                print(f"Erreur: {e}")

async def check_caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if user_id in ADMINS:
        return
    
    if message.text:
        text = message.text
        if len(text) > 10:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.7:
                try:
                    warning = await message.reply_text(
                        text=f"⚠️ @{message.from_user.username or message.from_user.first_name}, pas besoin de CRIER ! 🔇"
                    )
                    await asyncio.sleep(3)
                    await warning.delete()
                except Exception as e:
                    print(f"Erreur: {e}")

async def check_forwards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if user_id in ADMINS:
        return
    
    if message.forward_from or message.forward_from_chat:
        try:
            await message.delete()
            await add_warning(context, message.chat_id, user_id,
                            message.from_user.username or message.from_user.first_name,
                            "Messages transférés interdits")
        except Exception as e:
            print(f"Erreur: {e}")

# ====================== RÉACTIONS ======================

async def detecter_reaction_individuelle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not hasattr(update, 'message_reaction') or update.message_reaction is None:
            return
        
        reaction = update.message_reaction
        
        if reaction.user is None:
            return
        
        user = reaction.user
        chat = reaction.chat
        
        emojis = []
        for r in reaction.new_reaction:
            if hasattr(r, 'emoji') and r.emoji:
                emojis.append(r.emoji)
        
        if emojis:
            notif = (
                f"🔔 <b>Réaction GROUPE</b>\n\n"
                f"📢 {chat.title or 'Chat'}\n"
                f"👤 {user.first_name}\n"
                f"📝 @{user.username or 'N/A'}\n"
                f"😊 {' '.join(emojis)}"
            )
            
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=notif, parse_mode='HTML')
            
    except Exception as e:
        print(f"❌ Erreur réaction: {e}")

async def detecter_reaction_anonyme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not hasattr(update, 'message_reaction_count') or update.message_reaction_count is None:
            return
        
        reaction_count = update.message_reaction_count
        chat = reaction_count.chat
        
        reactions = []
        for r in reaction_count.reactions:
            if hasattr(r.reaction, 'emoji') and r.reaction.emoji:
                reactions.append(f"{r.reaction.emoji} x{r.count}")
        
        notif = (
            f"📊 <b>Réactions CANAL</b>\n\n"
            f"📢 {chat.title or 'Canal'}\n"
            f"📊 {', '.join(reactions) if reactions else 'Aucune'}"
        )
        
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=notif, parse_mode='HTML')
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

# ====================== COMMANDES ADMIN ======================

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("❌ Admins uniquement !")
        return
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        await add_warning(context, update.message.chat_id, target.id,
                        target.username or target.first_name, "Warning manuel")
    else:
        await update.message.reply_text("❌ Réponds à un message !")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("❌ Admins uniquement !")
        return
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        try:
            await context.bot.ban_chat_member(chat_id=update.message.chat_id, user_id=target.id)
            msg = await update.message.reply_text(f"🚫 @{target.username or target.first_name} banni !")
            await asyncio.sleep(5)
            await msg.delete()
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur: {e}")
    else:
        await update.message.reply_text("❌ Réponds à un message !")

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("❌ Admins uniquement !")
        return
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        duration = 3600
        
        if context.args:
            d = context.args[0]
            if 'h' in d:
                duration = int(d.replace('h', '')) * 3600
            elif 'm' in d:
                duration = int(d.replace('m', '')) * 60
        
        try:
            await context.bot.restrict_chat_member(
                chat_id=update.message.chat_id,
                user_id=target.id,
                permissions={'can_send_messages': False},
                until_date=int(time.time() + duration)
            )
            msg = await update.message.reply_text(f"🔇 @{target.username or target.first_name} mute {duration//3600}h !")
            await asyncio.sleep(5)
            await msg.delete()
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur: {e}")
    else:
        await update.message.reply_text("❌ Réponds à un message !")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("❌ Admins uniquement !")
        return
    
    total = sum(user_warnings.values())
    users = len([w for w in user_warnings.values() if w > 0])
    contacts = len(user_data)
    
    await update.message.reply_text(f"""
📊 **STATS BOT**

⚠️ Warnings : {total}
👥 Users avertis : {users}
🆕 Nouveaux visiteurs : {contacts}

✅ Toutes protections ACTIVES
🎯 Système d'invitation : ACTIF
    """)

def main():
    print("=" * 70)
    print("🚀 @GuideDuTrading_bot - VERSION WEBHOOK RENDER")
    print("=" * 70)
    
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN manquant !")
    
    print(f"🌐 URL: {RENDER_EXTERNAL_URL}")
    print(f"📍 Port: {PORT}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(ChatMemberHandler(detect_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.Entity("url") | filters.Entity("text_link") | filters.Entity("mention"), check_links))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_text_links))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_insults))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_spam))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_caps))
    app.add_handler(MessageHandler(filters.FORWARDED, check_forwards))
    app.add_handler(MessageReactionHandler(detecter_reaction_individuelle, message_reaction_types=1))
    app.add_handler(MessageReactionHandler(detecter_reaction_anonyme, message_reaction_types=2))
    app.add_handler(CommandHandler("warn", warn_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("mute", mute_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    print("✅ BOT ACTIF!")
    print("🛡️ MODÉRATION : Active")
    print("🎯 SYSTÈME D'INVITATION : Actif")
    print("🔗 LIEN À PARTAGER : https://t.me/GuideDuTrading_bot?start=welcome")
    print("😊 RÉACTIONS : Trackées")
    print(f"👥 ADMINS : {ADMINS}")
    print(f"📬 NOTIFICATIONS → {ADMIN_CHAT_ID} (@Guidedutrading)")
    print(f"👥 GROUPE : {GROUP_ID}")
    print("=" * 70)
    
    # MODE WEBHOOK POUR RENDER
    webhook_url = f"{RENDER_EXTERNAL_URL}/telegram"
    print(f"🔗 Webhook URL: {webhook_url}")
    print("🚀 Démarrage en mode WEBHOOK...")
    print("=" * 70)
    
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="telegram",
        webhook_url=webhook_url,
        allowed_updates=['message', 'message_reaction', 'message_reaction_count', 'channel_post', 'chat_member', 'callback_query'],
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()
