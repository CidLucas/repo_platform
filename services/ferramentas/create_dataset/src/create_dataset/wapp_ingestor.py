from langchain_community.chat_loaders.whatsapp import WhatsAppChatLoader

loader = WhatsAppChatLoader(
    path="./data/conversa_teste.txt",
)

raw_messages = loader.lazy_load()
