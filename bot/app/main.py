import asyncio
import logging
import os
import uuid

from . import config, db, signal_client, summarizer, transcription, generate_audio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("bot")

HELP_TEXT = (
    "Commandes :\n"
    "!on - se déclarer de service\n"
    "!off - quitter le service\n"
    "!status - voir qui est de service\n"
    "!members - lister les membres enregistrés\n"
    "!help - afficher ce message\n\n"
    "Administrateurs uniquement :\n"
    "!add <nom> <+numéro> - ajouter un membre\n"
    "!remove <+numéro> - supprimer un membre"
)


def handle_command(sender: str, text: str) -> str | None:
    parts = text.strip().split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd == "!help":
        return HELP_TEXT

    if cmd == "!on":
        db.set_on_duty(sender)
        return f"You ({db.get_member_name(sender)}) are now on duty."

    if cmd == "!off":
        if db.get_on_duty() == sender:
            db.set_on_duty(None)
            return "You are now off duty."
        return "You weren't marked as on duty."

    if cmd == "!status":
        on_duty = db.get_on_duty()
        if on_duty:
            return f"On duty: {db.get_member_name(on_duty)} ({on_duty})"
        return "No one is currently on duty."

    if cmd == "!members":
        members = db.list_members()
        if not members:
            return "No members registered yet."
        lines = [f"- {name} ({number})" for number, name in members]
        return "Registered members:\n" + "\n".join(lines)

    if cmd == "!add":
        if sender not in config.ADMIN_NUMBERS:
            return "Only admins can add members."
        if len(parts) < 3:
            return "Usage: !add <name> <+phonenumber>"
        name, number = parts[1], parts[2]
        db.add_member(number, name)
        return f"Added {name} ({number}) as a member."

    if cmd == "!remove":
        if sender not in config.ADMIN_NUMBERS:
            return "Only admins can remove members."
        if len(parts) < 2:
            return "Usage: !remove <+phonenumber>"
        number = parts[1]
        db.remove_member(number)
        return f"Removed {number} from members."

    return None  # not a recognized command


def forward_text(sender: str, text: str) -> str | None:
    on_duty = db.get_on_duty()
    if not on_duty:
        return "Personne n'est de service. Votre message n'a pas été transmis."
    if on_duty == sender:
        return None  # sender is on duty themself, nothing to forward
    sender_name = db.get_member_name(sender)
    signal_client.send_message(on_duty, f"[{sender_name}]: {text}")
    return None


def process_audio_attachment(sender: str, attachment: dict):
    on_duty = db.get_on_duty()
    sender_name = db.get_member_name(sender)

    attachment_id = attachment.get("id")
    content_type = attachment.get("contentType", "audio/aac")
    if not attachment_id:
        return

    os.makedirs(config.TMP_AUDIO_DIR, exist_ok=True)
    local_path = os.path.join(config.TMP_AUDIO_DIR, f"{uuid.uuid4()}.audio")
    audio_output_path = os.path.join(config.TMP_AUDIO_DIR, f"{uuid.uuid4()}.wav")

    try:
        raw = signal_client.download_attachment(attachment_id)
        with open(local_path, "wb") as f:
            f.write(raw)

        transcript = transcription.transcribe(local_path)
        
        message = (
            f"[{sender_name}] a envoyé un message vocal.\n\n"
            f"Transcription : {transcript if transcript else '(aucune parole détectée)'}"
        )

        if on_duty:
            audio_note = signal_client.attachment_to_base64_note(raw, content_type)
            signal_client.send_message(on_duty, message, attachments_b64=[audio_note])
        else:
            signal_client.send_message(
                sender, "Personne n'est de service. Voici votre transcription/résumé :\n\n" + message
            )
        summary = summarizer.summarize(transcript)
        message2 = (
            f"Résumé : {summary}"
        )
        generate_audio.generate_french_audio(summary, audio_output_path)
        audio_note2 = signal_client.attachment_to_base64_note(open(audio_output_path, "rb").read(), "audio/wav")
        signal_client.send_message(on_duty, message2, attachments_b64=[audio_note2])
        
    except Exception:
        log.exception("Failed processing audio attachment from %s", sender)
        signal_client.send_message(sender, "Désolé, quelque chose s'est mal passé lors du traitement de votre message vocal.")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
        if os.path.exists(audio_output_path):
            os.remove(audio_output_path)


def handle_envelope(envelope: dict):
    sender = envelope.get("source") or envelope.get("sourceNumber")
    data_message = envelope.get("dataMessage")
    if not sender or not data_message:
        return  # receipts, typing indicators, sync messages, etc.

    if not db.is_member(sender):
        log.info("Ignoring message from unregistered number %s", sender)
        return

    text = (data_message.get("message") or "").strip()
    attachments = data_message.get("attachments") or []

    # Handle any audio attachments first
    for attachment in attachments:
        content_type = attachment.get("contentType", "")
        if content_type.startswith("audio/"):
            process_audio_attachment(sender, attachment)

    if not text:
        return

    if text.startswith("!"):
        reply = handle_command(sender, text)
        if reply:
            signal_client.send_message(sender, reply)
        return

    reply = forward_text(sender, text)
    if reply:
        signal_client.send_message(sender, reply)


async def main():
    db.init_db()
    log.info("Bot starting for number %s", config.SIGNAL_NUMBER)
    async for envelope in signal_client.listen():
        try:
            handle_envelope(envelope)
        except Exception:
            log.exception("Error handling envelope: %s", envelope)


if __name__ == "__main__":
    asyncio.run(main())
