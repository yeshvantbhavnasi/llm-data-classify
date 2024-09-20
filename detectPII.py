from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOllama(
    model="llama3.1",
    temperature=0,
    # other params...
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant that detects PII (personally identifiable information) in text. Please help me detect PII in the following text:",
        ),
        ("human", "{input}"),
    ]
)

chain = prompt | llm

inputs = [
    {
        "input": "My name is John Doe and my email address is johndoe@example.com.",
        "output": "PII: Yes, Kind: Name/Person Name, Specifics: John Doe",
    },
    {
        "input": "I live at 123 Main Street, New York, NY.",
        "output": "PII: Yes, Kind: Address, Specifics: 123 Main Street, New York, NY",
    },
    {
        "input": "My social security number is 123-45-6789.",
        "output": "PII: Yes, Kind: SSN, Specifics: 123-45-6789",
    },
    {
        "input": "My credit card number is 1234-5678-9012-3456.",
        "output": "PII: Yes, Kind: Credit Card Number, Specifics: 1234-5678-9012-3456",
    },
    {
        "input": "Driving license number: 123456789.",
        "output": "PII: Yes, Kind: Driving License Number, Specifics: 123456789",
    },
]

for input_data in inputs:
    chain.invoke(input_data)


# test with new input
print(chain.invoke({"input": "My phone number is 123-456-7890."}))

# test with new input
print(chain.invoke({"input": "The quick brown fox jumps over the lazy dog. In a faraway land, a gentle breeze rustled through the leaves of ancient trees, whispering tales of old. The sky was painted in hues of orange and pink as the sun set behind the mountains. Birds chirped softly, signaling the end of another peaceful day. Meanwhile, in the bustling city, the aroma of freshly baked bread filled the air as people hurried along the crowded streets. Children laughed and played in the park, their carefree spirits a contrast to the busy world around them. The evening brought a calm that settled over the town, wrapping it in a comforting embrace."}))



