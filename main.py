import io

import json
import requests
import os
import hmac
import hashlib
from openai import OpenAI

# Access the API key using the environment variable
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
SECRET_KEY = os.environ.get("WHATSAPP_SECRET")
OPENAI_KEY = os.environ.get("OPENAI_KEY")


def lambda_handler(event, context):

    response = None
    print(f"event: {event}")

    if event.get("requestContext", {}).get("http", {}).get("method") == "GET":
        # Process GET request for webhook verification
        queryParams = event.get("queryStringParameters")

        if queryParams:
            mode = queryParams.get("hub.mode")

            if mode == "subscribe":
                verifyToken = queryParams.get("hub.verify_token")

                if verifyToken == VERIFY_TOKEN:
                    challenge = queryParams.get("hub.challenge")
                    response = {
                        "statusCode": 200,
                        "body": int(challenge),
                        "isBase64Encoded": False,
                    }
                else:
                    responseBody = "Error, wrong validation token"
                    response = {
                        "statusCode": 403,
                        "body": json.dumps(responseBody),
                        "isBase64Encoded": False,
                    }
            else:
                responseBody = "Error, wrong mode"
                response = {
                    "statusCode": 403,
                    "body": json.dumps(responseBody),
                    "isBase64Encoded": False,
                }
        else:
            responseBody = "Error, no query parameters"
            response = {
                "statusCode": 403,
                "body": json.dumps(responseBody),
                "isBase64Encoded": False,
            }
    elif event.get("requestContext", {}).get("http", {}).get("method") == "POST":
        # Get the X-Hub-Signature-256 header from the request
        received_signature = event.get("headers", {}).get('x-hub-signature-256')
        print(f"received_signature: {received_signature}")
        headers=event.get("headers", {})
        print(f"headers: {headers}")

        # Process POST request (WhatsApp chat messages)
        body = json.loads(event.get("body", "{}"))
        print(body)
        entries = body.get("entry", [])

        # Validate the signature
        if not verify_webhook(event.get("body",{}),received_signature):
            # Your logic for processing incoming messages
            responseBody = "Error, wrong X-Hub-Signature-256"
            response = {
                "statusCode": 403,
                "body": json.dumps(responseBody),
                "isBase64Encoded": False,
            }
            return response

        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value")

                if value:
                    phone_number_id = value.get("metadata", {}).get("phone_number_id")

                    if value.get("messages"):
                        for message in value.get("messages", []):
                            if message.get("type") == "text":
                                print("Message text")
                                from_number = message.get("from")
                                message_body = message.get("text", {}).get("body")
                                reply_message = "Ack from AWS lambda: " + message_body
                                send_reply(phone_number_id, WHATSAPP_TOKEN, from_number, reply_message)

                                responseBody = "Done"
                                response = {
                                    "statusCode": 200,
                                    "body": json.dumps(responseBody),
                                    "isBase64Encoded": False,
                                }
                            elif message.get("type") == "audio":
                                print("Message audio")
                                audioUrl = get_media_url(message.get("audio",{}).get("id"),WHATSAPP_TOKEN)
                                audioContent = download_media_file(audioUrl,WHATSAPP_TOKEN)
                                if audioContent:
                                    res = generate_corrected_transcript(audioContent)
                                    responseBody = "Transcription and summarization done"
                                    reply_message = f"Summary: {res}"
                                    from_number = message.get("from")
                                    send_reply(phone_number_id, WHATSAPP_TOKEN, from_number, reply_message)
                                    response = {
                                        "statusCode": 200,
                                        "body": json.dumps(responseBody),
                                        "isBase64Encoded": False,
                                    }
                                    print("Audio file conversion finished")

    else:
        responseBody = "Unsupported method " + event.get("requestContext", {}).get("http", {}).get("method")
        response = {
            "statusCode": 403,
            "body": json.dumps(responseBody),
            "isBase64Encoded": False,
        }
    return response

# send message to whatsapp number (in reply to the audio message)
def send_reply(phone_number_id, whatsapp_token, to, reply_message):
    json_data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": reply_message},
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer "+whatsapp_token
    }
    path = f"/v18.0/{phone_number_id}/messages"
    url = f"https://graph.facebook.com{path}"

    response = requests.post(url, data=json.dumps(json_data), headers=headers)

    return response

# Verify that the request made to the webhook is a valid one
def verify_webhook(data, hmac_header):
  hmac_recieved = str(hmac_header).removeprefix('sha256=')
  digest = hmac.new(SECRET_KEY.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
  return hmac.compare_digest(hmac_recieved, digest)

# retrieve from Whatsapp API the url of the Audio Message
def get_media_url(media_id,whatsapp_token):
    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
    }
    path = f"/v18.0/{media_id}/?debug=all"
    url = f"https://graph.facebook.com{path}"
    response = requests.get(url, headers=headers)
    print(f"media id response: {response.json()}")
    return response.json()["url"]

# download the media file from the media url
def download_media_file(media_url,whatsapp_token):
    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
    }
    response = requests.get(media_url, headers=headers)
    buffer = io.BytesIO(response.content)
    buffer.name = 'audio.ogg' 
    return buffer

# call OpenAI API in order to generate transcription
def generateTranscription(audioWav):
    client = OpenAI(api_key=OPENAI_KEY)
    transcript = client.audio.transcriptions.create(
        model="whisper-1", 
        file=audioWav
    )
    return transcript.text

# call OpenAI API to summarize the transcription
def generate_corrected_transcript(audio_file):
    system_prompt = "Sei un utile assistente. Il tuo compito è quello di riassumere il messaggio che ti verrà inviato.. Puoi aggiungere le putneggiature, come punti, virgole e altre."
    client = OpenAI(api_key=OPENAI_KEY)
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": generateTranscription(audio_file)
            }
        ]
    )
    print(response)
    if response.choices and len(response.choices)>0:
        return response.choices[0].message.content
    return "No Content"