import re
import json
from datetime import datetime, timedelta

import requests
from models import db, SenderSummary, ClientPage
from fireworks import LLM


class LLMManager:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_reply(self, page_id: int, sender_id: str, user_message: str):
            """
            Generate a reply for a given page and sender using OpenAI.
            Updates or creates the summary automatically.
            Returns the reply text.
            """

            # Get page description
            page = ClientPage.query.filter(ClientPage.page_id==page_id).first()
            page_description = page.description if hasattr(page, "description") else ""

            # Get previous summary
            summary_record = SenderSummary.query.filter_by(page_id=page_id, sender_id=sender_id).first()
            previous_summary = summary_record.summary_text if summary_record else ""
            bot_replay = summary_record.bot_replay if summary_record else ""

            # Build strict system prompt
            system_prompt = f"""
You are an AI sales chat assistant. 
You must act like a **real salesperson chatting with a client**.

🔒 RULES (follow strictly):
1. Collect requirements from the user and try to schedule a meeting/call.
2. Always respond in a **professional, persuasive, and sales-oriented tone**.
3. If the user requests a specific date, reply ONLY with:
   "I will check availability and text you again." 
   **Do not confirm or negotiate dates**.
   **Do not offer or negotiate dates**.
4. Reply must be in the SAME language as the user (English or Arabic).
5. "new_summary" must always be in ENGLISH and must include ALL details 
   - It must be a **fresh regenerated summary** of the entire conversation so far.
   - Include ALL important details from:
     - the previous summary,
     - the last bot reply,
     - and the summary of current user message.
   - Write it as one clean, concise, factual summary (not just an addition).
6. Do not invent prices or services not in the Page description.
7. Your output MUST be a valid JSON object that matches the schema below. 
   Replace all values with meaningful content — NEVER placeholders.
8. NEVER greet the user more than once in the whole conversation. Only the very first message may contain a greeting. 
9. NEVER return an empty message. Your reply must always contain useful and non-empty text. 
10. **NEVER repeat any response you have already sent. Each reply must add NEW and relevant information**. 
11. Your answer must directly address the latest user input in a natural and business-appropriate way. 
12. If you cannot add value, summarize the user’s input or ask a clarifying question. 



Page description: {page_description}
Previous summary: {previous_summary}
User message: {user_message}
Last bot reply: {bot_replay}


📑 Schema (strictly follow):
{{
  "reply": "Chat reply to the user in SAME language (short, persuasive, professional)",
  "new_summary": "Updated factual summary in ENGLISH with ALL details"
}}
"""



        # JSON schema for reply + new_summary
            schema = {
    "name": "sales_chat_schema",
    "schema": {
        "type": "object",
        "properties": {
            "reply": {
                "type": "string",
                "description": (
                    "Chat reply to the user in the SAME language they used "
                    "(English or Arabic only). "
                    "This is a **chat message**, not an explanation. "
                    "Tone: professional, persuasive, short, and sales-oriented. "
                    "If the user requests a specific date for a meeting, "
                    "the reply MUST be exactly: 'I will check availability and text you again.' "
                    "Never confirm or negotiate dates. "
                    "Keep reply concise (1–3 sentences max)."
                )
            },
            "new_summary": {
                "type": "string",
                "description": (
                    "Updated factual summary in ENGLISH only. "
                    "This is NOT a reply, but a background memory. "
                    "It must include ALL details from: "
                    "- The current user input "
                    "- The previous summary "
                    "- The last bot reply "
                    "Do not omit anything. "
                    "Summary must be concise, factual, assumption-free, "
                )
            }
        },
        "required": ["reply", "new_summary"],
        "additionalProperties": False
    },
    "strict": True
}

        
            API_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
            try:
                response = requests.post(
                    API_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "accounts/fireworks/models/deepseek-v3p1",   # أو deepseek-reasoner لو عايز
                        "messages": [{"role": "system", "content": system_prompt}],
                        "temperature": 0,
                    "response_format": {
            "type": "json_schema",
            "json_schema": schema
        }    
                    },
                    
                    timeout=40,
                )

                data = response.json()
                parsed = data["choices"][0]["message"]['content']
                parsed = json.loads(parsed)

                if parsed:
                    replay = parsed.get("reply") or parsed.get("response", "")
                    new_summary = parsed.get("new_summary", "")
                else:
                    try:
                        raw_output = data['choices'][0]['message']['content']

                        # 1) Try extracting last JSON object
                        matches = re.findall(r"\{.*?\}", raw_output, re.DOTALL)
                        if matches:
                            last_json = matches[-1]
                            parsed = json.loads(last_json)
                            print("✅ Extracted JSON:", parsed)
                            replay = parsed.get("reply") or parsed.get("bot_reply") or parsed.get("response", "")
                            new_summary = parsed.get("new_summary", "")
                     

                    except Exception as e:
                        print("❌ JSON parse error:", e)
                        replay = "سيتم التواصل معكم في اقرب وقت"
                        new_summary = previous_summary
            except:
                      print("سيتم التواصل معكم في اقرب وقت")
                      return "سيتم التواصل معكم في اقرب وقت"              
            # reply, new_summary = self._handle_llm_response(raw_output, previous_summary, user_message)

            # Save or update summary in DB
            if summary_record:
                summary_record.summary_text = new_summary
                summary_record.bot_replay = replay
                summary_record.expires_at = datetime.utcnow() + timedelta(days=30)
            else:
                summary_record = SenderSummary(
                    page_id=page_id,
                    sender_id=sender_id,
                    summary_text=new_summary,
                    bot_replay = replay,
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                db.session.add(summary_record)
            
            db.session.commit()
            return replay
       

    import re

    def _handle_llm_response(self, llm_response_content, previous_summary, user_message):
        """
        Parse LLM response for 'reply' and 'new_summary'.
        Handles messy quotes and fallback extraction.
        """
        import re
        import json

        reply = ""
        new_info = ""

        # Step 1: Fix common quote issues
        cleaned = llm_response_content.replace('\n', ' ').replace("“", '"').replace("”", '"')

        # Step 2: Attempt JSON parsing
        try:
            data = json.loads(cleaned)
            reply = str(data.get("reply", "")).strip()
            new_info = str(data.get("new_summary", "")).strip()
            return reply, new_info
        except Exception:
            pass  # fall back to regex

        # Step 3: Regex fallback (non-greedy)
        try:
            reply_match = re.search(r'"reply"\s*:\s*"(.+?)"', cleaned)
            new_summary_match = re.search(r'"new_summary"\s*:\s*"(.+?)"', cleaned)
            if reply_match:
                reply = reply_match.group(1).strip()
            if new_summary_match:
                new_info = new_summary_match.group(1).strip()
        except Exception as e:
            print("Fallback extraction failed:", str(e))
            reply = cleaned
            new_info = ""

        # Step 4: Merge with previous summary if needed
        updated_summary = previous_summary.strip()
        if new_info and new_info not in updated_summary:
            updated_summary += " " + new_info if updated_summary else new_info

        return reply, updated_summary
