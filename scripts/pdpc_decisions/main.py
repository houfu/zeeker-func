import json
import os
from datetime import datetime

import bs4
import requests
from ckanapi import RemoteCKAN
from openai import OpenAI

from pdpc_types import (
    CommissionDecisionItem,
    DPObligations,
    DecisionType,
    SummaryPageData,
)

PACKAGE_NAME = "pdpcsg-decisions"

CASE_LISTING_URL = (
    "https://www.pdpc.gov.sg/api/pdpcenforcementcases/getenforcementcaselisting"
)


def create_form_data(page: int):
    return {
        "keyword": "",
        "industry": "all",
        "nature": "all",
        "decision": "all",
        "penalty": "all",
        "page": str(page),
    }


def get_data():
    start_form_date = create_form_data(1)
    # Get the number of total pages
    response = requests.post(CASE_LISTING_URL, data=start_form_date)

    if response.status_code == requests.codes.ok:
        response_json = response.json()
        total_pages = response_json["totalPages"]

        for page in range(1, total_pages + 1):
            yield requests.post(CASE_LISTING_URL, data=create_form_data(page=page))


def get_summary_and_respondent(article_text: str) -> SummaryPageData:
    openai_client = OpenAI()
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "I will provide a passage about a decision made by the Personal Data Protection "
                "Commission in Singapore. Your role is to locate the information in the passage and "
                "output JSON in the "
                'following schema:\n\n{\n  "type": "object",\n  "properties": {\n    '
                '"Summary": {\n      "type": "string",\n      "description": "A brief summary '
                'of the decision provided by the Personal Data Protection Commission in Singapore."'
                '\n    },\n    "Respondent": {\n      "type": "string",\n      '
                '"description": "The person or entity who is the subject of the decision. '
                'If there are more than 1 respondent, they are separated by commas."\n    }\n  }\n}',
            },
            {"role": "user", "content": article_text},
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    data = json.loads(response.choices[0].message.content)
    return SummaryPageData(**data)

    # prompt = ChatPromptTemplate.from_messages(
    #     [
    #         (
    #             "system",
    #             "You extract information about a decision from the Personal Data Protection Commission "
    #             "in Singapore. Output in JSON",
    #         ),
    #         ("human", "{text}"),
    #     ]
    # )
    # model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    # runnable = prompt | model.with_structured_output(schema=SummaryPageData, method="json_mode")
    # return runnable.invoke({"text": article_text})


