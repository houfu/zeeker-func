from enum import Enum
from typing import Union, Optional

from pydantic import BaseModel, Field


class DPObligations(Enum):
    ACCESS_AND_CORRECTION = "Access and Correction"
    ACCOUNTABILITY = "Accountability"
    ACCURACY = "Accuracy"
    CONSENT = "Consent"
    DATA_BREACH_NOTIFICATION = "Data Breach Notification"
    DO_NOT_CALL_PROVISIONS = "Do Not Call Provisions"
    NOTIFICATION = "Notification"
    PROTECTION = "Protection"
    PURPOSE_LIMITATION = "Purpose Limitation"
    RETENTION_LIMITATION = "Retention Limitation"
    TRANSFER_LIMITATION = "Transfer Limitation"

    def __repr__(self):
        """Override default behaviour to just output the value"""
        return self.value


class DecisionType(Enum):
    ADVISORY_NOTICE = "Advisory Notice"
    DIRECTIONS = "Directions"
    FINANCIAL_PENALTY = "Financial Penalty"
    NO_FURTHER_ACTION = "No further action"
    NOT_IN_BREACH = "Not in Breach"
    WARNING = "Warning"

    def __repr__(self):
        """Override default behaviour to just output the value"""
        return self.value


class CommissionDecisionItem(BaseModel):
    title: str
    published_date: str
    summary_url: str = ""
    nature: Union[list[DPObligations], str] = ""
    decision: Union[list[DecisionType], str] = ""
    respondent: Optional[str] = ""
    decision_url: Optional[str] = ""
    summary: Optional[str] = ""
    content: Optional[str] = ""
    zeeker_url: Optional[str] = ""


class SummaryPageData(BaseModel):
    """Data to be extracted from the summary page"""

    Summary: Optional[str] = Field(
        default=None,
        description="A brief summary of the decision."
    )
    Respondent: Optional[str] = Field(
        default=None,
        description="The subject of the decision. If more than 1, separate by commas."
    )
