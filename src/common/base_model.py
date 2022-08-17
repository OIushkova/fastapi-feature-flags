from datetime import datetime
from typing import Optional, List, Union
from uuid import uuid4

from beanie import Document, WriteRules
from beanie.odm.actions import ActionDirections
from beanie.odm.documents import DocType
from beanie.odm.fields import ExpressionField
from beanie.odm.operators.update.general import BaseUpdateGeneralOperator
from pydantic import Field, BaseModel, root_validator
from pymongo.client_session import ClientSession


class BaseDocument(Document):
    id: str = Field(default_factory=lambda: uuid4().hex, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    async def before_first_save(self) -> None:
        pass

    @root_validator
    def number_validator(cls, values):
        values["updated_at"] = datetime.utcnow()
        return values

    async def insert(
        self: DocType,
        *,
        link_rule: WriteRules = WriteRules.DO_NOTHING,
        session: Optional[ClientSession] = None,
        skip_actions: Optional[List[Union[ActionDirections, str]]] = None,
    ) -> DocType:
        await self.before_first_save()
        return await super().insert(link_rule=link_rule, session=session, skip_actions=skip_actions)

    @classmethod
    async def create_collection(cls, database):
        if (
            cls._document_settings.motor_collection.name
            not in await database.list_collection_names()
        ):
            await database.create_collection(cls._document_settings.motor_collection.name)

    @classmethod
    def update_many(cls, *args, **kwargs):
        return cls._document_settings.motor_collection.update_many(*args, **kwargs)

    class Config:
        validate_assignment = True


class BaseNestedDocument(BaseModel):
    @classmethod
    def init_fields(cls):
        """Init fields like for Document for be able to use names in mongo expressions"""
        for k, v in cls.__fields__.items():
            path = v.alias or v.name
            setattr(cls, k, ExpressionField(path))


class Push(BaseUpdateGeneralOperator):
    operator = "$push"


class Pull(BaseUpdateGeneralOperator):
    operator = "$pull"
