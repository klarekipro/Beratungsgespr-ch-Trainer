"""Bounded input contracts for the local dashboard (not the historical PoC)."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")]
ShortText = Annotated[str, Field(min_length=1, max_length=240)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Service(InputModel):
    id: Identifier
    title: ShortText
    description: str = Field(min_length=1, max_length=3000)
    conditions: str = Field(default="", max_length=3000)


class Company(InputModel):
    id: Identifier
    revision: int = Field(default=1, ge=1)
    name: ShortText
    description: str = Field(min_length=1, max_length=12000)
    source_url: str = Field(default="", max_length=2000)
    services: list[Service] = Field(min_length=1, max_length=20)
    limitations: str = Field(min_length=1, max_length=5000)
    reviewed: bool = False

    @field_validator("source_url")
    @classmethod
    def safe_source(cls, value):
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("Ссылка должна начинаться с https:// или http://")
        return value

    @model_validator(mode="after")
    def unique_services(self):
        ids = [s.id for s in self.services]
        if len(ids) != len(set(ids)) or "no_fit" in ids:
            raise ValueError("ID услуг должны быть уникальны; no_fit зарезервирован")
        return self


class Fact(InputModel):
    id: Identifier
    stage: Literal["needs", "capabilities"]
    label: ShortText
    value: str = Field(min_length=1, max_length=2000)
    status: Literal["known", "undecided", "does_not_know", "refuses_to_disclose", "not_applicable"]
    keywords: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(default_factory=list, max_length=24)
    required: bool = True
    material: bool = True

    @model_validator(mode="after")
    def applicable_requirement(self):
        if self.status == "not_applicable" and self.required:
            raise ValueError("Неприменимый вопрос не может быть обязательным")
        if self.required and not self.material:
            raise ValueError("Обязательное сведение должно влиять на итоговое решение")
        return self


class Scenario(InputModel):
    id: str = Field(default="", pattern=r"^(?:[a-z0-9][a-z0-9_-]{0,79})?$")
    revision: int = Field(default=1, ge=1)
    company_id: Identifier
    title: ShortText
    customer_name: ShortText
    public_brief: str = Field(min_length=1, max_length=3000)
    opening: str = Field(min_length=1, max_length=2000)
    language: Literal["ru", "de"] = "ru"
    facts: list[Fact] = Field(min_length=2, max_length=20)
    allowed_outcomes: list[Identifier] = Field(min_length=1, max_length=21)
    question_hints: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def complete_card(self):
        ids = [f.id for f in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError("ID фактов должны быть уникальны")
        for stage in ("needs", "capabilities"):
            if not any(f.stage == stage and f.required for f in self.facts):
                raise ValueError("У каждого этапа должен быть обязательный вопрос")
        if len(self.allowed_outcomes) != len(set(self.allowed_outcomes)):
            raise ValueError("Итоговые действия не должны повторяться")
        return self


class SessionStart(InputModel):
    scenario_id: Identifier
    mode: Literal["demo", "openai"]


class MessageInput(InputModel):
    text: str = Field(min_length=1, max_length=6000)
    kind: Literal["message", "summary", "proposal"] = "message"
    request_id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    version: int = Field(ge=1)


class ReviewInput(InputModel):
    note: str = Field(min_length=1, max_length=6000)
