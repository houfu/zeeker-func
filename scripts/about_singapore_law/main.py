import datetime
import os

import bs4
import requests
from ckanapi import RemoteCKAN
from langchain.chains import AnalyzeDocumentChain


def get_chain() -> AnalyzeDocumentChain:
    from langchain.chains import LLMChain, RefineDocumentsChain
    from langchain_core.prompts import PromptTemplate
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model="gpt-4-turbo",
        temperature=0,
        # api_key=" Ensure API Key is set
    )

    prompt = PromptTemplate.from_template("Summarize this content: {context}")
    initial_llm_chain = LLMChain(llm=llm, prompt=prompt)
    initial_response_name = "prev_response"
    prompt_refine = PromptTemplate.from_template(
        "Here's your first summary: {prev_response}. "
        "Now add to it based on the following context: {context}"
        'Start with "This Article:'
    )
    refine_llm_chain = LLMChain(llm=llm, prompt=prompt_refine)
    document_variable_name = "context"
    chain = RefineDocumentsChain(
        initial_llm_chain=initial_llm_chain,
        refine_llm_chain=refine_llm_chain,
        document_variable_name=document_variable_name,
        initial_response_name=initial_response_name,
    )
    from langchain_text_splitters import CharacterTextSplitter

    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=2000, chunk_overlap=0
    )
    return AnalyzeDocumentChain(combine_docs_chain=chain, text_splitter=text_splitter)


def main():
    start_urls = [
        "https://www.singaporelawwatch.sg/About-Singapore-Law/Overview",
        "https://www.singaporelawwatch.sg/About-Singapore-Law/Commercial-Law",
        "https://www.singaporelawwatch.sg/About-Singapore-Law/Singapore-Legal-System",
    ]
    zeeker = RemoteCKAN(
        os.environ["CKAN_HOST"],
        apikey=os.environ["CKAN_API_KEY"],
    )

    # Begin by grabbing all the relevant urls containing articles

    articles_url = []

    for url in start_urls:
        r = requests.get(url)
        soup = bs4.BeautifulSoup(r.text, "html5lib")
        article_list = soup.find(class_="edn__articleListWrapper")
        url_articles = [
            article.a["href"]
            for article in article_list
            if isinstance(article, bs4.element.Tag)
        ]
        articles_url = articles_url + url_articles

    # Process each article in the article list

    for index, url in enumerate(articles_url):
        r = requests.get(url)
        soup = bs4.BeautifulSoup(r.text, "html5lib")
        article = soup.find(class_="edn_article")
        text_list = []
        for child in article.children:
            if isinstance(child, bs4.element.Tag):
                if "edn_fixedPrevNextArticleNavigation" in child.attrs.get("class", []):
                    break
                text_list.append(child)

        # Get a summary of the article
        content_text = "".join([text.text for text in text_list])
        summarize_document_chain = get_chain()
        result = summarize_document_chain.invoke(content_text)
        summary = result["output_text"]

        # Add to the Dataset
        resource_create_result = zeeker.call_action(
            "resource_create",
            {
                "package_id": "about-singapore-law",
                "url": url,
                "description": summary,
                "position": index,
                "name": text_list[0].text,
            },
        )

        resource_id = resource_create_result["id"]

        records = []
        now = datetime.datetime.now().isoformat()

        for text_index, text in enumerate(text_list):
            records.append(
                {
                    "index": text_index,
                    "content": text.text,
                    "title": text_list[0].text,
                    "date": now,
                    "resource_url": url,
                    "zeeker_url": f"https://ckan.zeeker.sg/dataset/about-singapore-law/resource/{resource_id}",
                }
            )

        # Create datastore record
        zeeker.call_action(
            "datastore_create",
            {
                "resource_id": resource_id,
                "force": True,
                "primary_key": "index",
                "fields": [
                    {
                        "id": "index",
                        "type": "int",
                    },
                    {
                        "id": "content",
                        "type": "text",
                        "info": {
                            "label": "Content",
                            "notes": "The portion of the article.",
                        },
                    },
                    {
                        "id": "date",
                        "type": "timestamp",
                        "info": {
                            "label": "Date",
                            "notes": "The date this article was scraped from the source.",
                        },
                    },
                    {
                        "id": "title",
                        "type": "text",
                        "info": {"label": "Title", "notes": "Title of the article."},
                    },
                    {
                        "id": "resource_url",
                        "type": "text",
                        "info": {
                            "label": "Source URL",
                            "notes": "The url to the source article.",
                        },
                    },
                    {
                        "id": "zeeker_url",
                        "type": "text",
                        "info": {
                            "label": "Zeeker URL",
                            "notes": "The url to the resource on zeeker.",
                        },
                    },
                ],
                "records": records,
            },
        )


if "__main__" == __name__:
    main()
