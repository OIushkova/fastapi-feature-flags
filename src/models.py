from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Union

from beanie import Indexed
from beanie.odm.operators.update.general import Set, Unset
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import constr, validator, BaseModel, Field

from src.common.base_model import BaseDocument, Push, BaseNestedDocument
from src.keys_utils import generate_new_key
from src.lib.json_logic import evaluate


ALLOWED_TYPES = Union[str, int, float, bool]


class FlagRule(BaseNestedDocument):
    rules: Optional[Union[dict, ALLOWED_TYPES]] = None
    default: Optional[ALLOWED_TYPES] = None

    def db_representation(self, exclude_none=False) -> dict:
        _fields = self.dict(exclude_none=exclude_none)
        return {f: _fields[f] for f in FlagRule.__fields__}


class Flag(FlagRule):
    name: Indexed(constr(min_length=4, max_length=20))
    default: ALLOWED_TYPES = False


Flag.init_fields()


class FlagEvaluationStatus(Enum):
    OK = "ok"
    ERROR = "error"


class FlagEvaluationResult(BaseModel):
    value: ALLOWED_TYPES
    status: FlagEvaluationStatus
    reason: str


ApiKeyValue = str


class ApiKeyDescription(BaseModel):
    name: constr(min_length=4, max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApiKey(ApiKeyDescription):
    key: ApiKeyValue = Field(default_factory=generate_new_key)


class Environment(BaseDocument):
    name: constr(min_length=3, max_length=20)
    flags: Optional[Dict[str, FlagRule]] = None
    server_side_keys: Dict[ApiKeyValue, ApiKeyDescription] = Field(default_factory=dict)
    client_side_keys: Dict[ApiKeyValue, ApiKeyDescription] = Field(default_factory=dict)

    @classmethod
    async def init_model(cls, database: AsyncIOMotorDatabase, allow_index_dropping: bool) -> None:
        await super().init_model(database, allow_index_dropping)
        await cls.create_collection(database)

        # make flag's names to be unique
        # await database.command(
        #     {
        #         "collMod": cls._document_settings.motor_collection.name,
        #         "validator": {
        #             "$or": [
        #                 {"flags": {"$not": {"$type": "array"}}},
        #                 {
        #                     "$expr": {
        #                         "$eq": [
        #                             {"$size": "$flags.name"},
        #                             {"$size": {"$setUnion": "$flags.name"}},
        #                         ]
        #                     }
        #                 },
        #             ]
        #         },
        #     }
        # )

    @validator("name")
    def name_length(cls, v):
        if 3 <= len(v) <= 20:
            return v
        raise ValueError("the name must be from 3 to 20 characters long")

    async def update_flag(self, flag_name: str, flag_updatable: FlagRule):
        expr = {
            f"{Environment.flags}.{flag_name}.{f}": v
            for f, v in flag_updatable.db_representation().items()
        }

        if not expr:
            return

        await self.update(Set(expr))

    async def get_all_rules(self) -> Optional[Dict[str, FlagRule]]:
        return self.flags

    async def get_flag_rule(self, flag_name: str) -> Optional[FlagRule]:
        return self.flags.get(flag_name)

    async def evaluate_flag(self, flag_name: str, context: dict) -> Optional[FlagEvaluationResult]:
        flag_rule = await self.get_flag_rule(flag_name)
        if not flag_rule:
            return

        return self._evaluate_flag(flag_rule, context)

    async def evaluate_flags(self, context: dict) -> Optional[Dict[str, FlagEvaluationResult]]:
        rules = await self.get_all_rules()
        if not rules:
            return
        return {f_name: self._evaluate_flag(f_rule, context) for f_name, f_rule in rules.items()}

    @staticmethod
    def _evaluate_flag(flag_rule: FlagRule, context: dict) -> FlagEvaluationResult:
        status = FlagEvaluationStatus.OK
        reason = ""
        try:
            res = evaluate(flag_rule.rules, context)
        except Exception as e:
            res = flag_rule.default
            status = FlagEvaluationStatus.ERROR
            reason = str(e)

        return FlagEvaluationResult(
            value=res,
            status=status,
            reason=reason,
        )

    async def create_api_key(self, api_key: ApiKey, server_side=False) -> ApiKey:
        _key_type_field = (
            Environment.server_side_keys if server_side else Environment.client_side_keys
        )

        await self.update(
            Set({f"{_key_type_field}.{api_key.key}": ApiKeyDescription(**api_key.dict())})
        )
        return api_key

    async def delete_api_key(self, key: ApiKeyValue, server_side=False) -> None:
        _key_type_field = (
            Environment.server_side_keys if server_side else Environment.client_side_keys
        )

        await self.update(
            Unset({f"{_key_type_field}.{key}": ""}),
        )


class Project(BaseDocument):
    name: Indexed(constr(min_length=8, max_length=20), unique=True)
    flags: Optional[Dict[str, FlagRule]] = None
    environment_ids: Optional[List[str]] = None

    @classmethod
    async def init_model(cls, database: AsyncIOMotorDatabase, allow_index_dropping: bool) -> None:
        await super().init_model(database, allow_index_dropping)
        await cls.create_collection(database)
        # make flag's names to be unique
        await database.command(
            {
                "collMod": cls._document_settings.motor_collection.name,
                "validator": {
                    # "$and": [
                    #     {
                    "$or": [
                        {"_environment_ids": {"$not": {"$type": "array"}}},
                        {
                            "$expr": {
                                "$eq": [
                                    {"$size": "$_environment_ids"},
                                    {"$size": {"$setUnion": "$_environment_ids"}},
                                ]
                            }
                        },
                    ]
                    # },
                    # {
                    #     "$or": [
                    #         {"flags": {"$not": {"$type": "array"}}},
                    #         {
                    #             "$expr": {
                    #                 "$eq": [
                    #                     {"$size": "$flags.name"},
                    #                     {"$size": {"$setUnion": "$flags.name"}},
                    #                 ]
                    #             }
                    #         },
                    #     ]
                    # },
                    # ]
                },
            }
        )

    async def before_first_save(self):
        if self.flags is None:
            self.flags = {}
        if self.environment_ids is None:
            self.environment_ids = []

    async def add_environment(self, environment: Environment):
        environment.flags = self.flags
        await environment.create()
        await self.update(Push({"environment_ids": environment.id}))

    async def add_flag(self, flag: Flag) -> Flag:
        db_representation = flag.db_representation()

        await self.update(Set({f"{Project.flags}.{flag.name}": db_representation}))

        if self.environment_ids:
            await Environment.update_many(
                {"_id": {"$in": self.environment_ids}},
                Set({f"{Environment.flags}.{flag.name}": db_representation}),
            )

        return flag

    async def update_flag(self, flag_name: str, flag_updatable: FlagRule):
        # db.Project.updateOne({name:"name"}, {$set:{"flags.flag1.default": true}})

        expr = {
            f"{Project.flags}.{flag_name}.{f}": v
            for f, v in flag_updatable.db_representation().items()
        }

        if not expr:
            return

        await self.update(Set(expr))

    async def remove_flag(self, flag_name: str) -> None:
        await self.update(Unset({f"{Project.flags}.{flag_name}": ""}))

        if self.environment_ids:
            await Environment.update_many(
                {"_id": {"$in": self.environment_ids}},
                Unset({f"{Environment.flags}.{flag_name}": ""}),
            )
