from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.prompts.chat import (ChatPromptTemplate,HumanMessagePromptTemplate)
from langchain.llms import OpenAI

import lmql

# setup the LM to be used by langchain
llm = OpenAI(temperature=0.9)

human_message_prompt = HumanMessagePromptTemplate(
        prompt=PromptTemplate(
            template="What is a good name for a company that makes {product}?",
            input_variables=["product"],
        )
    )
chat_prompt_template = ChatPromptTemplate.from_messages([human_message_prompt])
chat = ChatOpenAI(temperature=0.9)
chain = LLMChain(llm=chat, prompt=chat_prompt_template)

@lmql.query
async def write_catch_phrase(company_name: str):
    '''
    argmax "Write a catchphrase for the following company: {company_name}. [catchphrase]" from "chatgpt"
    '''

from langchain.chains import SimpleSequentialChain
overall_chain = SimpleSequentialChain(chains=[chain, write_catch_phrase.aschain()], verbose=True)

# Run the chain specifying only the input variable for the first chain.
catchphrase = overall_chain.run("colorful socks")
print(catchphrase)