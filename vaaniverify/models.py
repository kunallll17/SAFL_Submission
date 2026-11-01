"""Small, strict schemas. Unknown fields and implicit numeric coercion fail closed."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Operation = Literal["READ_STATUS", "PAY", "MANDATE", "SHARE", "CANCEL_MANDATE"]
Language = Literal["en", "hi", "hinglish", "ta"]
Direction = Literal["READ_ONLY", "MONEY_OUT", "RECURRING_OUT", "DATA_OUT", "CANCEL"]
Handle = Annotated[str, Field(pattern=r"^[a-z][a-z0-9.-]{1,30}@demo$")]
Money = Annotated[int, Field(strict=True, ge=1, le=10_000_000)]
Documents = tuple[Literal["driving_license", "degree_certificate", "address_proof"], ...]

DIRECTIONS: dict[str, str] = {
    "READ_STATUS": "READ_ONLY", "PAY": "MONEY_OUT", "MANDATE": "RECURRING_OUT",
    "SHARE": "DATA_OUT", "CANCEL_MANDATE": "CANCEL",
}
ACTION_FIELDS = {
    "READ_STATUS": (),
    "PAY": ("recipient", "amount_paise"),
    "MANDATE": ("recipient", "amount_paise", "frequency", "installments"),
    "SHARE": ("recipient", "documents", "purpose", "retention_days"),
    "CANCEL_MANDATE": ("mandate_id",),
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Action(StrictModel):
    operation: Operation
    subject: Literal["demo-user"] = "demo-user"
    currency: Literal["INR"] = "INR"
    recipient: Handle | None = None
    amount_paise: Money | None = None
    frequency: Literal["WEEKLY", "MONTHLY"] | None = None
    installments: Annotated[int, Field(strict=True, ge=1, le=12)] | None = None
    documents: Documents = ()
    purpose: Literal["employment", "education", "identity_check"] | None = None
    retention_days: Annotated[int, Field(strict=True, ge=1, le=365)] | None = None
    mandate_id: Annotated[str, Field(pattern=r"^mandate-demo-[0-9]{1,6}$")] | None = None

    @model_validator(mode="after")
    def enforce_shape(self):
        allowed = set(ACTION_FIELDS[self.operation])
        fields = {"recipient", "amount_paise", "frequency", "installments", "documents",
                  "purpose", "retention_days", "mandate_id"}
        present = {name for name in fields if getattr(self, name) not in (None, ())}
        if present != allowed:
            raise ValueError(f"{self.operation} requires exactly these action fields: {', '.join(sorted(allowed)) or 'none'}")
        if len(set(self.documents)) != len(self.documents):
            raise ValueError("Document scopes must be unique")
        return self


class Intent(StrictModel):
    operation: Operation
    language: Language = "hinglish"
    user_text: Annotated[str, Field(min_length=1, max_length=1000)]
    recipient: Handle | None = None
    max_amount_paise: Money | None = None
    allow_external_recipient: bool = Field(default=False, strict=True)
    frequency: Literal["WEEKLY", "MONTHLY"] | None = None
    installments: Annotated[int, Field(strict=True, ge=1, le=12)] | None = None
    documents: Documents = ()
    purpose: Literal["employment", "education", "identity_check"] | None = None
    retention_days: Annotated[int, Field(strict=True, ge=1, le=365)] | None = None
    mandate_id: Annotated[str, Field(pattern=r"^mandate-demo-[0-9]{1,6}$")] | None = None

    @model_validator(mode="after")
    def enforce_scope(self):
        needs_recipient = self.operation in {"PAY", "MANDATE", "SHARE"}
        if needs_recipient and self.recipient is None and not self.allow_external_recipient:
            raise ValueError("Choose a recipient or explicitly permit external recipient review")
        if self.recipient and self.allow_external_recipient:
            raise ValueError("A pinned recipient cannot also be externally replaceable")
        # Reuse action invariants, substituting only the explicitly delegated recipient.
        Action(operation=self.operation,
               recipient=self.recipient or ("external.review@demo" if needs_recipient else None),
               amount_paise=self.max_amount_paise, frequency=self.frequency,
               installments=self.installments, documents=self.documents, purpose=self.purpose,
               retention_days=self.retention_days, mandate_id=self.mandate_id)
        if not needs_recipient and self.allow_external_recipient:
            raise ValueError("This operation does not accept an external recipient")
        return self


class ProposalInput(StrictModel):
    intent_id: Annotated[str, Field(min_length=10, max_length=100)]
    action: Action
    agent_message: Annotated[str, Field(max_length=2000)] = ""
    external_text: Annotated[str, Field(max_length=4000)] = ""


class Approval(StrictModel):
    direction: Direction
    recipient_answer: Annotated[str, Field(max_length=64)] = ""
    amount_answer_paise: Annotated[int, Field(strict=True, ge=0)] = 0
    action_digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    terms_accepted: bool = Field(strict=True)


class Execution(StrictModel):
    action: Action
    token: Annotated[str, Field(min_length=20, max_length=12000)]
