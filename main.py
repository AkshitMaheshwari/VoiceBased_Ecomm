import asyncio
from voice.mic import start_mic
from stt import listen
from retriever import retrieve
from llm import generate_answer_stream
from SessionMemory.Conversation_memory import ConversationMemory
from SessionMemory.user_memory import UserMemory
from tts import stream_tts

conversation = ConversationMemory()
user_memory = UserMemory()

async def main():
    print("🎙 AI Voice Salesman Started (CTRL+C to exit)")
    start_mic()

    while True:
        print("🎧 Listening...")
        query = await listen()

        if not query.strip():
            continue

        print("You:", query)
        conversation.add_user(query)
        user_memory.update(query)

        # Retrieval
        docs = retrieve(query, user_memory)
        context = "\n".join([d.page_content for d in docs])

        # Stream LLM + TTS together
        print("AI: ", end="", flush=True)
        full_response = ""
        
        text_stream = generate_answer_stream(
            context=context,
            convo=conversation.context(),
            prefs=user_memory.summary(),
            query=query
        )
        
        # Stream to TTS while collecting response
        full_response = await stream_tts(text_stream)
        print()  # New line after streaming
        
        conversation.add_ai(full_response)

if __name__ == "__main__":
    asyncio.run(main())