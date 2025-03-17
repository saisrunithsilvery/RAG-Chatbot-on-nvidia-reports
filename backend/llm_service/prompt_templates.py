# llm_service/prompt_templates.py

SYSTEM_TEMPLATES = {
    "chat": "You are a helpful AI assistant specialized in document analysis. Answer questions about the document based solely on the provided content.",
    
    "summarize": "You are a document summarization expert. Create clear, concise, and comprehensive summaries that highlight the most important information.",
    
    "extract_keypoints": "You are a content analysis specialist. Identify and extract the key points, facts, and insights from documents in a clear, organized format."
}

def get_chat_prompt(document_content, question):
    return f"""
Document Content:
----------------
{document_content}

Question:
---------
{question}

Please answer the question based solely on the information in the document. If the answer cannot be found in the document, clearly state that.
"""

def get_summary_prompt(document_content):
    return f"""
Document Content:
----------------
{document_content}

Instructions:
------------
Please provide a comprehensive summary of this document that:
1. Captures the main themes and key points
2. Includes important facts, figures, and conclusions
3. Maintains the document's original meaning and intent
4. Is well-structured and organized

Your summary should be thorough yet concise, highlighting what's most important.
"""

def get_keypoints_prompt(document_content):
    return f"""
Document Content:
----------------
{document_content}

Instructions:
------------
Extract the most important points from this document and present them as a well-organized list.
Each key point should:
- Capture a single important idea or fact
- Be clear and concise
- Include relevant details, numbers, or specifics if applicable

Format the key points as a bulleted list with clear headings for different sections if appropriate.
"""