import re
import openai
import json
from datetime import datetime, timedelta
from models import db, SenderSummary, ClientPage

class LLMManager:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = self.api_key

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

            # Build strict system prompt
            system_prompt =  f"""
You are an expert sales assistant that always responds in the following JSON format. Do NOT use double quotes (") inside the output:

{{
  "reply": "<Reply to the user in the same language, concise, professional, sales-oriented, including all information provided by the user, no extra info>",
  "new_summary": "<Update the factual summary for this user, including all information the user provided, concise, in English, include all info>"
}}

Rules:
- Keep replies as short and clear as possible, while including all user-provided info.
- Use a professional, persuasive, and sales-oriented tone.
- Always escape quotes inside values with \\". Do not use raw " inside strings.
- Don't miss any info in new_summary.
- Do not provide any prices or details that were not given by the user.
- Include **all user-provided information**; never omit anything.
- Reply must be in the same language as the user message (only English or Arabic).
- new_summary must be concise but **fully reflect the user's input and previous summary**.

Page description: {page_description}
Previous summary: {previous_summary}
User message: {user_message}
"""


           
            # Call OpenAI chat model
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt}
                ],
                temperature=0,
                    max_tokens=5000  # You can increase this if needed

            )
                
    

            # Parse response safely
            raw_output = response.choices[0].message.content
            reply, new_summary = self._handle_llm_response(raw_output, previous_summary, user_message)

            # Save or update summary in DB
            if summary_record:
                summary_record.summary_text = new_summary
                summary_record.expires_at = datetime.utcnow() + timedelta(days=30)
            else:
                summary_record = SenderSummary(
                    page_id=page_id,
                    sender_id=sender_id,
                    summary_text=new_summary,
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                db.session.add(summary_record)
            
            db.session.commit()
            return reply
       

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
