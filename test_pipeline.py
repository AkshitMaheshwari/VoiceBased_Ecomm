"""
Text-based chatbot pipeline.
Tests: Retriever → LLM → Streaming Response
"""
import sys
import time
from retriever import retrieve, format_context
from llm import generate_answer_stream
from SessionMemory.Conversation_memory import ConversationMemory
from SessionMemory.user_memory import UserMemory

conversation = ConversationMemory()
user_memory = UserMemory()


def test_retriever(query: str):
    """Test retriever only — shows docs + latency."""
    print(f"\n🔍 Query: {query}")
    print("-" * 50)

    t0 = time.perf_counter()
    docs = retrieve(query, user_memory)
    elapsed = (time.perf_counter() - t0) * 1000

    if not docs:
        print("❌ No documents found!")
        return None

    print(f"✅ Found {len(docs)} documents in {elapsed:.1f}ms\n")
    for i, doc in enumerate(docs, 1):
        print(f"📄 Doc {i}:")
        print(doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content)
        if doc.metadata:
            print(f"   🏷  {doc.metadata}")
        print()

    return docs


def test_full_pipeline(query: str):
    """Full pipeline: Retriever + streaming LLM response."""
    print(f"\n📝 You: {query}")
    print("-" * 50)

    # Update user memory (preference extraction)
    user_memory.update(query)

    # Retrieve — show timing
    t0 = time.perf_counter()
    docs = retrieve(query, user_memory)
    retrieval_ms = (time.perf_counter() - t0) * 1000

    context = format_context(docs)  # Structured context, not raw join

    if docs:
        print(f"✅ Retrieved {len(docs)} docs in {retrieval_ms:.1f}ms")
    else:
        print("⚠️  No docs retrieved")

    # Add to conversation
    conversation.add_user(query)

    # Streaming LLM response — first token appears fast
    print("\n🤖 AI: ", end="", flush=True)
    full_response = []
    t1 = time.perf_counter()
    first_token = True

    for chunk in generate_answer_stream(
        context=context,
        convo=conversation.context(),
        prefs=user_memory.summary(),
        query=query,
    ):
        if first_token:
            ttft_ms = (time.perf_counter() - t1) * 1000
            first_token = False
        print(chunk, end="", flush=True)
        full_response.append(chunk)

    total_ms = (time.perf_counter() - t1) * 1000
    response = "".join(full_response)

    print(f"\n\n⏱  Retrieval: {retrieval_ms:.0f}ms | LLM first token: {ttft_ms:.0f}ms | Total: {total_ms:.0f}ms")

    conversation.add_ai(response)
    return response


def interactive_test():
    """Interactive chat loop with streaming responses."""
    print("\n" + "=" * 50)
    print("🛒 Shopora Chatbot — Fast Mode")
    print("   (type 'quit' to exit, 'clear' to reset memory)")
    print("=" * 50)

    while True:
        try:
            query = input("\n👤 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Bye!")
            break

        if not query:
            continue

        if query.lower() in ("quit", "exit", "q"):
            print("👋 Bye!")
            break

        if query.lower() == "clear":
            conversation.buffer.clear()
            user_memory.pref.update({"budget": None, "brand": None, "category": None})
            print("🔄 Memory cleared.")
            continue

        test_full_pipeline(query)


if __name__ == "__main__":
    # Quick single-shot test (uncomment to use):
    # test_retriever("show me Samsung phones under 30000")
    # test_full_pipeline("I need a budget laptop under 50000")

    interactive_test()
