"""
Simple text-based test for the voice ecomm pipeline.
Tests: Retriever → LLM → Response
"""
from retriever import retrieve
from llm import generate_answer
from SessionMemory.Conversation_memory import ConversationMemory
from SessionMemory.user_memory import UserMemory

conversation = ConversationMemory()
user_memory = UserMemory()

def test_retriever(query: str):
    """Test retriever only."""
    print(f"\n🔍 Query: {query}")
    print("-" * 50)
    
    docs = retrieve(query, user_memory)
    
    if not docs:
        print("❌ No documents found!")
        return None
    
    print(f"✅ Found {len(docs)} documents:\n")
    for i, doc in enumerate(docs, 1):
        print(f"📄 Doc {i}:")
        print(doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content)
        print()
    
    return docs


def test_full_pipeline(query: str):
    """Test full pipeline: Retriever + LLM."""
    print(f"\n🎯 Full Pipeline Test")
    print(f"📝 Query: {query}")
    print("-" * 50)
    
    # Update user memory
    user_memory.update(query)
    print(f"👤 User Prefs: {user_memory.summary()}")
    
    # Retrieve
    docs = retrieve(query, user_memory)
    if docs:
        context = "\n".join([d.page_content for d in docs])
        print(f"✅ Retrieved {len(docs)} docs")
    else:
        context = ""
        print("⚠️ No docs retrieved")
    
    # Add to conversation
    conversation.add_user(query)
    
    # Generate response
    print("\n🤖 Generating response...")
    response = generate_answer(
        context=context,
        convo=conversation.context(),
        prefs=user_memory.summary(),
        query=query
    )
    
    print(f"\n💬 AI Response:\n{response}")
    conversation.add_ai(response)
    
    return response


def interactive_test():
    """Interactive chat loop."""
    print("\n" + "=" * 50)
    print("🛒 Voice Ecomm Test Mode (type 'quit' to exit)")
    print("=" * 50)
    
    while True:
        query = input("\n👤 You: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("👋 Bye!")
            break
        
        if not query:
            continue
        
        # Always run full pipeline for each user query
        test_full_pipeline(query)


if __name__ == "__main__":
    # Quick tests
    # print("=" * 50)
    # print("🧪 RETRIEVER TEST")
    # print("=" * 50)
    
    # # Test 1: Basic retriever test
    # test_retriever("what is the price of the apple iphone 10")
    
    # # Test 2: Full pipeline
    # print("\n" + "=" * 50)
    # print("🧪 FULL PIPELINE TEST")
    # print("=" * 50)
    
    # test_full_pipeline()
    
    # Test 3: Interactive mode (always full pipeline)
    print("\n" + "=" * 50)
    interactive_test()
