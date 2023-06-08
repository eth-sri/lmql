# from langchain import LLMChain, PromptTemplate
# from langchain.chat_models import ChatOpenAI
# from langchain.prompts.chat import (ChatPromptTemplate,HumanMessagePromptTemplate)
# from langchain.llms import OpenAI

import lmql

@lmql.query
def company_name(product: str):
    '''
    argmax 
        print("company_name")
        "What is a good name for a company that makes {product}? [company_name]" 
        return {"company_name": company_name}
    from 
        "chatgpt"
    '''


@lmql.query
def write_catch_phrase(company_name: str):
    '''
    argmax 
        print("catch_phrase") 
        "Write a catchphrase for the following company: {company_name}. [catchphrase]"
        return {"catchphrase": catchphrase}
    from 
        "chatgpt"
    '''

@lmql.query
async def acompany_name(product: str):
    '''
    argmax 
        print("acompany_name")
        "What is a good name for a company that makes {product}? [company_name]" 
        return {"company_name": company_name}
    from 
        "chatgpt"
    '''


@lmql.query
async def awrite_catch_phrase(company_name: str):
    '''
    argmax 
        print("acatch_phrase") 
        "Write a catchphrase for the following company: {company_name}. [catchphrase]"
        return {"catchphrase": catchphrase}
    from 
        "chatgpt"
    '''

# name = company_name("socks")
# print(name)
# catchphrase = write_catch_phrase(name)
# print(catchphrase)

# async def main():
#     name = (await acompany_name("socks"))[0]
#     print(name)
#     catchphrase = (await awrite_catch_phrase(name))[0]
#     print(catchphrase)
# lmql.main(main)

from langchain.chains import SimpleSequentialChain
overall_chain = SimpleSequentialChain(chains=[company_name.aschain(), write_catch_phrase.aschain()], verbose=True)

# Run the chain specifying only the input variable for the first chain.
catchphrase = overall_chain.run("colorful socks")
print(catchphrase)