def main():

    zeeker = RemoteCKAN(
        os.environ["CKAN_HOST"],
        apikey=os.environ["CKAN_API_KEY"],
    )

    # Part 0: Prepare the package/dataset (The package should not exist, and the API token should have the rights
    # to do this.

    package_create_result = zeeker.call_action(
        "package_create",
        {
            "name": PACKAGE_NAME,
            "title": "PDPC Enforcement Decisions",
            "notes": "The Personal Data Protection Commission (PDPC) publishes "
            "decisions relating to organisations that are found to"
            " have contravened the data protection provisions under the"
            " Personal Data Protection Act (PDPA). These decisions"
            " provide valuable insights and lessons so that"
            " organisations can implement measures to prevent similar"
            " occurrences. They also serve to remind individuals and"
            " organisations of their respective rights and obligations"
            " under the PDPA. In the longer term, the publication of"
            " cases aims to promote accountability among organisations"
            " to build and strengthen consumer trust and confidence. "
            "\n\n"
            "This dataset contains enforcement decisions made by "
            "the PDPC from 2016. Updated manually monthly.",
            "owner_org": "personal-data-protection-commission-sg",
            "maintainer": "Ang Hou Fu",
            "maintainer_email": "houfu+i2em2ddq@outlook.sg",
        },
    )

    # Part 0A: Initialize data store

    consolidated_create_result = zeeker.call_action(
        "resource_create",
        {"package_id": PACKAGE_NAME, "url": "", "name": "Consolidated Data"},
    )

    consolidated_resource_id = consolidated_create_result["id"]

    zeeker.call_action(
        "datastore_create",
        {
            "resource_id": consolidated_resource_id,
            "force": True,
            "primary_key": "resource_url",
            "fields": [
                {
                    "id": "date_published",
                    "type": "timestamp",
                    "info": {
                        "label": "Date Published",
                        "notes": "The date this decision was published by the PDPC.",
                    },
                },
                {
                    "id": "title",
                    "type": "text",
                    "info": {"label": "Title", "notes": "Title of the decision."},
                },
                {
                    "id": "content",
                    "type": "text",
                    "info": {
                        "label": "Content",
                        "notes": "Extracted text from the decision.",
                    },
                },
                {
                    "id": "summary",
                    "type": "text",
                    "info": {
                        "label": "Summary",
                        "notes": "Summary of this decision as provided by PDPC.",
                    },
                },
                {
                    "id": "respondent",
                    "type": "text",
                    "info": {
                        "label": "Respondent(s)",
                        "notes": "The name of the respondents in this decision. If there are several, they are "
                        "separated by commas.",
                    },
                },
                {
                    "id": "nature",
                    "type": "text[]",
                    "info": {
                        "label": "Relevant obligations",
                        "notes": "The data protection obligations which are involved in this decision "
                        "as provided by PDPC",
                    },
                },
                {
                    "id": "decision",
                    "type": "text[]",
                    "info": {
                        "label": "Decision",
                        "notes": "The type of decision rendered by the PDPC.",
                    },
                },
                {
                    "id": "resource_url",
                    "type": "text",
                    "info": {
                        "label": "Source URL",
                        "notes": "The url to the PDF of the decision.",
                    },
                },
                {
                    "id": "summary_url",
                    "type": "text",
                    "info": {
                        "label": "Summary URL",
                        "notes": "The url to the summary on PDPC's website.",
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
        },
    )

    # Part 1: Get the data to start a pipeline
    decision_items: list[CommissionDecisionItem] = []
    for response in get_data():
        response_json = response.json()
        for item in response_json["items"]:
            nature = (
                [DPObligations(nature.strip()) for nature in item["nature"].split(",")]
                if item["nature"]
                else "None"
            )
            decision = (
                [
                    DecisionType(decision.strip())
                    for decision in item["decision"].split(",")
                ]
                if item["decision"]
                else "None"
            )
            decision_items.append(
                CommissionDecisionItem(
                    title=item["title"],
                    summary_url=f"https://www.pdpc.gov.sg{item['url']}",
                    nature=nature,
                    decision=decision,
                    published_date=datetime.strptime(
                        item["date"], "%d %b %Y"
                    ).isoformat(),
                    respondent=None,
                    decision_url=None,
                    summary=None,
                    content=None,
                    zeeker_url=None,
                )
            )

    # Part 2: Process each item's summary page
    for index, item in enumerate(decision_items):
        soup = bs4.BeautifulSoup(
            requests.get(item.summary_url).text, features="html5lib"
        )
        article = soup.find("article")

        # Gets the summary and respondent from the decision summary page
        response_dict = get_summary_and_respondent(article.text)

        item.summary = response_dict.Summary
        item.respondent = response_dict.Respondent

        # Gets the link to the file to download the PDF decision
        item.decision_url = f"https://www.pdpc.gov.sg{article.find('a')['href']}"

        # Part 3: Post to Zeeker CKAN
        resource_create_result = zeeker.call_action(
            "resource_create",
            {
                "package_id": PACKAGE_NAME,
                "url": item.decision_url,
                "description": item.summary,
                "position": index,
                "name": item.title,
            },
        )

        resource_id = resource_create_result["id"]

        item.zeeker_url = (
            f"https://ckan.zeeker.sg/dataset/about-singapore-law/resource/{resource_id}"
        )

    zeeker.call_action(
        "datastore_upsert",
        {
            "resource_id": consolidated_resource_id,
            "records": [json.loads(item.json()) for item in decision_items],
            "force": True,
        },
    )


if __name__ == "__main__":
    main()
