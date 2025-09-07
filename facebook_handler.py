import requests

class FacebookWebhookHandler:
    GRAPH_URL = "https://graph.facebook.com/v20.0"
    
    def verify_webhook(self, args, verify_token_from_db):
        """
        Handles Facebook webhook verification (GET).
        Args:
            args: request.args from Flask/Django
            verify_token_from_db: token stored in DB for this app/page
        Returns:
            (response_text, status_code)
        """
        mode = args.get("hub.mode")
        token = args.get("hub.verify_token")
        challenge = args.get("hub.challenge")

        if mode == "subscribe" and token == verify_token_from_db:
            return challenge, 200
        return "Verification token mismatch", 403

    def parse_webhook_event(self, data):
        """
        Parse incoming Facebook webhook events.
        Args:
            data: JSON payload from POST request
        Returns:
            List of dicts with event info:
            {
                "page_id": str,
                "event_type": "message" or "comment",
                "sender_id": str,
                "sender_name": str (optional),
                "message_text": str (for messages/comments),
                "post_id": str (if comment),
                "comment_id": str (if comment),
                "raw_event": dict
            }
        """
        events = []

        if data.get("object") == "page":
            for entry in data.get("entry", []):
                page_id = entry.get("id")

                # --- Handle comments ---
                for change in entry.get("changes", []):
                    if change.get("field") == "feed":
                        
                        value = change.get("value", {})
                        verb = value.get("verb")
                        if verb == "remove":
                            continue

                        if value.get("item") == "comment":
                            message_text = value.get("message") or value.get("text") or ""

                            events.append({
                                "page_id": page_id,
                                "event_type": "comment",
                                "sender_id": value.get("from", {}).get("id"),
                                "sender_name": value.get("from", {}).get("name"),
                                "message_text": message_text,
                                "post_id": value.get("post_id"),
                                "comment_id": value.get("comment_id"),
                                "raw_event": change
                            })

                # --- Handle messages ---
                for messaging_event in entry.get("messaging", []):
                    if messaging_event.get("message"):
                        sender_id = messaging_event["sender"]["id"]
                        message_text = messaging_event["message"].get("text", "")
                        events.append({
                            "page_id": page_id,
                            "event_type": "message",
                            "sender_id": sender_id,
                            "sender_name": None,
                            "message_text": message_text,
                            "post_id": None,
                            "comment_id": None,
                            "raw_event": messaging_event
                        })
        return events

    def send_message(self, page_access_token, recipient_id, text):
        """
        Send a message to a user via Facebook Messenger.
        """
        url = f"{self.GRAPH_URL}/me/messages"
        params = {"access_token": page_access_token}
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
        response = requests.post(url, params=params, json=payload)
        return response.json()

    def reply_comment(self, page_access_token, comment_id, text):
        """
        Reply to a specific comment on a Facebook post.
        """
        url = f"{self.GRAPH_URL}/{comment_id}/comments"
        params = {"access_token": page_access_token}
        payload = {"message": text}
        response = requests.post(url, params=params, data=payload)
        return response.json()

    def add_like(self, page_access_token, object_id):
        """
        Add a like to a comment or post.
        """
        url = f"{self.GRAPH_URL}/{object_id}/likes"
        params = {"access_token": page_access_token}
        response = requests.post(url, params=params)
        return response.json()
