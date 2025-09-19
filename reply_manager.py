import re
import json
import logging
from datetime import datetime, timedelta

import requests
from models import db, SenderSummary, ClientPage
from fireworks import LLM


class LLMManager:
    def __init__(self, api_key: str):
        self.api_key =  "fw_3ZStg1yRydAJfFDiACWY6tBd"

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
            system_prompt =f"""
You must act like a **real salesperson chatting with a client**.

🔒 HARD RULES (obey strictly, never break):
1. Collect requirements from the user and try to schedule a meeting/call.
2. Always respond in a **professional, persuasive, and sales-oriented tone**.
3. If the user requests a specific date, reply ONLY with But use the same user language :
   "I will check availability and text you again"in english or 'سأتحقق من المواعيد المتاحة وسأراسلك مرة أخرى.' in Arabic. "
   - Do NOT confirm dates.
   - Do NOT negotiate or offer alternative dates.
4. Reply must be in the SAME language as the user (English or Arabic).
5. "new_summary" must always be in **ENGLISH** and must include ALL details:
   - It must be a **fresh regenerated summary** of the entire conversation so far.
   - Include ALL important details from:
     - the previous summary,
     - the last bot reply,
     - and the summary of the current user message.
   - Write as one clean, concise, factual summary.
6. Do NOT invent prices didn't provide in description.
7. Output MUST be a valid JSON object that matches the schema below.
   - All values must be meaningful.
   - NEVER output placeholders or empty strings.
8. **NEVER greet the user more than once** in the whole conversation.
   - Only the very first reply may contain a greeting.
9. NEVER return an empty message.
   - Every reply must contain useful, non-empty content.
10. **NEVER repeat, rephrase, or copy the last bot reply**.
    - This includes Arabic replies, English replies, and short phrases.
    - Each reply must introduce **new, original content**.
    - If no new value can be added, **ask a clarifying question instead**.
11. Your reply MUST directly address the latest user input in a natural, business-appropriate way.
12. If the user asks about price:
    - Do NOT provide prices.
    - Focus on collecting requirements and scheduling a meeting.
13. If you cannot add business value:
    - Reframe the user’s input OR ask a clarifying question.
    - But you MUST NOT repeat the last reply.
14. If the user clearly tries to close or end the conversation (e.g., says thank you, goodbye, not interested, I’ll get back later):
   → Reply with a short, polite closing message in the SAME language (English or Arabic). 
   → Do not ask further questions, do not try to push, do not spam. End gracefully. 

Page description: {page_description}
Previous summary: {previous_summary}
User message: {user_message}
Last bot reply (⚠️  **STRICTLY FORBIDDEN TO REPEAT OR REPHRASE)**:  '{bot_replay}'

Schema (strictly follow):
{{
  "reply": "Chat reply to the user in SAME language (Arabic or English). Must be short (1–3 sentences), persuasive, professional. 
   ✅ If the user is still engaged: collect requirements, ask clarifying questions, or encourage scheduling a meeting. 
   ✅ If the user requests a date: reply MUST be exactly 'I will check availability and text you again. or 'سأتحقق من المواعيد المتاحة وسأراسلك مرة أخرى.' in Arabic. 
   ✅ If the user clearly tries to close/end the conversation (e.g. says thank you, goodbye, not interested, will get back later): reply with a short, polite closing message without spamming or asking further questions. 
   Never empty, never generic, never repeated.",
   "new_summary": "Updated factual summary in ENGLISH only. It MUST include ALL important details without missing anything:
   - From the previous summary,
   - From the last bot reply (as meaning, not exact words),
   - From the current user input,
   - From the page description if relevant. 
   This must be a complete, fresh regeneration of the entire conversation so far, not just an addition. 
   It must be written as one concise, factual, assumption-free paragraph. 
   Nothing can be skipped, omitted, or ignored."
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
                    "Chat reply to the user in the SAME language they used (English or Arabic only). "
                    "This is a **chat message**, not an explanation. "
                    "Tone: professional, persuasive, short (1–3 sentences), and sales-oriented. "
                    "Rules: "
                    "- If the user is engaged: collect requirements, ask clarifying questions, or encourage scheduling a meeting. "
                    "- If the user requests a specific date: the reply MUST be exactly 'I will check availability and text you again.' in English, "
                    "or 'سأتحقق من المواعيد المتاحة وسأراسلك مرة أخرى.' in Arabic. "
                    "- If the user clearly tries to close/end the conversation (e.g. says thank you, goodbye, not interested, later): "
                    "reply with a short, polite closing message in the SAME language, without spamming or asking more questions. "
                    "The reply must never be empty, never generic, never repeated, and must never copy the last bot reply verbatim."
                )
},
            "new_summary": {
                "type": "string",
                "description": (
                    "Updated factual summary in ENGLISH only. "
                    "This is NOT a reply, but a background memory. "
                    "**It must include ALL details from:** "
                    "-** The current user input** "
                    "- **The previous summary** "
                    "- **The last bot reply** "
                    "**Do not omit anything**. "
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
                

                print(data,flush=True)
                

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
